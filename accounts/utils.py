from datetime import datetime, timedelta, time
from typing import Iterable, List, Dict, Any, Optional, Tuple
import requests
from django.conf import settings
from django.utils import timezone
from .models import *

# 편의 상수
_CO2_KG_PER_KM = 0.232  # 대략 승용차 1km 주행 대비 절감량(예시)
_STEPS_PER_KM   = 1300   # 기록 없을 때 걸음 수 추정
_KCAL_PER_KM    = 50     # 기록 없을 때 칼로리 추정

# =============================================================================
# 1) 사용자 주소 동기화
# =============================================================================
def mirror_user_address(user: CustomUser, addr: Address) -> None:
    """
    대표 주소(FK)와 유저의 주소 미러 필드들을 Address 값으로 동기화.
    """
    user.selected_address = addr
    user.address     = addr.address
    user.addr_level1 = addr.addr_level1
    user.addr_level2 = addr.addr_level2
    user.addr_level3 = addr.addr_level3
    user.latitude    = addr.latitude
    user.longitude   = addr.longitude
    user.save(update_fields=[
        "selected_address", "address", "addr_level1", "addr_level2",
        "addr_level3", "latitude", "longitude"
    ])


def apply_selected_address(user: CustomUser, addr: Address) -> None:
    """
    의미 동일한 별칭 함수. (기존 _apply_selected_address 대체용)
    """
    mirror_user_address(user, addr)


# =============================================================================
# 2) 행정구 / 주간 경계
# =============================================================================
def my_district(user: CustomUser) -> Optional[str]:
    """
    대표 주소가 있으면 그 주소의 '구'(addr_level2), 없으면 유저 미러 필드 사용.
    """
    a = getattr(user, "active_address", None)
    if a and getattr(a, "addr_level2", None):
        return a.addr_level2
    return getattr(user, "addr_level2", None)


def week_bounds_now() -> Tuple[datetime, datetime]:
    """
    (로컬 타임존 기준) 이번 주의 시작/끝 경계 반환.
    시작은 월요일 00:00:00, 끝은 다음 주 월요일 00:00:00 (tz-aware).
    """
    now_local = timezone.localtime()
    week_start_date = now_local.date() - timedelta(days=now_local.weekday())
    start_naive = datetime.combine(week_start_date, time.min)   # naive
    end_naive   = start_naive + timedelta(days=7)
    tz = timezone.get_current_timezone()
    return timezone.make_aware(start_naive, tz), timezone.make_aware(end_naive, tz)


# =============================================================================
# 3) 카카오 주소 검색
# =============================================================================
def kakao_address_search(query: str, size: int = 20) -> List[Dict[str, Any]]:
    """
    카카오 주소 검색 API 래퍼.
    - 반환: [{name, l1, l2, l3, lat, lng}, ...]
    - size는 1~30 범위로 클램프.
    - 오류 시 예외 발생(뷰에서 메시지 처리하기 쉬움).
    """
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {settings.KAKAO_REST_API_KEY}"}

    try:
        size = int(size)
    except Exception:
        size = 20
    size = max(1, min(size, 30))

    r = requests.get(url, headers=headers, params={"query": query, "size": size}, timeout=5)
    if r.status_code != 200:
        raise Exception(f"Kakao API {r.status_code}: {r.text}")

    items: List[Dict[str, Any]] = []
    data = r.json()
    for doc in data.get("documents", []):
        base = doc.get("road_address") or doc.get("address")
        if not base:
            continue
        name = base.get("address_name") or doc.get("address_name")
        l1 = base.get("region_1depth_name") or ""
        l2 = base.get("region_2depth_name") or ""
        l3 = base.get("region_3depth_name") or ""
        lng = float(base.get("x"))
        lat = float(base.get("y"))
        items.append({"name": name, "l1": l1, "l2": l2, "l3": l3, "lat": lat, "lng": lng})
    return items


# =============================================================================
# 4) 활동 요약/목록(쿼리셋 의존 유틸) — 모델 import 없이 동작
# =============================================================================
def summarize_activity_totals(qs) -> Dict[str, Any]:
    """
    ActivityLog 쿼리셋으로 전체 요약을 계산.
    - total_logs, total_steps, total_points, total_distance_km, co2_saved_kg
    """
    from django.db.models import Sum  # 지연 import (앱 로딩 순환 방지)
    total_logs = qs.count()
    total_steps = qs.aggregate(s=Sum("steps"))["s"] or 0
    total_points = qs.aggregate(s=Sum("point_earned"))["s"] or 0
    total_distance_km = total_points / 100.0  # 규칙: 100P = 1km
    co2_saved_kg = round(total_distance_km * _CO2_KG_PER_KM, 2)
    return {
        "total_logs": total_logs,
        "total_steps": total_steps,
        "total_points": total_points,
        "total_distance_km": total_distance_km,
        "co2_saved_kg": co2_saved_kg,
    }


def activity_rows_minimal(qs) -> List[Dict[str, Any]]:
    """
    리스트 렌더용 최소 필드만 뽑아 dict 목록으로 변환.
    (shopping_list, market 리レー션은 select_related로 미리 붙여주면 효율↑)
    """
    rows: List[Dict[str, Any]] = []
    for log in qs:
        sl = getattr(log, "shopping_list", None)
        market = getattr(sl, "market", None) if sl else None
        rows.append({
            "visited_at": log.visited_at,
            "market_name": (market.name if market else "미지정 마트"),
            "shopping_list_id": (sl.id if sl else None),
            "point_earned": log.point_earned or 0,
            "steps": log.steps or 0,
        })
    return rows


# =============================================================================
# 5) 기록이 없을 때 추정값 계산(디테일 모달 AJAX에서 사용)
# =============================================================================
def fallback_from_points(point_earned: int) -> Dict[str, int | float]:
    """
    포인트만 있을 때 거리/걸음/시간/칼로리를 대략 추정.
    - 100P = 1km
    - 1km ≈ 1300보, 1km ≈ 15분, 1km ≈ 50kcal (프로젝트 가정)
    """
    distance_km = point_earned / 100.0 if point_earned else 0.0
    steps = int(round(distance_km * _STEPS_PER_KM))
    minutes = int(round(distance_km * 15))
    kcal = int(round(distance_km * _KCAL_PER_KM))
    return {
        "distance_km": distance_km,
        "steps": steps,
        "travel_minutes": minutes,
        "calories_kcal": kcal,
    }

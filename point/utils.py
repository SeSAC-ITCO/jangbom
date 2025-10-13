from dataclasses import dataclass
from datetime import datetime, timedelta, time
from typing import Optional, Tuple, Iterable
from django.db import transaction
from django.db.models import Sum, F, Value, IntegerField
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.crypto import get_random_string
from .models import *
from accounts.models import CustomUser
from market.models import ShoppingList, Market, MarketStock, Ingredient, ActivityLog


# =============================================================================
# A. 사용자/주소 유틸
# =============================================================================
def my_district(user) -> Optional[str]:
    """대표 주소의 addr_level2 우선, 없으면 유저 필드 값 사용."""
    addr = getattr(user, "active_address", None)
    if addr and getattr(addr, "addr_level2", None):
        return addr.addr_level2
    return getattr(user, "addr_level2", None)


def users_in_same_district(user):
    """같은 구(區)에 속한 사용자 queryset (없으면 전체)."""
    district = my_district(user)
    return CustomUser.objects.filter(addr_level2=district) if district else CustomUser.objects.all()


# =============================================================================
# B. 주간 경계/통계 유틸
# =============================================================================
def week_bounds(now: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    """
    이번 주(월~일) 구간의 [시작, 끝) 타임스탬프를 tz-aware 로 반환.
    - 시작: 월요일 00:00:00
    - 끝:   다음 주 월요일 00:00:00
    """
    now_local = timezone.localtime(now or timezone.now())
    week_start_date = now_local.date() - timedelta(days=now_local.weekday())
    start_naive = datetime.combine(week_start_date, time.min)
    end_naive = start_naive + timedelta(days=7)
    tz = timezone.get_current_timezone()
    return timezone.make_aware(start_naive, tz), timezone.make_aware(end_naive, tz)


def base_logs_this_week(user):
    """같은 구의 이번 주 ActivityLog queryset."""
    start, end = week_bounds()
    return ActivityLog.objects.filter(
        user__in=users_in_same_district(user),
        visited_at__gte=start,
        visited_at__lt=end,
    )


def weekly_points_of(base_qs, user) -> int:
    """주어진 base_qs에서 특정 사용자의 주간 포인트 합."""
    return base_qs.filter(user=user).aggregate(s=Sum("point_earned"))["s"] or 0


def weekly_rank_among(base_qs, my_weekly_points: int) -> Optional[int]:
    """
    base_qs에서 사용자별 주간 포인트 합을 집계해
    나보다 점수가 큰 사람 수 + 1을 순위로 반환.
    포인트가 0이면 None.
    """
    if my_weekly_points <= 0:
        return None
    higher_cnt = (
        base_qs.values("user_id")
        .annotate(points=Sum("point_earned"))
        .filter(points__gt=my_weekly_points)
        .count()
    )
    return higher_cnt + 1


def weekly_stats_qs(base_qs) -> dict:
    """이번 주 전체 통계 (인원수/포인트 합)."""
    return {
        "shopper_count": base_qs.values("user_id").distinct().count(),
        "total_points": base_qs.aggregate(s=Sum("point_earned"))["s"] or 0,
    }


def overall_stats_qs(user) -> dict:
    """같은 구 전체 기간 통계."""
    qs = ActivityLog.objects.filter(user__in=users_in_same_district(user))
    return {
        "shopper_count": qs.values("user_id").distinct().count(),
        "total_points": qs.aggregate(s=Sum("point_earned"))["s"] or 0,
    }


def weekly_top_n(base_qs, n: int = 30):
    """이번 주 상위 N 랭킹."""
    return (
        base_qs.values("user_id", "user__nickname", "user__addr_level3")
        .annotate(points=Sum("point_earned"))
        .order_by("-points", "user_id")[:n]
    )


# =============================================================================
# C. 히스토리 필터/정렬
# =============================================================================
def filter_history_period(qs, period_key: str, periods_map: dict):
    """기간 키(1m/3m/6m/1y/all)에 맞게 ActivityLog queryset 필터."""
    days = periods_map.get(period_key)
    if days is None:  # 'all'
        return qs
    cutoff = timezone.now() - timedelta(days=days)
    return qs.filter(visited_at__gte=cutoff)


def order_history(qs, sort_key: str):
    """정렬 키(latest|points)에 맞게 정렬."""
    sort_field = "visited_at" if sort_key == "latest" else "point_earned"
    return qs.order_by(f"-{sort_field}")


# =============================================================================
# D. 포인트 차감/검증/중복 방지
# =============================================================================
def valid_4digit(code: str) -> bool:
    """정확히 4자리 숫자인지."""
    return bool(code) and code.isdigit() and len(code) == 4


def verify_staff_pin(code: str) -> bool:
    """활성화된 스태프 PIN과 일치하는지."""
    pin = StaffPin.objects.filter(is_active=True).first()
    return bool(pin and pin.verify(code))


def parse_use_point(raw: str) -> int:
    """
    int 변환 + 100 단위/0 이상 검증. 실패 시 ValueError.
    """
    value = int(raw)
    if value < 0 or value % 100 != 0:
        raise ValueError("point must be multiple of 100 and >= 0")
    return value


def ensure_request_id(raw: Optional[str]) -> str:
    """중복 방지용 request_id. 비었으면 생성."""
    rid = (raw or "").strip()
    return rid or get_random_string(24)


@transaction.atomic
def deduct_points_and_log(user, use_point: int, request_id: str, memo: str = "바코드 차감") -> int:
    """
    원자적으로 포인트 차감 + 사용 이력 기록.
    - 중복 요청(request_id) 있으면 IntegrityError(user code에서 선확인 권장)
    - 잔액 부족이면 False 반환 대신 예외 없이 0 업데이트 → 호출 측에서 처리
    반환: 차감 후 잔액(int)
    """
    updated = UserPoint.objects.filter(
        user=user,
        total_point__gte=use_point
    ).update(total_point=F("total_point") - use_point)

    if updated == 0:
        # 잔액 부족
        raise RuntimeError("INSUFFICIENT")

    up = UserPoint.objects.get(user=user)
    PointUsage.objects.create(user=user, amount=use_point, request_id=request_id, memo=memo)
    return int(up.total_point)


# =============================================================================
# E. 누적 걸음 수 (포인트 홈/성공 화면 등에서 공통)
# =============================================================================
def total_steps_of(user) -> int:
    return ActivityLog.objects.filter(user=user).aggregate(
        total_steps=Coalesce(Sum("steps"), Value(0), output_field=IntegerField())
    )["total_steps"]

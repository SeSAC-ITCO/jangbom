import datetime, math, re, requests
from math import radians, cos, sin, sqrt, atan2
from typing import Iterable, Optional, Sequence, Tuple, Set, Dict, Any, List
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
from openai import OpenAI
from .models import Market, MarketStock, ShoppingList, ShoppingListIngredient
from food.models import Ingredient

# 한국 요일 약어
WEEKDAYS_KO = ['월', '화', '수', '목', '금', '토', '일']


# =============================================================================
# A. 거리/경로 관련
# =============================================================================
def get_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine 공식으로 두 좌표 간 거리(km)."""
    R = 6371.0  # km
    d_lat = radians(lat2 - lat1)
    d_lng = radians(lng2 - lng1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lng / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def _cache_key(prefix: str, *parts: Any) -> str:
    return prefix + ":" + ":".join(str(p) for p in parts)


def get_directions_api(start_x: float, start_y: float, end_x: float, end_y: float) -> Optional[Dict[str, Any]]:
    """
    Kakao Mobility Directions API. (자동차 경로 기반이지만, 폴리라인 추출 용도)
    - 캐시: 60초
    """
    key = settings.KAKAO_REST_API_KEY
    if not key:
        return None

    ck = _cache_key("kakao_dir", round(start_x, 5), round(start_y, 5), round(end_x, 5), round(end_y, 5))
    cached = cache.get(ck)
    if cached is not None:
        return cached

    url = "https://apis-navi.kakaomobility.com/v1/directions"
    headers = {"Authorization": f"KakaoAK {key}"}
    params = {
        "origin": f"{start_x},{start_y}",
        "destination": f"{end_x},{end_y}",
        "priority": "RECOMMEND",
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            cache.set(ck, data, 60)
            return data
    except Exception:
        pass
    return None


def get_walking_directions(start_lat: float, start_lng: float, end_lat: float, end_lng: float) -> List[List[float]]:
    """
    Kakao 응답에서 폴리라인 [[lat, lng], ...] 추출. 실패 시 빈 리스트.
    """
    result = get_directions_api(start_lng, start_lat, end_lng, end_lat)
    if not result:
        return []
    try:
        roads = result['routes'][0]['sections'][0]['roads']
        polyline: List[List[float]] = []
        for road in roads:
            v = road.get('vertexes') or []
            for i in range(0, len(v), 2):
                lng = float(v[i])
                lat = float(v[i + 1])
                polyline.append([lat, lng])
        return polyline
    except Exception:
        return []


def get_travel_info(user_lat: float, user_lng: float, market_lat: float, market_lng: float) -> Tuple[int, int, int]:
    """
    (예상시간(분), 거리(m), 적립포인트) 반환.
    - 1순위: TMAP 보행자 경로 (distance_m, duration_s)
    - 폴백: Haversine + 80m/분 가정
    """
    distance_m, duration_s = 0, 0
    try:
        # 지연 import: 의존성 최소화
        from .integrations.tmap_client import get_pedestrian_route
        route = get_pedestrian_route(user_lat, user_lng, market_lat, market_lng)
        distance_m = int(route.get("distance_m", 0))
        duration_s = int(route.get("duration_s", 0))
    except Exception:
        pass

    if distance_m <= 0:
        distance_km = get_distance_km(user_lat, user_lng, market_lat, market_lng)
        distance_m = int(round(distance_km * 1000))

    if duration_s <= 0:
        # 보행 80m/분
        duration_s = max(60, int(distance_m / 80 * 60))

    expected_min = math.ceil(duration_s / 60)
    point_earned = round(expected_min)
    return expected_min, distance_m, point_earned


# =============================================================================
# B. 장바구니/재고 매칭
# =============================================================================
def get_latest_shopping_ingredients(user) -> Set[str]:
    """
    유저의 is_done=False 최신 장바구니의 재료명 set. 없으면 빈 set.
    """
    qs = (
        ShoppingList.objects
        .filter(user=user, is_done=False)
        .order_by('-created_at')
    )
    sl = qs.first()
    if not sl:
        return set()
    names = (
        ShoppingListIngredient.objects
        .filter(shopping_list=sl)
        .values_list('ingredient__name', flat=True)
    )
    return set(names)


def match_ingredients(market: Market, shopping_ingredients_set: Set[str]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    마켓 재고와 유저 장바구니 재료를 비교.
    반환: (matched[], unmatched[]) with {'name', 'image'}
    """
    stocks = MarketStock.objects.filter(market=market).select_related('ingredient')
    stocked_names = {s.ingredient.name for s in stocks}

    ings = Ingredient.objects.filter(name__in=shopping_ingredients_set)
    img_map = {i.name: (i.image.url if i.image else None) for i in ings}

    matched, unmatched = [], []
    for name in sorted(shopping_ingredients_set):
        item = {"name": name, "image": img_map.get(name)}
        (matched if name in stocked_names else unmatched).append(item)

    return matched, unmatched


# =============================================================================
# C. 사용자 활동/ 마켓 영업정보
# =============================================================================
def estimate_steps(distance_m: int, step_length_m: float = 0.75) -> int:
    """거리(m)/보폭(m)으로 걸음 수 추정."""
    if step_length_m <= 0:
        step_length_m = 0.75
    return int(round(distance_m / step_length_m))


def estimate_calories_kcal(user, distance_m: int, duration_min: int, steps: int) -> float:
    """
    칼로리(kcal) 추정.
    1) user.weight_kg 있으면 MET 기반 사용,
    2) 없으면 걸음당 0.045kcal.
    """
    # 기본(보폭 기반)
    kcal_steps = steps * 0.045

    weight_kg = getattr(user, "weight_kg", None)
    if weight_kg and duration_min > 0:
        hours = duration_min / 60.0
        kmh = (distance_m / 1000.0) / hours if hours > 0 else 0.0
        # 평지 보행 대략적 MET
        if   kmh < 3.0: met = 2.3
        elif kmh < 4.0: met = 3.3
        elif kmh < 5.0: met = 3.8
        elif kmh < 6.0: met = 4.3
        else:           met = 5.0
        return round(met * weight_kg * hours, 2)

    return round(kcal_steps, 2)


def is_open_now(open_days: str, open_time, close_time, when=None, *, treat_equal_as_24h: bool = True) -> bool:
    """
    영업 여부 판단.
    - open_days: '월,화,수' 등
    - open_time, close_time: datetime.time
    - treat_equal_as_24h: open==close → 24시간으로 간주
    """
    if not (open_days and open_time and close_time):
        return False

    now = timezone.localtime(when or timezone.now())
    wd = WEEKDAYS_KO[now.weekday()]
    days = {s.strip() for s in open_days.split(',') if s.strip()}
    if wd not in days:
        return False

    t = now.time()
    ot, ct = open_time, close_time

    if treat_equal_as_24h and ot == ct:
        return True

    # 같은 날 닫힘
    if ot <= ct:
        return ot <= t <= ct

    # 자정 넘어 닫힘
    return t >= ot or t <= ct


def minutes_until_close(open_time, close_time, when=None) -> int:
    """현재 기준 마감까지 남은 분(영업 중이 아닐 땐 0). 자정 넘김 포함."""
    if not (open_time and close_time):
        return 0
    now_dt = timezone.localtime(when or timezone.now())
    t = now_dt.time()
    ot, ct = open_time, close_time

    # 같은 날 닫힘
    if ot <= ct:
        if not (ot <= t <= ct):
            return 0
        end = datetime.datetime.combine(now_dt.date(), ct, tzinfo=now_dt.tzinfo)
        return max(0, int((end - now_dt).total_seconds() // 60))

    # 자정 넘김
    if not (t >= ot or t <= ct):
        return 0
    end_date = now_dt.date() if t <= ct else (now_dt.date() + datetime.timedelta(days=1))
    end = datetime.datetime.combine(end_date, ct, tzinfo=now_dt.tzinfo)
    return max(0, int((end - now_dt).total_seconds() // 60))


# =============================================================================
# D. 세션 유틸
# =============================================================================
def reset_cart_session(request) -> None:
    """
    장보기 완료 후 세션 초기화. (food앱 세션 키와 충돌 없이 유지)
    """
    for k in [
        'optional_selected', 'extra_ingredients', 'search_selected',
        'basic', 'optional', 'recipe_input', 'latest_recipe'
    ]:
        request.session.pop(k, None)
    request.session['active_sl_id'] = None

# =============================================================================
# E. GPT 연동 헬퍼(식재료 구매 TIP/칭찬 문구)
# =============================================================================

AI_MODEL_TIPS = getattr(settings, "AI_MODEL_TIPS", "gpt-4o")
AI_TEMPERATURE_DEFAULT = getattr(settings, "AI_TEMPERATURE_DEFAULT", 0.6)

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def generate_tip_text(name: str, followup: str | None = None) -> str:
    """
    followup 이 None이면: 구매 TIP을 '주제: 설명' 형식으로 간결하게.
    followup 이 있으면: 자유로운 대화체로 친근하게 답변.
    """
    if followup:
        # 자유로운 대화체(후속 질문 응답)
        system_prompt = (
            "너는 친근한 요리 도우미야. 형식 제한 없이 자연스러운 존댓말 대화체로 답해."
            " 핵심만 2~5문장 정도로 간결하게, 필요하면 짧은 조언/대안도 함께 제시해."
            " 과장·광고 문구는 피하고, 안전/보관/대체재 팁이 떠오르면 덧붙여."
        )
        user_prompt = (
            f"재료: {name}\n"
            f"사용자 질문: {followup}\n"
            "친근하게 답해줘."
        )
    else:
        # 최초 구매 TIP
        system_prompt = (
            "너는 신선식품 구매 도우미야. 아래 형식을 반드시 지켜.\n"
            "형식: 줄마다 한 문장, 앞에다가 · 같은 줄바꿈 구분 기호를 써줘\n"
            f"예시 : {name} 구매 TIP💡\n• 색 - ...\n• 향 - ...\n• 크기 - ...\n• 손상 - ... \n• 보관법 - ..."
        )
        user_prompt = (
            f"{name} 구매 팁을 6~10줄로 제공해줘. "
            "색/향 → 크기 → 손상 → 보관법 순서로, 각 줄은 접두사 없이 '주제: 설명' 문장으로."
        )

    resp = client.chat.completions.create(
        model=AI_MODEL_TIPS,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=AI_TEMPERATURE_DEFAULT,
    )
    return (resp.choices[0].message.content or "").strip()

def generate_arrival_praises(market_name: str, dong: str | None, distance_m: int | None) -> list[str]:
    """
    도착 화면용 칭찬 문구 2줄 생성. 마크다운/불릿 없이 '문장만' 반환.
    """
    system_prompt = (
        "너는 한국어 카피라이터야. 아래 규칙을 지켜 두 줄짜리 문구를 만든다.\n"
        "- 출력은 정확히 두 줄\n"
        "- 각 줄 12~17자 사이, 존댓말, 끝에 마침표 없기\n"
        "- 각 줄은 문장이 아니라 '명사구(헤드라인/슬로건체)'로 작성\n"
        "- 불릿/번호/대시/별표/이모지/따옴표/마크다운 금지\n"
        "- 지역·시장명을 자연스럽게 녹여 칭찬과 격려의 톤으로 (다만 너무 딱딱한 말투는 지양, 살짝 귀엽게)"
    )

    # 서비스 핵심 메시지 요약(프롬프트에 주입)
    service_pitch = (
        "쌍문동의 동네 마트를 디지털로 연결하여 사용자가 직접 걷고 직접 사고 직접 건강해지는 "
        "걷기형 로컬 장보기 플랫폼. 걷기·소비·건강·지역경제를 '나의 한 끼 식사'로 연결. "
        "디지털 플랫폼을 지역에게 돌려주는 상생 모델."
    )

    user_prompt = (
        f"장소: {dong or ''} {market_name}\n"
        f"사용자는 총 {distance_m or 0}m를 걸어 도착했어.\n"
        f"아래 서비스 특징을 바탕으로 사용자에게 칭찬과 격려 문구 2줄을 만들어줘:\n"
        f"{service_pitch}\n"
        "두 줄은 줄바꿈으로 구분하고, 형식 규칙을 반드시 지켜."
    )

    resp = client.chat.completions.create(
        model=AI_MODEL_TIPS,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=AI_TEMPERATURE_DEFAULT,
    )
    text = (resp.choices[0].message.content or "").strip()

    # 후처리: 혹시 모를 기호/불릿 제거 & 2줄만 추출
    lines = [re.sub(r'^[\s\-\*\•\d\.\)\(]+', '', ln).strip()
             for ln in text.splitlines() if ln.strip()]
    return lines[:2]
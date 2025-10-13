from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.db.models import Sum, Value, IntegerField
from django.db.models.functions import Coalesce
from django.core.cache import cache
import json, random, logging
from decimal import Decimal
from .services.route_service import route_user_to_market
from .models import *
from food.models import Ingredient
from point.models import UserPoint
from .utils import *
from food.utils import get_user_total_point, cart_items_count


# =============================================================================
# A. 마켓 필터 설정 (레시피/식재료)
# =============================================================================

@login_required
def edit_market_filter_recipe(request):
    """
    [필터 설정: 레시피 플로우]
    - 사용자별 마켓 필터(거리/타입) 값을 폼에서 받아 저장.
    - 저장 후 레시피 장바구니 확인 화면으로 이동.
    """
    filt, _ = MarketFilterSetting.objects.get_or_create(user=request.user)

    if request.method == "POST":
        dp = request.POST.get("distance_preference")
        tp = request.POST.get("type_preference")

        if not dp or not tp:
            messages.error(request, "거리와 상점 종류를 각각 하나씩 선택해 주세요.")
            return redirect("market:edit_market_filter_recipe")

        # 유효성 체크(선택지 외 값 방지)
        valid_dp = {v for v, _ in MarketFilterSetting.DistancePref.choices}
        valid_tp = {v for v, _ in MarketFilterSetting.TypePref.choices}

        changed = False
        if dp in valid_dp and dp != filt.distance_preference:
            filt.distance_preference = dp
            changed = True
        if tp in valid_tp and tp != filt.type_preference:
            filt.type_preference = tp
            changed = True

        if changed:
            filt.save()

        return redirect("food:confirm_shopping_list")

    # GET: 설정 폼 렌더
    return render(request, "market/filter_form_recipe.html", {
        "filter": filt,
        "distance_choices": MarketFilterSetting.DistancePref.choices,
        "type_choices": MarketFilterSetting.TypePref.choices,
    })


@login_required
def edit_market_filter_ingredient(request):
    """
    [필터 설정: 식재료 플로우]
    - 사용자별 마켓 필터(거리/타입) 값을 폼에서 받아 저장.
    - 저장 후 ‘식재료 모아보기’ 화면으로 이동.
    """
    filt, _ = MarketFilterSetting.objects.get_or_create(user=request.user)

    if request.method == "POST":
        dp = request.POST.get("distance_preference")
        tp = request.POST.get("type_preference")

        if not dp or not tp:
            messages.error(request, "거리와 상점 종류를 각각 하나씩 선택해 주세요.")
            return redirect("market:edit_market_filter_ingredient")

        valid_dp = {v for v, _ in MarketFilterSetting.DistancePref.choices}
        valid_tp = {v for v, _ in MarketFilterSetting.TypePref.choices}

        changed = False
        if dp in valid_dp and dp != filt.distance_preference:
            filt.distance_preference = dp
            changed = True
        if tp in valid_tp and tp != filt.type_preference:
            filt.type_preference = tp
            changed = True

        if changed:
            filt.save()

        return redirect("food:ingredient_result")

    # GET: 설정 폼 렌더
    return render(request, "market/filter_form_ingredient.html", {
        "filter": filt,
        "distance_choices": MarketFilterSetting.DistancePref.choices,
        "type_choices": MarketFilterSetting.TypePref.choices,
    })


# =============================================================================
# B. 최적 마켓 추천 (가까운 마켓 찾기)
# =============================================================================

@csrf_exempt
@login_required
def nearest_market_view(request):
    """
    [가장 가까운(=규칙상 최적) 마켓 추천]
    1) 사용자 위치와 필터(거리/타입)로 영업 중인 후보 추리기
    2) type_preference가 'mart'일 때, 모든 마트의 장바구니 매칭수가 0이면
       → 전통시장(trad) 중 가장 가까운 곳으로 폴백
    3) 그 외에는 (타입 우선) + (마트일 때 매칭수 내림차순) + (거리 오름차순) 정렬
    4) 최종 선택 마켓의 이동 시간/거리/포인트, 재료 매칭 결과를 템플릿에 전달
    """
    user = request.user
    user_lat, user_lng = user.latitude, user.longitude

    # 사용자 필터
    filt, _ = MarketFilterSetting.objects.get_or_create(user=user)
    min_m, max_m, min_strict = filt.distance_range_m

    def in_range(d):
        return (d > min_m if min_strict else d >= min_m) and d <= max_m

    # 내 장바구니 재료 set (교집합 개수로 가중치)
    shopping_ingredients_set = get_latest_shopping_ingredients(user)

    # 후보 수집: (영업 중 + 거리 범위)
    candidates = []
    for m in Market.objects.all():
        if m.latitude is None or m.longitude is None:
            continue
        d_m = int(round(get_distance_km(user_lat, user_lng, m.latitude, m.longitude) * 1000))
        if not in_range(d_m):
            continue
        if not is_open_now(m.open_days, m.open_time, m.close_time):
            continue

        # 장바구니와의 재료 매칭 개수
        if shopping_ingredients_set:
            match_count = MarketStock.objects.filter(
                market=m, ingredient__name__in=shopping_ingredients_set
            ).count()
        else:
            match_count = 0

        candidates.append((m, d_m, match_count))   # (마켓, 거리(m), 재료일치수)

    # 후보 없으면 안내 화면
    if not candidates:
        return render(request, 'market/nearest_market.html', {
            "market": None, "distance_m": 0, "expected_time": -1,
            "closing_in_minutes": 0, "point_earned": 0,
        })

    # 정렬 로직: 타입 우선 → (마트 우선 시) 매칭수 ↓ → 거리 ↑
    type_pref = (filt.type_preference or "none")  # 'mart' | 'trad' | 'none'

    def type_priority(market_type: str) -> int:
        mt = (market_type or "").lower()
        if type_pref == "mart":
            return 0 if mt == "mart" else 1
        if type_pref == "trad":
            return 0 if mt == "trad" else 1
        return 0

    # 폴백: 'mart' 우선인데 모든 마트가 매칭 0이면 → trad 중 최단거리 선택
    selected_market = None
    if type_pref == "mart":
        marts = [t for t in candidates if (t[0].market_type or "").lower() == "mart"]
        if marts and all(t[2] == 0 for t in marts):
            trads = [t for t in candidates if (t[0].market_type or "").lower() == "trad"]
            if trads:
                trads.sort(key=lambda x: x[1])  # 거리 오름차순
                selected_market = trads[0][0]

    # 일반 정렬: (타입 우선), 마트 우선이면 매칭수 내림차순도 포함
    if selected_market is None:
        def sort_key(tup):
            m, dist, match_cnt = tup
            if type_pref == "mart":
                return (type_priority(m.market_type), -match_cnt, dist)
            else:
                return (type_priority(m.market_type), dist)
        candidates.sort(key=sort_key)
        selected_market = candidates[0][0]

    nearest = selected_market

    # 이동/포인트 계산 (TMAP 보행자 + 폴백)
    expected_time, distance_m, point_earned = get_travel_info(
        user_lat, user_lng, nearest.latitude, nearest.longitude
    )
    # 마감까지 남은 시간(분)
    closing_in_minutes = minutes_until_close(nearest.open_time, nearest.close_time)

    # 내 최신 장바구니에 마켓 연결(한 번만)
    shopping_list = user.shoppinglist_set.order_by('-created_at').first()
    if shopping_list and shopping_list.market_id is None:
        shopping_list.market = nearest
        shopping_list.save(update_fields=['market'])

    # 재료 매칭 결과
    matched_ingredients, unmatched_ingredients = match_ingredients(nearest, shopping_ingredients_set)

    items_count = cart_items_count(user)
    total_point = get_user_total_point(user)

    return render(request, 'market/nearest_market.html', {
        "market": nearest,
        "distance_m": distance_m,
        "expected_time": expected_time,
        "closing_in_minutes": closing_in_minutes,
        "point_earned": point_earned,
        "matched_ingredients": matched_ingredients,
        "unmatched_ingredients": unmatched_ingredients,
        "cart_items_count": items_count,
        "total_point": total_point,
    })


# =============================================================================
# C. 지도/경로 보기 (TMAP 보행자)
# =============================================================================

@login_required
def map_direction_view(request):
    """
    [지도/경로 페이지]
    - TMAP 보행자 경로를 서비스 레이어(route_user_to_market)로 받아서 폴리라인/거리/시간 표시
    - 현재 선택 마켓과 장바구니 재료 매칭 결과도 함께 렌더
    """
    user = request.user
    market_id = request.GET.get('market_id')
    market = get_object_or_404(Market, id=market_id)

    # 1) 경로(보행자) 조회: polyline/거리/시간
    route = route_user_to_market(user, market)  # {'path': [{lat,lng},...], 'distance_m': int, 'duration_s': int}
    polyline = route["path"]

    # 2) 포인트 등 산출(유저↔마켓)
    expected_time, distance_m, point_earned = get_travel_info(
        user.latitude, user.longitude, market.latitude, market.longitude
    )

    # 3) 최신 장바구니에 마켓 연결(없을 때만)
    shopping_list = user.shoppinglist_set.order_by('-created_at').first()
    if shopping_list and getattr(shopping_list, "market", None) is None:
        shopping_list.market = market
        shopping_list.save()

    # 4) 재료 매칭 결과
    shopping_ingredients_set = get_latest_shopping_ingredients(user)
    matched_ingredients, unmatched_ingredients = match_ingredients(market, shopping_ingredients_set)

    items_count = cart_items_count(user)
    total_point = get_user_total_point(user)

    # 5) 영업 여부
    is_open = is_open_now(market.open_days, market.open_time, market.close_time)
    closing_in_minutes = minutes_until_close(market.open_time, market.close_time) if is_open else 0

    # 5) 렌더
    context = {
        'market': market,
        'shopping_list': shopping_list,
        'expected_time': expected_time,
        'distance_m': distance_m,
        'point_earned': point_earned,
        'kakao_key': settings.KAKAO_JS_API_KEY,
        'polyline': json.dumps(polyline),
        'matched_ingredients': matched_ingredients,
        'unmatched_ingredients': unmatched_ingredients,
        "cart_items_count": items_count,
        "total_point": total_point,
        "is_open_now": is_open,
        "closing_in_minutes": closing_in_minutes,
        
    }
    return render(request, 'market/map_direction.html', context)


# =============================================================================
# D. 도착 화면 & 재료 선택 저장
# =============================================================================

log = logging.getLogger(__name__)

@never_cache
@login_required
def market_arrival_view(request, shoppinglist_id):
    """
    [마켓 도착 화면]
    - 이동정보(분/미터/포인트)와 재료 매칭 결과 표시
    - AI 칭찬 문구는 실패 시 기본 2줄로 폴백
    - 매 요청마다 재계산/재생성 & 캐시 금지
    """
    user = request.user
    shopping_list = get_object_or_404(ShoppingList, id=shoppinglist_id, user=user)
    market = shopping_list.market

    # 1) 이동정보는 매 요청마다 재계산
    expected_time, distance_m, point_earned = get_travel_info(
        user.latitude, user.longitude, market.latitude, market.longitude
    )

    # 2) 재료 매칭도 매 요청마다 실행
    shopping_ingredients_set = get_latest_shopping_ingredients(user)
    matched_ingredients, unmatched_ingredients = match_ingredients(market, shopping_ingredients_set)

    items_count = cart_items_count(user)
    total_point = get_user_total_point(user)

    # 3) AI 칭찬 문구 2줄 생성 (에러 시 기본 문구)
    try:
        praise_lines = generate_arrival_praises(
            market.name,
            getattr(market, "dong", None),
            distance_m
        )
        if len(praise_lines) < 2:
            raise ValueError("not enough lines")
    except Exception:
        praise_lines = ["지역 경제를 살린 쇼핑", "탄소 없는 도보 쇼핑"]

    # 4) 디버그: 실제 들어간 값 확인 (문구 고정 이슈 추적용)
    log.info(
        "[arrival] market=%s dong=%s distance_m=%s sl.id=%s",
        market.name, getattr(market, "dong", None), distance_m, shopping_list.id
    )

    context = {
        'user': user,
        'market': market,
        'point_earned': point_earned,
        'distance_m': distance_m,
        'expected_time': expected_time,
        'shopping_list': shopping_list,
        'matched_ingredients': matched_ingredients,
        'unmatched_ingredients': unmatched_ingredients,
        "cart_items_count": items_count,
        'total_point': total_point,
        'praise_lines': praise_lines,
    }

    # 5) 브라우저/프록시 캐시 완전 차단
    resp = render(request, 'market/market_arrival.html', context)
    resp['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp['Pragma'] = 'no-cache'
    resp['Expires'] = '0'
    return resp


@login_required
@require_POST
def save_selected_ingredients_view(request, shoppinglist_id):
    """
    [도착 화면에서 재료 선택 저장]
    - 체크박스로 선택된 재료만 장바구니에 남기고 나머지 제거
    - 저장 후 next가 있으면 그 URL로, 없으면 도착 화면으로 유지
    """
    sl = get_object_or_404(ShoppingList, id=shoppinglist_id, user=request.user)
    selected = set(request.POST.getlist("items"))

    current = set(
        ShoppingListIngredient.objects
        .filter(shopping_list=sl)
        .values_list("ingredient__name", flat=True)
    )

    # 제거
    ShoppingListIngredient.objects.filter(shopping_list=sl)\
        .exclude(ingredient__name__in=selected).delete()

    # 추가
    to_add = selected - current
    if to_add:
        ing_map = {i.name: i for i in Ingredient.objects.filter(name__in=to_add)}
        ShoppingListIngredient.objects.bulk_create(
            [ShoppingListIngredient(shopping_list=sl, ingredient=ing_map[n]) for n in to_add if n in ing_map]
        )

    # 저장 후 이동
    next_url = request.POST.get("next")
    if next_url:
        return redirect(next_url)

    # 폴백: 도착 페이지로 유지
    return redirect("market:market_arrival", shoppinglist_id=sl.id)


# =============================================================================
# E. 식재료 팁 페이지 & API
# =============================================================================

@require_GET
@login_required
def ingredient_tip_page(request):
    """
    [식재료 팁 페이지]
    - 프론트에서 AJAX로 /ingredient_tip_api 호출해 텍스트 렌더
    """
    name = (request.GET.get("name") or "").strip()
    if not name:
        return HttpResponseBadRequest("name required")
    return render(request, "market/ingredient_tip.html", {"name": name})


@require_GET
@login_required
def ingredient_tip_api(request):
    """
    [식재료 팁 API]
    - q가 있으면 캐시 건너뛰고 바로 생성
    - q가 없으면 24h 캐시 사용
    """
    name = (request.GET.get("name") or "").strip()
    q    = (request.GET.get("q") or "").strip()
    if not name:
        return HttpResponseBadRequest("name required")

    if q:  # 후속 질문은 캐시 건너뛰고 즉시 생성
        tip = generate_tip_text(name, followup=q)
        return HttpResponse(tip, content_type="text/plain; charset=utf-8")

    key = f"tip:{name.lower()}"
    tip = cache.get(key)
    if tip is None:
        tip = generate_tip_text(name)
        cache.set(key, tip, 60 * 60 * 24)

    return HttpResponse(tip, content_type="text/plain; charset=utf-8")


# =============================================================================
# F. 구매 인증 (비밀번호) 화면 & 처리
# =============================================================================

@csrf_exempt
@login_required
def verify_secret_code(request):
    """
    [상점 비밀번호 검증]
    - 점주가 생성한 secret_code와 입력값이 일치하면 ‘구매 인증 성공’ 페이지 렌더
    """
    if request.method == "POST":
        input_code = request.POST.get("password")
        market_id = request.POST.get("market_id")
        point_earned = request.POST.get("point_earned")
        shoppinglist_id = request.POST.get("shoppinglist_id")

        market = Market.objects.filter(id=market_id).first()
        if market and market.secret_code == input_code:
            return render(request, 'market/secret_input.html', {
                'market': market,
                'shoppinglist_id': shoppinglist_id,
                'point_earned': point_earned,
                'message': "구매 인증 성공"
            })
        else:
            return render(request, 'market/secret_input.html', {
                'market': market,
                'shoppinglist_id': shoppinglist_id,
                'point_earned': point_earned,
                'message': "올바르지 않은 비밀번호입니다"
            })

    return render(request, 'market/secret_input.html', {
        'message': "잘못된 요청입니다"
    })


@login_required
def secret_input_view(request, market_id):
    """
    [비밀번호 입력 화면]
    - verify_secret_code로 POST 전송하는 뷰
    """
    market = get_object_or_404(Market, id=market_id)
    point_earned = request.GET.get("point_earned")
    shoppinglist_id = request.GET.get("shoppinglist_id")

    return render(request, 'market/secret_input.html', {
        'market': market,
        'point_earned': point_earned,
        'shoppinglist_id': shoppinglist_id,
    })


# =============================================================================
# G. 장보기 완료 (포인트 적립/활동 로그)
# =============================================================================

@login_required
def shopping_success_view(request, shoppinglist_id):
    """
    [장보기 완료 화면]
    1) 영업 중인 주변 장소 3곳 랜덤 추천(닫힘 제외)
    2) 중복 적립 방지: 기존 ActivityLog 확인
    3) TMAP/폴백으로 이동정보 → 걸음수/칼로리 계산
    4) 쇼핑리스트 완료, 포인트 적립, 활동 로그 저장
    5) 세션 초기화 후 완료 화면 렌더
    """
    user = request.user
    shopping_list = get_object_or_404(ShoppingList, id=shoppinglist_id, user=user)
    market = shopping_list.market

    # 1) 주변 장소: 영업 중만 필터 → 랜덤 3개
    places_qs = NearbyPlace.objects.filter(market=market)
    open_places = []
    for p in places_qs:
        if is_open_now(p.open_days, p.open_time, p.close_time):
            p.is_open = True
            p.closing_in_minutes = minutes_until_close(p.open_time, p.close_time)
            open_places.append(p)
    random.shuffle(open_places)
    nearby_sample = open_places[:3]

    total_steps = ActivityLog.objects.filter(user=user).aggregate(
        total_steps=Coalesce(Sum('steps'), Value(0), output_field=IntegerField())
    )['total_steps']

    # 2) 이미 적립된 장보기면 포인트 0
    if ActivityLog.objects.filter(user=user, shopping_list=shopping_list).exists():
        user_point, _ = UserPoint.objects.get_or_create(user=user)
        return render(request, "market/shopping_success.html", {
            "market": market,
            "point_earned": 0,
            "total_point": user_point.total_point,
            "message": "이미 포인트가 지급된 장보기입니다",
            "nearby_places": nearby_sample,
            "total_steps": total_steps,
        })

    # 3) 이동정보(분/미터/포인트)
    expected_time_min, distance_m, point_earned = get_travel_info(
        user.latitude, user.longitude, market.latitude, market.longitude
    )

    # 4) 걸음/칼로리
    steps = estimate_steps(distance_m)
    calories = estimate_calories_kcal(user, distance_m, expected_time_min, steps)

    # 5) 쇼핑리스트 완료 → 포인트 적립 → 활동 로그
    shopping_list.is_done = True
    shopping_list.save(update_fields=["is_done"])

    user_point, _ = UserPoint.objects.get_or_create(user=user)
    user_point.total_point += point_earned
    user_point.save(update_fields=["total_point"])

    ActivityLog.objects.create(
        user=user,
        shopping_list=shopping_list,
        point_earned=point_earned,
        visited_at=timezone.now(),
        steps=steps,
        travel_minutes=expected_time_min,
        calories_kcal=Decimal(str(calories)),
    )

    # 6) 세션 초기화 후 렌더
    reset_cart_session(request)

    return render(request, "market/shopping_success.html", {
        "market": market,
        "point_earned": point_earned,
        "total_point": user_point.total_point,
        "nearby_places": nearby_sample,
        "total_steps": total_steps,
    })


# =============================================================================
# H. 주변 장소 추천 API (랜덤 3)
# =============================================================================

@login_required
@require_GET
def nearby_places_random_api(request, market_id: int):
    """
    [주변 장소 3개 랜덤 API]
    - 영업 중인 곳만 추려서 3개 반환
    """
    market = get_object_or_404(Market, id=market_id)
    items = []
    for p in NearbyPlace.objects.filter(market=market):
        if is_open_now(p.open_days, p.open_time, p.close_time):
            items.append({
                "name": p.name,
                "category": p.category,
                "info": p.info,
                "distance_m": p.distance_m,
                "image_url": (p.image.url if p.image else ""),
                "link_url": p.link_url or "",
                "closing_in_minutes": minutes_until_close(p.open_time, p.close_time),
            })
    random.shuffle(items)
    return JsonResponse({"ok": True, "items": items[:3]})

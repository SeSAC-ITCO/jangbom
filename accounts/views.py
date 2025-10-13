from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.contrib import messages
from django.conf import settings
from datetime import timedelta
from .forms import CustomUserCreationForm, CustomLoginForm
from .models import *
from market.models import ShoppingList, ShoppingListIngredient
from food.models import SavedRecipe
from market.models import ActivityLog
from food.utils import get_user_total_point, cart_items_count
from accounts.utils import *

# =============================================================================
# A. 회원가입 / 로그인 / 로그아웃
# =============================================================================

def signup_view(request):
    """회원가입 → 즉시 로그인 후 스플래시로 이동"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('food:splash')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/signup.html', {'form': form})


def login_view(request):
    """로그인 → 메인으로 이동"""
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('food:main')
    else:
        form = CustomLoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """로그아웃 → 메인으로 이동"""
    logout(request)
    return redirect('food:main')


# =============================================================================
# B. 활동 홈 (전체 요약 + 이번 주 구(區) 랭킹)
# =============================================================================

@login_required
def activity_log_view(request):
    """
    - 전체 기간 기준 ‘나의 활동’ 요약(횟수/걸음/포인트/거리/CO₂)과 목록 제공
    - 랭킹은 ‘이번 주 + 같은 구’ 기준으로만 계산
    """
    user = request.user

    # 전체 활동(완료된 장보기만)
    logs_all = (
        ActivityLog.objects
        .filter(user=user, shopping_list__is_done=True)
        .select_related('shopping_list__market')
        .order_by('-visited_at')
    )

    totals = summarize_activity_totals(logs_all)
    log_data = activity_rows_minimal(logs_all)

    # 이번 주 + 같은 구의 랭킹 계산
    week_start, week_end = week_bounds_now()
    district = my_district(user)
    local_users = (
        CustomUser.objects.filter(addr_level2=district) if district
        else CustomUser.objects.all()
    )

    base_qs = ActivityLog.objects.filter(
        user__in=local_users,
        visited_at__gte=week_start,
        visited_at__lt=week_end,
    )

    my_week_points = base_qs.filter(user=user).aggregate(s=Sum('point_earned'))['s'] or 0
    user_rank = (
        base_qs.values('user')
        .annotate(points=Sum('point_earned'))
        .filter(points__gt=my_week_points)
        .count() + 1
    ) if my_week_points > 0 else None

    items_count = cart_items_count(user)
    total_point = get_user_total_point(user)

    return render(request, 'accounts/activity_log.html', {
        # 전체 기준 요약(유틸 반환 분해)
        'total_logs': totals['total_logs'],
        'total_steps': totals['total_steps'],
        'co2_saved_kg': totals['co2_saved_kg'],

        # 랭킹(이번 주 + 같은 구)
        'user_rank': user_rank,

        # 목록(전체 로그)
        'log_data': log_data,

        "cart_items_count": items_count,
        "total_point": total_point,
    })


# =============================================================================
# C. 활동 내역(필터/정렬) + 활동 상세(AJAX)
# =============================================================================

# 기간 프리셋
_PERIODS = {
    "1m": timedelta(days=30),
    "3m": timedelta(days=90),
    "6m": timedelta(days=180),
    "1y": timedelta(days=365),
    "all": None,
}

@login_required
def activity_history_view(request):
    """
    활동 목록 페이지
    - 기간/검색/정렬 필터
    - 목록 카드에 필요한 최소 데이터만 내려줌
    """
    user = request.user

    q = (request.GET.get("q") or "").strip()
    period = request.GET.get("period") or "1m"
    sort = request.GET.get("sort") or "latest"

    qs = (
        ActivityLog.objects
        .filter(user=user)
        .select_related("shopping_list__market")
    )

    # 기간 필터
    if period not in _PERIODS:
        period = "1m"
    delta = _PERIODS[period]
    if delta is not None:
        since = timezone.now() - delta
        qs = qs.filter(visited_at__gte=since)

    # 검색(마트명)
    if q:
        qs = qs.filter(shopping_list__market__name__icontains=q)

    # 정렬
    if sort == "points":
        qs = qs.order_by("-point_earned")
    else:
        sort = "latest"
        qs = qs.order_by("-visited_at")

    # 카드용 최소 데이터 구성
    log_data = []
    for log in qs:
        sl = log.shopping_list
        market_name = sl.market.name if (sl and sl.market) else "미지정"
        log_data.append({
            "visited_at": log.visited_at,
            "market_name": market_name,
            "shopping_list_id": sl.id if sl else None,
            "point_earned": log.point_earned,
            "steps": log.steps,
            "travel_minutes": log.travel_minutes,
            "calories_kcal": log.calories_kcal,
        })

    items_count = cart_items_count(user)
    total_point = get_user_total_point(user)

    return render(request, "accounts/activity_history.html", {
        "q": q,
        "period": period,
        "sort": sort,
        "log_data": log_data,
        "cart_items_count": items_count,
        "total_point": total_point,
    })


@login_required
def activity_detail_ajax(request, shopping_list_id):
    """
    상세 모달용 AJAX
    - 기록이 있으면 그대로 사용
    - 부족하면 ‘포인트 기준 추정치’로 안전하게 보완
    """
    shopping_list = get_object_or_404(
        ShoppingList.objects.select_related('market'),
        id=shopping_list_id,
        user=request.user
    )

    ingredients = (
        ShoppingListIngredient.objects
        .filter(shopping_list=shopping_list)
        .select_related('ingredient')
    )

    log = ActivityLog.objects.filter(
        user=request.user,
        shopping_list=shopping_list
    ).first()

    point_earned = 0
    distance_km = 0.0
    steps = None
    travel_minutes = None
    calories_kcal = None
    visited_at = None  

    if log:
        point_earned = log.point_earned or 0
        visited_at = log.visited_at
        steps = log.steps
        travel_minutes = log.travel_minutes
        calories_kcal = float(log.calories_kcal) if log.calories_kcal is not None else None

    # 부족하면 포인트 기반 추정치로 보완
    if point_earned and (steps is None or travel_minutes is None or calories_kcal is None):
        fb = fallback_from_points(point_earned)
        distance_km = fb["distance_km"]
        steps = steps if steps is not None else fb["steps"]
        travel_minutes = travel_minutes if travel_minutes is not None else fb["travel_minutes"]
        calories_kcal = calories_kcal if calories_kcal is not None else fb["calories_kcal"]
    else:
        distance_km = point_earned / 100.0 if point_earned else 0.0

    return JsonResponse({
        "market_name": shopping_list.market.name if shopping_list.market else "미지정",
        "created_at": shopping_list.created_at.strftime("%Y.%m.%d %H:%M"),
        "visited_at": visited_at.strftime("%Y.%m.%d %H:%M") if visited_at else None,
        "point_earned": point_earned,
        "distance_km": f"{distance_km:.2f}",
        "steps": steps or 0,
        "travel_minutes": travel_minutes or 0,
        "calories_kcal": calories_kcal or 0,
        "ingredients": [item.ingredient.name for item in ingredients],
    })


# =============================================================================
# D. 요리법 보관함
# =============================================================================

@login_required
def my_recipes(request):
    """
    내가 저장한 레시피 목록
    - 검색(제목), 정렬(최신/가나다)
    """
    user = request.user

    q = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', 'latest')

    recipes = SavedRecipe.objects.filter(user=user)

    if q:
        recipes = recipes.filter(title__icontains=q)

    if sort == 'alpha':
        recipes = recipes.order_by('title')
    else:
        recipes = recipes.order_by('-created_at')

    items_count = cart_items_count(user)
    total_point = get_user_total_point(user)

    return render(request, 'accounts/my_recipes.html', {
        'recipes': recipes,
        'q': q,
        'sort': sort,
        "cart_items_count": items_count,
        "total_point": total_point,
    })


@login_required
def recipe_detail_ajax(request, recipe_id):
    """레시피 상세 내용을 JSON으로 반환(AJAX)"""
    recipe = get_object_or_404(SavedRecipe, id=recipe_id, user=request.user)
    return JsonResponse({
        'title': recipe.title,
        'created_at': recipe.created_at.strftime('%Y.%m.%d %H:%M'),
        'description': recipe.description,
    })


# =============================================================================
# E. 주소 설정 (목록/검색/저장/선택/삭제)
# =============================================================================

@login_required
def address_settings(request):
    """대표 주소/최근 주소 기록을 보여주는 페이지"""
    user = request.user
    current = user.selected_address
    recents = user.addresses.order_by("-created_at")[:10]

    return render(request, "accounts/address_settings.html", {
        "current": current,
        "recents": recents,
    })


@login_required
def address_search(request):
    """
    주소 검색 페이지
    - 카카오 주소 검색 유틸 호출
    - 오류는 메시지로 노출
    """
    q = (request.GET.get("q") or "").strip()
    results = []
    if q:
        try:
            results = kakao_address_search(q, size=30)
        except Exception as e:
            messages.error(request, f"주소 검색 중 오류: {e}")

    return render(request, "accounts/address_search.html", {
        "q": q,
        "results": results,
    })


@login_required
@require_POST
def address_save(request):
    """
    검색 결과에서 ‘바로 저장’ + 대표 주소로 지정
    - 좌표/문자열 조합으로 동일 주소 재사용
    """
    user = request.user

    name   = (request.POST.get("name") or "").strip()
    l1     = (request.POST.get("l1") or "").strip()
    l2     = (request.POST.get("l2") or "").strip()
    l3     = (request.POST.get("l3") or "").strip()
    detail = (request.POST.get("detail") or "").strip()
    lat    = request.POST.get("lat")
    lng    = request.POST.get("lng")

    full_address = f"{name} {detail}".strip() if detail else name

    try:
        lat_f = float(lat); lng_f = float(lng)
    except (TypeError, ValueError):
        messages.error(request, "좌표값이 올바르지 않습니다.")
        return redirect("accounts:address_search")

    addr, _created = Address.objects.get_or_create(
        user=user,
        address=full_address,
        addr_level1=l1,
        addr_level2=l2,
        addr_level3=l3,
        defaults={"latitude": lat_f, "longitude": lng_f},
    )

    # 좌표 보정
    if addr.latitude is None or addr.longitude is None:
        addr.latitude = lat_f
        addr.longitude = lng_f
        addr.save(update_fields=["latitude", "longitude"])

    apply_selected_address(user, addr) 
    return redirect("accounts:address_settings")


@login_required
def address_select_primary(request, addr_id: int):
    """최근 기록에서 주소 클릭 → 대표 주소 변경"""
    addr = get_object_or_404(Address, id=addr_id, user=request.user)
    mirror_user_address(request.user, addr) 
    return redirect("accounts:address_settings")


@login_required
def address_pick_map(request):
    """
    지도에서 위치 선택하는 페이지
    - 초기 중심: (유저 좌표) → 없으면 서울시청 좌표
    """
    user = request.user
    init_lat = user.latitude or 37.5665
    init_lng = user.longitude or 126.9780
    return render(request, "accounts/address_pick_map.html", {
        "init_lat": init_lat,
        "init_lng": init_lng,
        "kakao_js_key": getattr(settings, "KAKAO_JS_API_KEY", ""),
    })


@login_required
@require_POST
def address_save_from_map(request):
    """
    지도에서 선택한 좌표를 바로 저장 + 대표 지정
    - 동일한 address 문자열은 재사용
    """
    name = request.POST.get("name")
    l1   = request.POST.get("l1")
    l2   = request.POST.get("l2")
    l3   = request.POST.get("l3") or ""
    lat  = float(request.POST.get("lat"))
    lng  = float(request.POST.get("lng"))
    detail = (request.POST.get("detail") or "").strip()
    full = name if not detail else f"{name} {detail}"

    addr, _ = Address.objects.get_or_create(
        user=request.user, address=full,
        defaults={
            "addr_level1": l1, "addr_level2": l2, "addr_level3": l3,
            "latitude": lat, "longitude": lng
        }
    )
    mirror_user_address(request.user, addr) 
    return redirect("accounts:address_settings")


@login_required
@require_POST
def address_delete(request, addr_id: int):
    """
    주소 삭제
    - 지우려는 주소가 대표 주소라면 유저 미러필드를 함께 비움
    """
    user = request.user
    addr = get_object_or_404(Address, id=addr_id, user=user)

    with transaction.atomic():
        if user.selected_address_id == addr.id:
            user.selected_address = None
            user.address = None
            user.addr_level1 = None
            user.addr_level2 = None
            user.addr_level3 = None
            user.latitude = None
            user.longitude = None
            user.save(update_fields=[
                "selected_address", "address", "addr_level1", "addr_level2",
                "addr_level3", "latitude", "longitude"
            ])
        addr.delete()

    return redirect("accounts:address_settings")

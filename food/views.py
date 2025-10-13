from django.shortcuts import render, redirect
from .utils import *
from .models import *
from market.models import ShoppingList, ShoppingListIngredient
from point.models import UserPoint
from django.contrib import messages
from urllib.parse import urlencode
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.urls import reverse
from django.db import transaction
from django.utils import timezone
from django.http import JsonResponse, HttpResponseBadRequest
from openai import OpenAI
from typing import List
from django.core.cache import cache
import hashlib, logging
from django.utils.html import escape
from typing import Iterable, List, Sequence, Optional, Set, Tuple, Dict, Any
from typing import List


# =============================================================================
# Constants / Session Keys
# =============================================================================
PER_CART_SESSION_KEYS = (
    'extra_selected',
    'optional_selected',
    'ing_search_started',
    'optional_selected_snapshot',
    'ing_added_temp',
)

# leftover 전용 세션 키 (레시피 플로우와 완전 분리)
LEFTOVER_EXTRA_SELECTED_KEY = "leftover_extra_selected"
LEFTOVER_SESSION_KEYS = (
    LEFTOVER_EXTRA_SELECTED_KEY,  # ← 기존 'extra_selected' 제거
    'selected_ingredient_ids',
    'selected_seed',
    'recipe_chat',
    'last_recipe_text',
)


# =============================================================================
# A. 기본 페이지: 스플래시 / 메인
# =============================================================================

@login_required
def splash(request):
    return render(request, "food/splash.html")

@login_required
def main(request):
    user = request.user

    # 카테고리 탭 (없으면 전체)
    allowed = {"mart", "cafe", "trad"}
    tab_raw = request.GET.get("tab")
    tab = normalize_tab(tab_raw, allowed)
    if tab is None:
        tab = "cafe"
    # 배너 쿼리: 노출 중 + 사용자 동(동네) 타깃
    banners = get_banners_for_main(user, tab, limit=5)

    # 진행 중 장바구니
    shopping_list = (
        ShoppingList.objects
        .filter(user=user, is_done=False)
        .order_by('-created_at')
        .first()
    )
    items_count = (
        ShoppingListIngredient.objects
        .filter(shopping_list=shopping_list)
        .count()
        if shopping_list else 0
    )

    total_point = get_user_total_point(user)

    return render(request, "food/main.html", {
        "tab": tab,                         # None이면 '전체'로 취급
        "banners": banners,                 # ← 템플릿에서 for 루프로 출력
        "shoppinglist_id": shopping_list.id if shopping_list else None,
        "has_active_cart": items_count > 0,
        "cart_items_count": items_count,
        "total_point": total_point,
    })


# =============================================================================
# B. 요리를 할거야 (레시피 플로우)
#   Step1) 레시피 입력 → Step2) GPT 재료 확인 화면 → Step3) 장바구니 저장
# =============================================================================

# Step 1. 요리 입력
@login_required
def recipe_input_view(request):
    user = request.user
    initial_recipe = request.GET.get('recipe', '')

    if request.method == 'POST':
        recipe_name = request.POST.get('recipe')
        request.session['recipe_input'] = recipe_name

        # 새 요리를 입력했으므로 이전 재료들 초기화
        for k in ('basic', 'optional', 'extra_selected'):
            request.session.pop(k, None)
        return redirect('food:recipe_ingredients') 
        
    items_count = cart_items_count(user)
    total_point = get_user_total_point(user)
    today = timezone.localdate()            # 날짜만 (로컬 타임존 기준)
    today_str = today.strftime('%Y년 %m월 %d일')  # 템플릿에서 문자열이 더 편하면 사용

    return render(request, 'food/recipe_input.html', {
        'initial_recipe': initial_recipe,
        'cart_items_count': items_count,
        'total_point': total_point,
        'today': today,        
        'today_str': today_str, 
    })

# Step 2-1. GPT 분석 결과 보여주기
@login_required
def recipe_ingredient_result(request):
    recipe_name = (request.GET.get('recipe') or request.session.get('recipe_input') or "").strip()
    if not recipe_name:
        return redirect('food:recipe_input')

    # 장보기가 끝난 뒤 새 장보기를 시작하면 per-cart 세션키 초기화
    try:
        sl = get_or_create_active_shopping_list(request.user)
    except Exception:
        sl = None
    if sl:
        prev_sl_id = request.session.get('shopping_list_id')
        if prev_sl_id != sl.id:
            for k in ('extra_selected', 'optional_selected',
                      'ing_search_started', 'optional_selected_snapshot', 'ing_added_temp'):
                request.session.pop(k, None)
            request.session['shopping_list_id'] = sl.id

    prev_recipe = request.session.get('recipe_input')

    # 레시피 변경 시 세션 초기화
    if prev_recipe != recipe_name:
        request.session['recipe_input'] = recipe_name
        for k in ('basic', 'optional', 'optional_selected', 'extra_selected'):
            request.session.pop(k, None)

    if request.method == "POST":
        # 폼에서 체크된 재료들만 사용 (중복 제거 + 빈 값 제거)
        selected = extract_checked_names_from_post(request, key='ingredients')
        next_action = request.POST.get('next')

        # 검색 화면에서 장바구니(선택 목록) 보여주기 위해 세션에 현재 선택 상태 저장
        request.session['optional_selected'] = selected

        if next_action == 'search':
            return redirect('food:ingredient_search')

        if next_action == 'confirm':
            if not selected:
                messages.warning(request, "선택된 재료가 없습니다.")
                return redirect('food:recipe_ingredients')

            shopping_list = get_active_shopping_list_from_session(request)

            from django.db import transaction
            with transaction.atomic():
                # 기존 장바구니 비우고
                ShoppingListIngredient.objects.filter(shopping_list=shopping_list).delete()
                # 체크된 것만 저장
                ing_map = {
                    n: i for n, i in Ingredient.objects
                    .filter(name__in=selected)
                    .values_list('name', 'id')
                }
                bulk = [
                    ShoppingListIngredient(shopping_list=shopping_list, ingredient_id=ing_map[n])
                    for n in selected if n in ing_map
                ]
                if bulk:
                    ShoppingListIngredient.objects.bulk_create(bulk)

            request.session['shopping_list_id'] = shopping_list.id
            return redirect('food:confirm_shopping_list')

        # 기타 버튼 동작 시 자기 자신으로
        return redirect('food:recipe_ingredients')

    # ---- GET 분기 ----
    basic_filtered = request.session.get('basic')
    optional_filtered = request.session.get('optional')

    need_fetch = (
        prev_recipe != recipe_name or
        basic_filtered is None or optional_filtered is None or
        (len(basic_filtered or []) == 0 and len(optional_filtered or []) == 0)
    )

    if need_fetch:
        try:
            basic_raw, optional_raw = extract_ingredients_from_recipe(recipe_name)
            db_names = set(Ingredient.objects.values_list('name', flat=True))
            basic_filtered    = [x for x in (basic_raw or [])    if x in db_names]
            optional_filtered = [x for x in (optional_raw or []) if x in db_names]
            request.session['basic'] = basic_filtered
            request.session['optional'] = optional_filtered
        except Exception:
            basic_filtered = basic_filtered or []
            optional_filtered = optional_filtered or []

    items_count = cart_items_count(request.user)
    total_point = get_user_total_point(request.user)

    return render(request, 'food/recipe_ingredients.html', {
        'recipe': recipe_name,
        'basic': basic_filtered or [],
        'optional': optional_filtered or [],
        'optional_selected': request.session.get('optional_selected', []),
        'extra_ingredients': request.session.get('extra_selected', []),
        'items_count' : items_count,
        'total_point' : total_point,
    })

# Step 3. 장바구니 저장
@login_required
def confirm_shopping_list(request):
    # 세션 장바구니 우선 사용(없으면 생성)
    try:
        shopping_list = get_active_shopping_list_from_session(request)
    except Exception:
        shopping_list = get_or_create_active_shopping_list(request.user)

    # 1) 최종 선택 목록 수집(POST면 폼, GET이면 세션)
    if request.method == 'POST':
        selected_names = list(dict.fromkeys(request.POST.getlist('ingredients')))
        # 2) DB 갱신(교체 저장)
        with transaction.atomic():
            ShoppingListIngredient.objects.filter(shopping_list=shopping_list).delete()
            if selected_names:
                name_to_id = dict(
                    Ingredient.objects.filter(name__in=selected_names).values_list('name', 'id')
                )
                bulk = [
                    ShoppingListIngredient(shopping_list=shopping_list, ingredient_id=name_to_id[n])
                    for n in selected_names if n in name_to_id
                ]
                if bulk:
                    ShoppingListIngredient.objects.bulk_create(bulk)
    else:
        selected_names = list(dict.fromkeys(request.session.get('optional_selected', [])))

    # 3) 화면 표시용 현재 장바구니 조회(확정된 DB 기준)
    items = (
        ShoppingListIngredient.objects
        .filter(shopping_list=shopping_list)
        .select_related('ingredient')
        .order_by('ingredient__name')
    )
    ingredients_ctx = [
        {
            "name": it.ingredient.name,
            "image_url": (it.ingredient.image.url if getattr(it.ingredient, "image", None) else None)
        }
        for it in items
    ]

    # 4) extra_ingredients는 '현재 확정된 것들' 중 extra 후보만 표시
    extra_pool = set(request.session.get('extra_selected', []))
    checked_extra_ingredients = [d["name"] for d in ingredients_ctx if d["name"] in extra_pool]

    request.session['shopping_list_id'] = shopping_list.id

    items_count = cart_items_count(request.user)
    total_point = get_user_total_point(request.user)

    return render(request, 'food/recipe_result.html', {
        "shopping_list": shopping_list,
        "ingredients": ingredients_ctx,              # ← 템플릿의 ingredients와 동일
        "extra_ingredients": checked_extra_ingredients,
        'cart_items_count': items_count,
        "total_point": total_point,
    })


# =============================================================================
# C. 레시피 화면 내 "재료 직접 담기" (검색 & 세션에만 반영)
# =============================================================================

@login_required
def ingredient_search_view(request):
    # 장바구니가 바뀌었는지 확인하고, 바뀌었다면 per-cart 세션 키 초기화
    sl = get_or_create_active_shopping_list(request.user)
    prev_sl_id = request.session.get('shopping_list_id')
    if prev_sl_id != sl.id:
        for k in PER_CART_SESSION_KEYS:
            request.session.pop(k, None)
        request.session['shopping_list_id'] = sl.id

    raw = request.GET.get('search')
    search_query = (raw or '').strip()
    did_click_search = request.GET.get('action') == 'search'

    if did_click_search and search_query == '':
        messages.warning(request, "검색어를 입력해주세요.")
        return redirect('food:ingredient_search')

    # 최근 검색어 업데이트
    if did_click_search and search_query:
        update_recent_searches(request.session, search_query, key='recent_searches', maxlen=6)

    # 장바구니 후보(세션 기반)
    extra_selected = request.session.get('extra_selected', [])
    selected_ingredients = Ingredient.objects.filter(name__in=extra_selected).order_by('name')

    if search_query:
        category_ingredients = search_ingredients_by_name(search_query, exclude_names=extra_selected)
        if did_click_search and not category_ingredients.exists():
            messages.info(request, f"‘{search_query}’에 해당하는 재료가 없습니다.")
    else:
        category_ingredients = Ingredient.objects.none()

    return render(request, 'food/recipe_ingredients_search.html', {
        'search_query': search_query,
        'category_ingredients': category_ingredients,
        'selected_ingredients': selected_ingredients,
        'recent_searches': request.session.get('recent_searches', []),
    })

# 체크박스 클릭 → 즉시 '세션(extra_selected)'에만 추가
@login_required
def add_extra_ingredient(request):
    if request.method != 'POST':
        return redirect('food:ingredient_search')

    name = (request.POST.get('ingredient') or '').strip()
    search = (request.POST.get('search') or '').strip()
    if not name:
        return redirect_with_query('food:ingredient_search', 'search', search)

    # 유효성(존재 재료) 체크만
    if not Ingredient.objects.filter(name=name).exists():
        messages.error(request, f"{name} 재료를 찾을 수 없습니다.")
    else:
        extra_selected = request.session.get('extra_selected', [])
        if name not in extra_selected:
            extra_selected.append(name)
            request.session['extra_selected'] = extra_selected
        else:
            messages.info(request, f"{name}은(는) 이미 담겨 있어요.")

    return redirect_with_query('food:ingredient_search', 'search', search)

# (세션에서만) 장바구니 후보 제거
@login_required
def delete_extra_ingredient(request, name):
    if request.method != 'POST':
        return redirect('food:ingredient_search')

    search = (request.POST.get('search') or '').strip()

    extra_selected = request.session.get('extra_selected', [])
    if name in extra_selected:
        extra_selected.remove(name)
        request.session['extra_selected'] = extra_selected
    else:
        messages.info(request, f"{name}은(는) 후보에 없어요.")

    return redirect_with_query('food:ingredient_search', 'search', search)

# 최근 검색어 삭제/전체삭제
@login_required
def delete_recent_search(request, keyword):
    recent_searches = request.session.get('recent_searches', [])
    if keyword in recent_searches:
        recent_searches.remove(keyword)
        request.session['recent_searches'] = recent_searches
    return redirect('food:ingredient_search')

@login_required
def clear_recent_searches(request):
    request.session['recent_searches'] = []
    return redirect('food:ingredient_search')

# X(취소) → 이번 화면에서 새로 담은 것만 롤백(DB/세션 복원) 후 검색 화면으로
@login_required
def cancel_ingredient_search(request):
    if request.session.get('ing_search_started'):
        sl = get_active_shopping_list_from_session(request)

        added = request.session.get('ing_added_temp', [])
        if added:
            ShoppingListIngredient.objects.filter(
                shopping_list=sl,
                ingredient__name__in=added
            ).delete()

        snapshot = request.session.get('optional_selected_snapshot', [])
        request.session['optional_selected'] = snapshot

        for k in ('ing_search_started', 'optional_selected_snapshot', 'ing_added_temp'):
            request.session.pop(k, None)

    return redirect('food:recipe_ingredients')


# =============================================================================
# D. 식재료를 고를거야 (별도 메뉴: 직접 담기)
# =============================================================================

@login_required
def ingredient_input_view(request):
    # 검색어/액션
    raw = request.GET.get('search')
    search_query = (raw or '').strip()
    did_click_search = request.GET.get('action') == 'search'  # 검색 버튼 눌렀는지 여부

    # 빈 검색어 제출 방지
    if did_click_search and search_query == '':
        messages.warning(request, "검색어를 입력해주세요.")
        return redirect('food:ingredient_input')

    # 최근 검색어 업데이트(검색 버튼 눌렀을 때만)
    if did_click_search and search_query:
        update_recent_searches(request.session, search_query, key='recent_searches', maxlen=6)

    # 장바구니(확정된 항목): optional_selected 세션 기준
    optional_selected = request.session.get('optional_selected', [])
    selected_ingredients = Ingredient.objects.filter(name__in=optional_selected).order_by('name')

    # 검색 버튼 눌렀을 때만 결과 계산/표시, 이미 담긴 것 제외
    if did_click_search and search_query:
        category_ingredients = search_ingredients_by_name(search_query, exclude_names=optional_selected)
        if not category_ingredients.exists():
            messages.info(request, f"‘{search_query}’에 해당하는 재료가 없습니다.")
    else:
        category_ingredients = Ingredient.objects.none()

    items_count = cart_items_count(request.user)
    total_point = get_user_total_point(request.user)

    return render(request, 'food/ingredient_input.html', {
        'search_query': search_query,
        'category_ingredients': category_ingredients,
        'selected_ingredients': selected_ingredients,
        'recent_searches': request.session.get('recent_searches', []),
        'cart_items_count': items_count,
        'total_point': total_point,
    })

# Step 1-1. 원하는 식재료 장바구니에 추가하기
@login_required
def add_ingredient(request):
    if request.method != 'POST':
        return redirect('food:ingredient_input')

    name = (request.POST.get('ingredient') or '').strip()
    search = (request.POST.get('search') or '').strip()

    if not name:
        messages.error(request, "내용을 입력해 주세요.")
        return redirect_with_query('food:ingredient_input', 'search', search)

    try:
        ingredient = Ingredient.objects.get(name=name)
    except Ingredient.DoesNotExist:
        messages.error(request, f"{name}은(는) 존재하지 않습니다.")
        return redirect_with_query('food:ingredient_input', 'search', search)

    shopping_list = get_or_create_active_shopping_list(request.user)

    # DB 추가 (중복 생성 방지)
    _, created = ShoppingListIngredient.objects.get_or_create(
        shopping_list=shopping_list,
        ingredient=ingredient
    )

    # 세션(optional_selected) 동기화
    optional_selected = request.session.get('optional_selected', [])
    if name not in optional_selected:
        optional_selected.append(name)
        request.session['optional_selected'] = optional_selected

    if not created:
        messages.info(request, f"{name}은(는) 이미 추가되어 있어요.")

    return redirect_with_query('food:ingredient_input', 'search', search)

# Step 1-2. 장바구니에 담은 식재료 제거하기
@login_required
def delete_ingredient(request, name):
    if request.method != 'POST':
        return redirect('food:ingredient_input')

    search = (request.POST.get('search') or '').strip()

    try:
        ingredient = Ingredient.objects.get(name=name)
    except Ingredient.DoesNotExist:
        messages.error(request, f"{name}은(는) 존재하지 않습니다.")
        return redirect_with_query('food:ingredient_input', 'search', search)

    shopping_list = get_or_create_active_shopping_list(request.user)

    # DB 제거
    ShoppingListIngredient.objects.filter(
        shopping_list=shopping_list, ingredient=ingredient
    ).delete()

    # 세션(optional_selected) 동기화
    optional_selected = request.session.get('optional_selected', [])
    if name in optional_selected:
        optional_selected.remove(name)
        request.session['optional_selected'] = optional_selected

    messages.success(request, f"{name}을(를) 장바구니에서 제거했어요.")

    return redirect_with_query('food:ingredient_input', 'search', search)

# 최근 검색어 삭제/전체삭제
@login_required
def delete_recent_ingredient(request, keyword):
    recent = request.session.get('recent_searches', [])
    if keyword in recent:
        recent.remove(keyword)
        request.session['recent_searches'] = recent
    return redirect('food:ingredient_input')

@login_required
def clear_recent_ingredient(request):
    request.session['recent_searches'] = []
    return redirect('food:ingredient_input')

# Step 2. 장바구니에 담은 식재료 모아보기
@login_required
def ingredient_result_view(request):
    user = request.user

    # 진행 중인 장바구니 가져오기 (없으면 생성)
    shopping_list = get_or_create_active_shopping_list(user)

    items_count = cart_items_count(user)
    total_point = get_user_total_point(user)

    return render(request, 'food/ingredient_result.html', {
        'shopping_list': shopping_list, 'cart_items_count': items_count, 'total_point': total_point,
    })


# =============================================================================
# E. AI 대화형 추천 (감정/상황 → 요리 제안) + 아이디어 API
# =============================================================================

@login_required
def recipe_ai(request):
    user = request.user
    # 대화 세션 초기화 + system 가이드 주입
    ingredient_names = list(Ingredient.objects.values_list('name', flat=True))
    ingredient_list_str = ', '.join(ingredient_names)

    if 'chat_history' not in request.session:
        request.session['chat_history'] = [{
            "role": "system",
            "content": (
                "넌 사용자의 기분과 상황을 듣고 요리를 제안하는 친절한 요리 도우미야. "
                "반드시 **하나의 요리만** 추천하고, 추천 끝에 요리명을 큰따옴표(\")로 감싸서 제시해. "
                "간단한 설명과 필요한 재료도 덧붙여."
                "추천 요리는 반드시 사용할 수 있는 재료 목록에서 만들 수 있는 요리만 추천해"
                "재료도 마찬가지로 반드시 사용할 수 있는 재료 목록에서 설명해줘"
                f"- 사용할 수 있는 재료 목록: {ingredient_list_str}\n"
                "한 문장이 끝나면 줄바꿈을 해"
            )
        }]

    chat = request.session['chat_history']

    if request.method == 'POST':
        user_msg = (request.POST.get('message') or '').strip()
        if not user_msg:
            return redirect('food:recipe_ai')

        # 1) 사용자 메시지 추가
        chat.append({"role": "user", "content": user_msg})

        # 2) GPT 대화 호출 (모듈 함수 그대로 사용)
        try:
            gpt_reply = gpt_conversational_cook(chat)
        except Exception as e:
            messages.error(request, f"AI 응답 실패: {e}")
            return redirect('food:recipe_ai')

        # 3) GPT 응답 저장
        chat.append({"role": "assistant", "content": gpt_reply})
        request.session['chat_history'] = chat
        request.session.modified = True

        # 4) 최신 응답에서 요리명 추출 (모듈 함수 그대로 사용)
        recipe_name = extract_recipe_name_from_gpt_response(gpt_reply)

        # 5) 요리명이 있으면: 버튼용 저장 + 재료 v2 분석 시도
        if recipe_name:
            request.session['latest_recipe']  = recipe_name
            request.session['recipe_input']   = recipe_name  # 이후 재료 페이지에서 사용

            # v2 분석기로 basic/optional 미리 세션에 저장
            try:
                # DB 재료 이름 리스트
                allowed = list(Ingredient.objects.values_list('name', flat=True))
                basic_v2, optional_v2 = extract_ingredients_from_recipe_v2(
                    recipe_name, allowed_ingredients=allowed
                )
                if basic_v2 or optional_v2:
                    allowed_set = set(allowed)
                    basic_filtered    = [x for x in basic_v2    if x in allowed_set]
                    optional_filtered = [x for x in optional_v2 if x in allowed_set]
                    request.session['basic']    = basic_filtered
                    request.session['optional'] = optional_filtered
            except Exception:
                pass

        # 6) 다시 같은 페이지로 (대화 + 버튼 표시)
        return redirect('food:recipe_ai')

    items_count = cart_items_count(user)
    total_point = get_user_total_point(user)

    # 화면용 채팅 정렬: 최신 턴이 위, 턴 안에서는 user → assistant
    display_chat = format_chat_for_display(request.session['chat_history'], exclude_roles={'system'})

    # GET 렌더
    return render(request, 'food/recipe_ai.html', {
        'chat_history': display_chat,
        'latest_recipe': request.session.get('latest_recipe'),
        'user' : user,
        'cart_items_count': items_count,
        'total_point': total_point,
    })


@login_required
@require_GET
def ingredient_idea_page(request):
    """
    페이지 입장 시, 해당 재료(name)에 대한 대화 히스토리와 캐시를 초기화한다.
    (이전 재료의 히스토리 찌꺼기가 섞이지 않도록 다른 재료 히스토리도 함께 정리)
    """
    name = (request.GET.get("name") or "").strip()
    if not name:
        return HttpResponseBadRequest("name required")

    # 현재 재료의 히스토리/캐시 초기화
    sess_key = f"idea_hist:{name.lower()}"
    cache_key = f"idea:{name.lower()}"
    request.session.pop(sess_key, None)
    cache.delete(cache_key)

    # (선택) 다른 재료 히스토리까지 모두 정리
    for k in list(request.session.keys()):
        if k.startswith("idea_hist:") and k != sess_key:
            request.session.pop(k, None)

    request.session.modified = True

    return render(request, "food/ingredient_idea.html", {"name": name})


@login_required
@require_GET
def ingredient_idea_api(request):
    name = (request.GET.get("name") or "").strip()
    q    = (request.GET.get("q") or "").strip()
    if not name:
        return JsonResponse({"ok": False, "error": "name required"}, status=400)

    sess_key = f"idea_hist:{name.lower()}"
    hist = request.session.get(sess_key, [])

    try:
        if q:
            text = generate_recipe_chat(name, followup=q, history=hist)

            hist.extend([
                {"role": "user", "content": f"재료: {name}\n질문: {q}"},
                {"role": "assistant", "content": text},
            ])
            request.session[sess_key] = hist[-20:]
            request.session.modified = True
            return JsonResponse({"ok": True, "text": text})

        # ---- 초기: nocache 지원 ----
        nocache = request.GET.get("nocache") == "1"
        key = f"idea:{name.lower()}"
        text = None if nocache else cache.get(key)
        cache_hit = text is not None
        if text is None:
            text = generate_recipe_chat(name)
            cache.set(key, text, 60 * 60 * 24)

        if not hist:
            request.session[sess_key] = [{"role": "assistant", "content": text}]
            request.session.modified = True

        return JsonResponse({"ok": True, "text": text})

    except Exception as e:
        logger.exception("ingredient_idea_api error (name=%s, q=%s)", name, q)
        return JsonResponse({"ok": False, "error": f"{type(e).__name__}: {e}"}, status=502)


# =============================================================================
# F. 남은 식재료로 요리 추천 (leftover)
#   1) 재료 선택/직접 추가 → 2) 채팅 추천 → 3) 저장
# =============================================================================

# ---------- 1) 재료 선택 ----------
def reset_leftover_session(request):
    for k in LEFTOVER_SESSION_KEYS:
        request.session.pop(k, None)

@login_required
def select_recent_ingredients(request):
    user = request.user

    if request.GET.get('reset') == '1':
        reset_leftover_session(request)

    latest_list = (
        ShoppingList.objects.filter(user=user, is_done=True).first()
    )
    if not latest_list:
        items_count = cart_items_count(user)
        total_point = get_user_total_point(user)
        return render(request, 'food/leftover_save_no_ingredients.html', {
            "cart_items_count": items_count,
            "total_point": total_point,
        })

    recent_ingredients = (
        ShoppingListIngredient.objects
        .filter(shopping_list=latest_list)
        .select_related('ingredient')
    )

    # leftover 전용 추가 재료
    extra_names = request.session.get(LEFTOVER_EXTRA_SELECTED_KEY, [])
    extra_ingredients = Ingredient.objects.filter(name__in=extra_names).order_by('name')

    if request.method == 'POST':
        selected_ids = request.POST.getlist('ingredient_ids')  
        if not selected_ids:
            messages.error(request, "재료를 최소 1개 선택해주세요.")
            return redirect('food:select_recent_ingredients')

        # 1) 세션 저장(기존 동작)
        request.session['selected_ingredient_ids'] = selected_ids
        request.session['selected_seed'] = ids_seed(selected_ids)
        request.session['recipe_chat'] = []
        request.session['last_recipe_text'] = None
        request.session.modified = True 

        # 2) 우회: 쿼리스트링으로도 함께 전달
        url = reverse('food:chat_with_selected_ingredients')
        qs  = urlencode({'ids': ','.join(selected_ids)})
        return redirect(f'{url}?{qs}')

    items_count = cart_items_count(user)
    total_point = get_user_total_point(user)

    selected_ids = request.session.pop('selected_ingredient_ids', [])

    return render(request, 'food/leftover_select_recent_ingredients.html', {
        'recent_ingredients': recent_ingredients,
        'extra_ingredients': extra_ingredients,
        "cart_items_count": items_count,
        "total_point": total_point,
        "selected_ids": selected_ids,

    })

@login_required
def leftover_extra_ingredient_search_view(request):
    search_query = request.GET.get("search", "").strip()

    # 최근 검색어
    if search_query:
        update_recent_searches(request.session, search_query, key="recent_searches", maxlen=10)

    # 검색 결과
    category_ingredients = Ingredient.objects.none()
    if search_query:
        category_ingredients = search_ingredients_by_name(search_query)

    # leftover 전용 선택 목록 (중복 방지)
    extra_selected = request.session.get(LEFTOVER_EXTRA_SELECTED_KEY, [])
    extra_selected = dedupe_keep_order(extra_selected)
    request.session[LEFTOVER_EXTRA_SELECTED_KEY] = extra_selected

    selected_ingredients = Ingredient.objects.filter(
        name__in=extra_selected
    ).order_by("name")

    return render(request, "food/leftover_extra_ingredient_search.html", {
        "search_query": search_query,
        "category_ingredients": category_ingredients,
        "selected_ingredients": selected_ingredients,
        "recent_searches": request.session.get("recent_searches", []),
    })

@login_required
def leftover_add_extra_ingredient(request):
    """leftover 전용 세션에만 추가"""
    if request.method != 'POST':
        return redirect('food:leftover_extra_ingredient_search')

    name = (request.POST.get('ingredient') or '').strip()
    search = (request.POST.get('search') or '').strip()
    if not name:
        return redirect_with_query('food:leftover_extra_ingredient_search', 'search', search)

    if not Ingredient.objects.filter(name=name).exists():
        messages.error(request, f"{name} 재료를 찾을 수 없습니다.")
    else:
        extra_selected = request.session.get(LEFTOVER_EXTRA_SELECTED_KEY, [])
        if name not in extra_selected:
            extra_selected.append(name)
            request.session[LEFTOVER_EXTRA_SELECTED_KEY] = extra_selected
        else:
            messages.info(request, f"{name}은(는) 이미 담겨 있어요.")

    return redirect_with_query('food:leftover_extra_ingredient_search', 'search', search)

@login_required
def leftover_remove_extra_ingredient(request, ingredient_name):
    """leftover 전용 추가 재료 제거 (GET/POST 둘 다 허용)"""
    extra_selected = request.session.get(LEFTOVER_EXTRA_SELECTED_KEY, [])
    if ingredient_name in extra_selected:
        extra_selected.remove(ingredient_name)
        request.session[LEFTOVER_EXTRA_SELECTED_KEY] = extra_selected
    return redirect('food:leftover_extra_ingredient_search')

# (post로 부르는 삭제 뷰를 계속 쓸 거면 아래도 같은 키로 정렬)
@login_required
def leftover_delete_extra_ingredient(request, name):
    if request.method != 'POST':
        return redirect('food:leftover_extra_ingredient_search')

    search = (request.POST.get('search') or '').strip()
    extra_selected = request.session.get(LEFTOVER_EXTRA_SELECTED_KEY, [])
    if name in extra_selected:
        extra_selected.remove(name)
        request.session[LEFTOVER_EXTRA_SELECTED_KEY] = extra_selected
    else:
        messages.info(request, f"{name}은(는) 후보에 없어요.")

    return redirect_with_query('food:leftover_extra_ingredient_search', 'search', search)

@login_required
def delete_extra_recent_search(request, keyword):
    recent_searches = request.session.get('recent_searches', [])
    if keyword in recent_searches:
        recent_searches.remove(keyword)
        request.session['recent_searches'] = recent_searches
    return redirect('food:leftover_extra_ingredient_search')

@login_required
def clear_extra_recent_searches(request):
    request.session['recent_searches'] = []
    return redirect('food:leftover_extra_ingredient_search')

# ---------- 2) 채팅(자동 추천) ----------
@login_required
def chat_with_selected_ingredients(request):
    user = request.user

    # ─────────────────────────────────────────────
    # 1) 세션이 비어 있으면 ?ids=2,8,… 로부터 복구
    # ─────────────────────────────────────────────
    selected_ids = request.session.get('selected_ingredient_ids', [])

    if not selected_ids:
        ids_param = (request.GET.get('ids') or '').strip()
        if ids_param:
            # 공백 제거 + 숫자만 유지
            selected_ids = [s for s in ids_param.split(',') if s.strip().isdigit()]
            if selected_ids:
                request.session['selected_ingredient_ids'] = selected_ids
                request.session['selected_seed'] = ids_seed(selected_ids)  # utils의 ids_seed
                request.session.setdefault('recipe_chat', [])
                request.session.setdefault('last_recipe_text', None)
                request.session.modified = True

    # 그래도 없으면 선택 화면으로
    if not selected_ids:
        messages.error(request, "먼저 재료를 선택해주세요.")
        return redirect('food:select_recent_ingredients')

    # ─────────────────────────────────────────────
    # 2) 이후 기존 로직 그대로
    # ─────────────────────────────────────────────
    ingredients = Ingredient.objects.filter(id__in=selected_ids).order_by('name')
    selected_names = [i.name for i in ingredients]

    chat = request.session.get('recipe_chat', [])
    last_recipe = request.session.get('last_recipe_text')

    # 첫 진입이면 자동 추천 1회
    if not chat:
        try:
            first = call_gpt(selected_names)
        except Exception as e:
            messages.error(request, str(e))
            return redirect('food:select_recent_ingredients')
        chat = [{"role": "assistant", "content": first}]
        request.session['recipe_chat'] = chat
        request.session['last_recipe_text'] = first
        last_recipe = first

    # 후속 질문
    if request.method == 'POST':
        followup = (request.POST.get('message') or '').strip()
        if followup:
            try:
                answer = call_gpt(selected_names, followup)
            except Exception as e:
                messages.error(request, str(e))
                return redirect('food:chat_with_selected_ingredients')

            chat.append({"role": "user", "content": followup})
            chat.append({"role": "assistant", "content": answer})
            request.session['recipe_chat'] = chat
            request.session['last_recipe_text'] = answer
        return redirect('food:chat_with_selected_ingredients')

    saved_title = request.session.pop('just_saved_recipe_title', None)

    items_count = cart_items_count(user)
    total_point = get_user_total_point(user)

    display_chat = format_chat_for_display(chat)

    return render(request, 'food/leftover_chat_with_ingredients.html', {
        'selected_names': selected_names,
        'chat': display_chat,
        'last_recipe': last_recipe,
        'last_recipe_title': parse_title_and_description(last_recipe)[0] if last_recipe else None,
        'saved_title': saved_title,
        "cart_items_count": items_count,
        "total_point": total_point,
    })

# ---------- 3) 저장 ----------
@login_required
def save_last_recipe(request):
    text = request.session.get('last_recipe_text')
    if not text:
        messages.error(request, "저장할 레시피가 없습니다.")
        return redirect('food:chat_with_selected_ingredients')

    title, desc = parse_title_and_description(text)  # utils 사용
    SavedRecipe.objects.create(user=request.user, title=title[:200], description=desc)
    
    # 채팅 화면에서 모달을 띄우기 위해 세션에 제목 저장
    request.session['just_saved_recipe_title'] = title

    # 채팅 화면으로 리다이렉트 (거기서 모달 띄움)
    return redirect('food:chat_with_selected_ingredients')

# (선택) 대화 초기화
@login_required
def clear_recipe_chat(request):
    request.session.pop('recipe_chat', None)
    request.session.pop('last_recipe_text', None)
    messages.info(request, "대화를 초기화했어요.")
    return redirect('food:chat_with_selected_ingredients')


# =============================================================================
# G. 장바구니 페이지
# =============================================================================

@login_required
def cart_view(request):
    user = request.user

    shopping_list = (
        ShoppingList.objects
        .filter(user=user, is_done=False)
        .order_by('-created_at')
        .first()
    )

    if not shopping_list:
        return render(request, "food/cart.html", {"shopping_list": None, "items": []})

    items = (
        ShoppingListIngredient.objects
        .filter(shopping_list=shopping_list)
        .select_related("ingredient")
        .order_by("ingredient__name")
    )

    if request.method == "POST":
        action = request.POST.get("action")
        selected_ids = request.POST.getlist("selected")
        next_url = request.POST.get("next") or request.GET.get("next")

        # 전체 비우기
        if action == "clear_all":
            ShoppingListIngredient.objects.filter(
                shopping_list=shopping_list
            ).delete()
            # 선택 목록 세션도 초기화(선택)
            request.session.pop("optional_selected", None)

            # next가 있으면 거기로, 없으면 기존처럼 장바구니로
            if next_url:
                return redirect(next_url)
            return redirect("food:main")

        # 선택 삭제
        if action == "remove_selected":
            if selected_ids:
                ShoppingListIngredient.objects.filter(
                    id__in=selected_ids, shopping_list=shopping_list
                ).delete()
            return redirect("food:cart_view")

        # 개별 삭제
        remove_one_id = request.POST.get("remove_one")
        if remove_one_id:
            ShoppingListIngredient.objects.filter(
                id=remove_one_id, shopping_list=shopping_list
            ).delete()
            return redirect("food:cart_view")

        # 선택한 것만 confirm 으로
        if action == "go_confirm":
            if selected_ids:
                selected_names = list(
                    ShoppingListIngredient.objects
                    .filter(id__in=selected_ids, shopping_list=shopping_list)
                    .values_list("ingredient__name", flat=True)
                )
            else:
                selected_names = list(
                    ShoppingListIngredient.objects
                    .filter(shopping_list=shopping_list)
                    .values_list("ingredient__name", flat=True)
                )
            request.session["optional_selected"] = selected_names
            request.session.modified = True
            return redirect("food:confirm_shopping_list")

    return render(request, "food/cart.html", {"shopping_list": shopping_list, "items": items})
import hashlib, json, re, time, logging, os
from urllib.parse import urlencode
from typing import Optional, Set, Iterable, List, Dict, Any, Sequence, Tuple
from django.shortcuts import redirect
from django.urls import reverse
from django.apps import apps
from django.conf import settings
from openai import OpenAI
from .models import Ingredient, FoodBanner
from market.models import ShoppingList, ShoppingListIngredient
from point.models import UserPoint



# =============================================================================
# A. 외부 클라이언트/설정
#    - OpenAI 클라이언트 초기화
# =============================================================================

client = OpenAI(api_key=settings.OPENAI_API_KEY)


# =============================================================================
# B. 입력/세션 관련 순수 유틸
#    - 탭 정규화, 중복 제거, 폼 파싱, 최근검색 갱신, 리다이렉트 헬퍼
# =============================================================================

def normalize_tab(tab_raw: Optional[str], allowed: Set[str]) -> Optional[str]:
    """
    쿼리파라미터 'tab'을 허용 목록에 맞춰 정규화.
    허용되지 않으면 None 반환.
    """
    return tab_raw if (tab_raw in allowed) else None

def dedupe_keep_order(seq: Iterable[str]) -> List[str]:
    """
    중복 제거 + 기존 순서 유지.
    (템플릿/세션에서 쓰는 리스트에 안전)
    """
    seen = set()
    out: List[str] = []
    for x in seq or []:
        if not x:
            continue
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def extract_checked_names_from_post(request, key: str = "ingredients") -> List[str]:
    """
    체크박스 같은 form field에서 넘어온 문자열 리스트를
    공백 제거 후 중복 제거하여 반환.
    """
    raw_list = request.POST.getlist(key) if hasattr(request, "POST") else []
    cleaned = [s.strip() for s in raw_list if isinstance(s, str) and s.strip()]
    return dedupe_keep_order(cleaned)

def update_recent_searches(session: Dict[str, Any], query: str, *, key: str = "recent_searches", maxlen: int = 6) -> None:
    """
    최근 검색어 세션 갱신(중복 제거, 최신 우선, 길이 제한).
    """
    if not query:
        return
    try:
        recent = session.get(key, []) or []
        # 리스트가 아닐 수도 있으니 방어
        if not isinstance(recent, list):
            recent = []
        if query in recent:
            recent.remove(query)
        recent.insert(0, query)
        session[key] = recent[:maxlen]
    except Exception:
        # 세션 쓰기 실패 등은 조용히 무시 (안전 우선)
        pass

def redirect_with_query(url_name: str, param: str, value: Optional[str]):
    """
    reverse(url_name)에 ?param=value를 붙여 redirect 반환.
    value가 비어있으면 쿼리스트링 없이 이동.
    """

    base = reverse(url_name)
    if value:
        return redirect(f"{base}?{urlencode({param: value})}")
    return redirect(base)


# =============================================================================
# C. 화면/텍스트 유틸
#    - 채팅 정렬, 제목/본문 분리, ID 시드 생성
# =============================================================================

def format_chat_for_display(
    messages: Sequence[Dict[str, Any]],
    exclude_roles: Optional[Set[str]] = None,
    *,
    latest_on_top: bool = False,   # ← True면 최신이 위, False면 최신이 아래
) -> List[Dict[str, Any]]:
    """
    화면용 채팅 정렬:
    - exclude_roles에 있는 role은 제외 (예: {'system'})
    - user → assistant 페어를 유지
    - latest_on_top=False → 시간순(최신이 아래)
      latest_on_top=True  → 최신이 위로 정렬
    """
    if not isinstance(messages, (list, tuple)):
        return []

    filtered: List[Dict[str, Any]] = []
    excl = exclude_roles or set()
    for m in messages:
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        if role in excl:
            continue
        if role and "content" in m:
            filtered.append({"role": role, "content": m.get("content")})

    pairs: List[List[Dict[str, Any]]] = []
    i = 0
    n = len(filtered)
    while i < n:
        cur = filtered[i]
        nxt = filtered[i + 1] if i + 1 < n else None
        if cur.get("role") == "user" and nxt and nxt.get("role") == "assistant":
            pairs.append([cur, nxt])
            i += 2
        else:
            pairs.append([cur])
            i += 1

    # 최신이 위로 필요할 때만 뒤집기
    if latest_on_top:
        pairs.reverse()

    flat: List[Dict[str, Any]] = [m for pair in pairs for m in pair]
    return flat

def parse_title_and_description(text: str) -> Tuple[str, str]:
    """
    첫 줄을 제목, 나머지를 본문으로 분리. 빈 텍스트에도 안전.
    """
    lines = [l for l in (text or "").splitlines() if l.strip()]
    if not lines:
        return "이름 미상", (text or "")
    return lines[0].strip(), "\n".join(lines[1:]).strip()

def ids_seed(ids: Sequence[int | str]) -> str:
    """
    숫자/문자 혼합 ID 시퀀스를 정렬해 안정적인 해시(seed) 생성.
    """
    try:
        normalized = [str(int(x)) for x in ids]  # "3" -> 3 -> "3"
    except Exception:
        normalized = [str(x) for x in ids]       # 숫자 변환 실패 시 문자열로
    s = ",".join(sorted(normalized))
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


# =============================================================================
# D. 읽기 전용 DB 헬퍼
#    - 모델 조회/정렬 (변경 없음)
# =============================================================================

def search_ingredients_by_name(query: str, exclude_names: Optional[Sequence[str]] = None):
    """
    Ingredient 이름 부분일치 검색 + 지정된 이름은 제외.
    읽기 전용이며, 아무것도 못 찾으면 빈 QuerySet.
    """
    qs = Ingredient.objects.all()
    if query:
        qs = qs.filter(name__icontains=query)
    if exclude_names:
        qs = qs.exclude(name__in=list(exclude_names))
    return qs.order_by("name")

def get_banners_for_main(user, tab: Optional[str], limit: int = 5):
    """
    메인 배너 조회. FoodBanner 커스텀 매니저 사용(읽기 전용).
    """
    qs = FoodBanner.objects.active().for_user(user)
    if tab:
        # 매니저에 for_category가 없으면 AttributeError 가능성 → 방어적으로 처리
        try:
            qs = qs.for_category(tab)
        except Exception:
            pass
    return list(qs.order_by("-created_at")[: int(limit) if limit else 5])

def ingredients_qs_to_ctx(qs) -> List[Dict[str, Optional[str]]]:
    """
    Ingredient QuerySet을 템플릿 컨텍스트에 맞는 리스트로 변환.
    (name, image_url)만 안전하게 추출.
    """
    out: List[Dict[str, Optional[str]]] = []
    for ing in qs or []:
        try:
            image_url = getattr(getattr(ing, "image", None), "url", None)
            out.append({"name": ing.name, "image_url": image_url})
        except Exception:
            # 개별 항목에서 속성 접근 실패 시 해당 항목만 스킵
            continue
    return out


# =============================================================================
# E. 쇼핑리스트/포인트 헬퍼
#    - 장바구니 생성/조회/동기화, 포인트 계산
# =============================================================================

def get_or_create_active_shopping_list(user):
    active_list = ShoppingList.objects.filter(user=user, is_done=False).first()
    return active_list or ShoppingList.objects.create(user=user)

def get_shopping_list_ingredients(shopping_list):
    return Ingredient.objects.filter(
        shoppinglistingredient__shopping_list=shopping_list
    ).order_by('name')

def add_ingredients_to_list(shopping_list, ingredient_names):
    added = []
    for name in ingredient_names:
        ing, _ = Ingredient.objects.get_or_create(name=name)
        if not ShoppingListIngredient.objects.filter(shopping_list=shopping_list, ingredient=ing).exists():
            ShoppingListIngredient.objects.create(shopping_list=shopping_list, ingredient=ing)
        added.append({
            'name': ing.name,
            'image_url': ing.image.url if ing.image else None
        })
    return added

def get_active_shopping_list_from_session(request):
    list_id = request.session.get('shopping_list_id')
    if list_id:
        try:
            return ShoppingList.objects.get(id=list_id, user=request.user, is_done=False)
        except ShoppingList.DoesNotExist:
            pass

    sl = get_or_create_active_shopping_list(request.user)
    request.session['shopping_list_id'] = sl.id
    return sl

def get_user_total_point(user):
    """해당 사용자의 보유 포인트를 정수로 반환. 없으면 0."""
    if not getattr(user, "is_authenticated", False):
        return 0
    val = (
        UserPoint.objects
        .filter(user=user)
        .values_list("total_point", flat=True)
        .first()
    )
    return int(val) if val is not None else 0

def cart_items_count(user) -> int:
    shopping_list = (ShoppingList.objects.filter(user=user, is_done=False).order_by('-created_at').first())
    if not shopping_list:
        return 0
    return ShoppingListIngredient.objects.filter(shopping_list=shopping_list).count()


# =============================================================================
# F. GPT 연동 헬퍼_레시피
#    - JSON 파싱 보정, 대화/레시피 추출, 재료 분석, 프롬프트 구성 및 호출
# -----------------------------------------------------------------------------
# [목차]
# F-1. 데이터 준비/폴백 유틸
# F-2. JSON/텍스트 파싱 보정
# F-3. 대화형 요리 제안 (대화 기록 기반)
# F-4. 응답 후처리(레시피명 추출)
# F-5. 레시피→재료 추출 v1 (간단 JSON 프롬프트)
# F-6. 레시피→재료 추출 v2 (허용 재료 매핑/정규화)
# F-7. 레시피 생성용 프롬프트 빌더
# F-8. 최종 레시피 생성 호출(실패 시 폴백 포함)
# =============================================================================


# ===== F-1. 데이터 준비/폴백 유틸 =============================================

def _all_ingredient_names(max_items: int | None = None) -> str:
    """
    DB의 재료 이름을 ", "로 이어 붙인 문자열.
    GPT 프롬프트에 넘길 전체 재료 목록.
    """
    qs = Ingredient.objects.values_list("name", flat=True).order_by("name")
    if max_items:
        qs = qs[:max_items]
    return ", ".join(qs)


def _fallback_recipe_text(selected_names: list[str]) -> str:
    """
    OpenAI 호출 실패 시에도 페이지가 계속 진행되도록 하는 안전한 폴백.
    텍스트 포맷은 화면에서 기대하는 형식(제목/재료/조리방법)을 그대로 맞춤.
    """
    names = [str(n).strip() for n in selected_names if str(n).strip()]
    title = " / ".join(names[:3]) + " 간단 요리"
    ing_lines = "\n".join(f"- {n}" for n in names)
    steps = [
        "재료를 손질합니다.",
        "팬을 달구고 기름을 살짝 둘러요.",
        "재료를 넣고 3~5분간 볶거나 데칩니다.",
        "소금/후추 등 간을 맞춰요.",
        "그릇에 담아 완성합니다.",
    ]
    step_lines = "\n".join(f"{i+1}) {s}" for i, s in enumerate(steps))

    return (
        f"{title}\n"
        f"필요한 재료:\n{ing_lines}\n"
        f"조리 방법:\n{step_lines}"
    )


# ===== F-2. JSON/텍스트 파싱 보정 ============================================

def _safe_json(content: str):
    """모델이 JSON 외 텍스트를 섞어 보내도 최대한 파싱."""
    # 1) 순수 시도
    try:
        return json.loads(content)
    except Exception:
        pass
    # 2) 본문에서 가장 바깥쪽 {...} 추출
    m = re.search(r'\{.*\}', content, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return None


# ===== F-3. 대화형 요리 제안 (대화 기록 기반) ================================

def gpt_conversational_cook(chat_history):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=chat_history,
        temperature=0.7,
    )
    return response.choices[0].message.content


# ===== F-4. 응답 후처리(레시피명 추출) =======================================

def extract_recipe_name_from_gpt_response(text):
    # 큰따옴표(" ~ ") 안에 있는 내용만 추출
    match = re.search(r'["“](.+?)["”]', text)
    if match:
        return match.group(1).strip()
    return None


# ===== F-5. 레시피→재료 추출 v1 (간단 JSON 프롬프트) =========================

def extract_ingredients_from_recipe(recipe_name):
    # 모든 재료 이름을 문자열로 나열
    ingredient_names = Ingredient.objects.values_list('name', flat=True)
    ingredient_list_str = ', '.join(ingredient_names)
    prompt = (
        f'"{recipe_name}"를 만들기 위해 필요한 식재료를 아래 JSON 형식으로만 응답해줘.'
        f'조건은 무조건 우리 재료 DB 내에서만 조합해서 "{recipe_name}"를 만들기 위해 필요한 식재료들을 추천해야 돼'
        f'우리 재료 DB:\\n{ingredient_list_str}'
        f'다른 설명, 인사말, 공백, 줄바꿈 없이 **JSON 데이터만** 줘.\n\n'
        f'조건:\n'
        f'- basic: 반드시 필요한 재료 목록 (예: 된장, 두부)\n'
        f'- optional: 선택적으로 넣을 수 있는 재료 목록 (예: 고추, 소고기)\n\n'
        f'응답 형식:\n'
        f'{{\n  "basic": ["된장", "두부"],\n  "optional": ["소고기", "고추"]\n}}'
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o", 
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        content = response.choices[0].message.content.strip()

        data = json.loads(content)  # JSON 파싱
        return data.get("basic", []), data.get("optional", [])

    except json.JSONDecodeError:
        return [], []  # 파싱 실패 시 빈 리스트 반환
    except Exception as e:
        return [], []  # GPT 호출 실패 시도 빈 리스트 반환
    


# ===== F-6. 레시피→재료 추출 v2 (허용 재료 매핑/정규화) ======================

def extract_ingredients_from_recipe_v2(recipe_name, allowed_ingredients=None, model="gpt-4o"):
    """
    주어진 요리명으로 필요한 재료를 GPT에 물어보고 (basic, optional) 리스트를 돌려준다.
    - allowed_ingredients가 주어지면 그 목록에 '정규화 매핑'으로 매칭되는 항목만 반환.
    - 항상 문자열 리스트 2개를 반환하며, 실패 시 ([], []).
    """

    def norm(s: str) -> str:
        # 공백 제거 + 소문자화로 너그럽게 매칭
        return re.sub(r"\s+", "", str(s)).strip().casefold()

    # 허용 재료 매핑 (정규화된 키 -> 원본 DB명)
    allowed_map = None
    allowed_block = ""
    if allowed_ingredients:
        allowed_map = {norm(a): a for a in allowed_ingredients}
        allowed_block = "\n사용 가능한 재료 목록(이 중에서만 선택):\n" + ", ".join(allowed_ingredients)

    messages = [
        {
            "role": "system",
            "content": (
                "당신은 주어진 요리의 재료만을 JSON으로 반환하는 도우미입니다. "
                "설명/인사/코드블록/추가 텍스트 금지. 오직 JSON 오브젝트만 출력하세요."
            ),
        },
        {
            "role": "user",
            "content": (
                f'"{recipe_name}"를 만들기 위한 재료를 아래 JSON 형식으로만 응답해줘.\n'
                '응답 형식:\n{"basic": ["재료1","재료2"], "optional": ["재료3","재료4"]}\n'
                + allowed_block
            ),
        },
    ]

    try:
        res = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
        )
        content = (res.choices[0].message.content or "").strip()

        # ```json ... ``` 제거
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.IGNORECASE | re.DOTALL)

        # 혹시 앞뒤에 잡텍스트가 섞였으면 첫 번째 JSON 오브젝트만 추출
        if not content.lstrip().startswith("{"):
            m = re.search(r"\{[\s\S]*\}", content)
            if m:
                content = m.group(0)

        data = json.loads(content)
    except Exception:
        return [], []

    def clean_list(x):
        if not isinstance(x, list):
            return []
        out, seen = [], set()
        for item in x:
            s = str(item).strip()
            if not s:
                continue
            if s not in seen:
                seen.add(s)
                out.append(s)
        return out

    basic = clean_list(data.get("basic", []))
    optional = clean_list(data.get("optional", []))

    # 허용 재료 필터링 + DB 원본명으로 복구
    if allowed_map is not None:
        def map_and_filter(seq):
            mapped, seen = [], set()
            for item in seq:
                k = norm(item)
                if k in allowed_map:
                    val = allowed_map[k]
                    if val not in seen:
                        seen.add(val)
                        mapped.append(val)
            return mapped
        basic = map_and_filter(basic)
        optional = map_and_filter(optional)

    return basic, optional


# ===== F-7. 레시피 생성용 프롬프트 빌더 =====================================

def _build_prompt(selected_names: List[str], ingredient_db_list: str, followup: str = "") -> str:
    max_chars = 8000
    safe_db = (ingredient_db_list or "")[:max_chars]
    base = (
        f"다음 재료를 활용한 간단한 요리법을 추천해줘: {', '.join(selected_names)}.\n"
        "아래 형식을 반드시, 정확히 지켜줘. 다른 말은 절대 쓰지 마:\n\n"
        "첫 줄: 요리 이름 (예: 달걀볶음밥)\n"
        "줄바꿈하고 다음 줄부터 '🧺 필요한 재료'\n"
        "   - 사용할 재료 목록을 - 기호와 줄바꿈으로 나열 (재료명만, 수량/단위는 쓰지 않기)\n"
        "   - 반드시 내가 넘겨준 DB 식재료들에서만 고르기.\n"
        "다음에 '🧑‍🍳 조리 방법'\n"
        "   - 총 5단계 번호 목록으로 간결히 설명\n\n"
        "아래는 전체 식재료 DB 목록이야. 이 목록에 있는 재료만 써야 해.\n"
        f"{safe_db}\n"
    )
    if followup.strip():
        base += f"\n[사용자 추가 요청]\n{followup.strip()}\n"
    return base


# ===== F-8. 최종 레시피 생성 호출(실패 시 폴백 포함) =========================

def call_gpt(selected_names: List[str], followup: str = "") -> str:
    """
    선택 재료 + (옵션) 추가 요구사항으로 레시피 텍스트 생성.
    실패 시에도 폴백 텍스트를 반환하여 화면이 튕기지 않도록 함.
    """
    try:
        prompt = _build_prompt(selected_names, _all_ingredient_names(), followup)
        system_msg = {
            "role": "system",
            "content": (
                "넌 사용자가 가진 재료로 요리를 설계하는 한국어 요리 비서야. "
                "요청 형식을 반드시 지켜야 하며, 사족을 절대 덧붙이지 마."
            ),
        }
        user_msg = {"role": "user", "content": prompt}

        resp = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.2,
            max_tokens=700,
            messages=[system_msg, user_msg],
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text:
            raise RuntimeError("빈 응답")
        return text

    except Exception:
        # 어떤 이유로든 실패하면 즉시 폴백으로 진행 (리다이렉트 X)
        return _fallback_recipe_text(selected_names)


# =============================================================================
# G. GPT 연동 헬퍼_식재료
# =============================================================================

logger = logging.getLogger(__name__)

def generate_recipe_chat(ingredient_name: str, followup: str | None = None, history: list | None = None) -> str:
    """
    - 초기: 재료를 반드시 사용하는 2가지 요리. 숫자 넘버링 + 불릿 + (선택)팁.
    - 후속: 자유 대화(1–2문장, 공감 톤). '추천' 요구가 없으면 레시피 제안 금지.
    - 사후검증: 응답에 재료명이 없으면 1회 재시도.
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    ingredient = ingredient_name.strip()
    # 음료/액체/조미료 계열 힌트
    beverage_like = {"사이다", "콜라", "탄산수", "맥주", "와인", "소주", "식초", "간장", "케첩"}
    extra_hint = ""
    if ingredient in beverage_like:
        extra_hint = (
            f"\n\n[재료 사용 규칙]\n"
            f"- '{ingredient}'는 실제 조리 과정에서 반드시 사용(연육, 반죽, 소스/드레싱, 잡내 제거 등).\n"
            f"- 각 요리에서 '{ingredient}'가 어디에 들어가는지 한 번씩 명시."
        )

    # 공통 system
    base_sys = {
        "role": "system",
        "content": (
            "너는 한국어 요리 도우미다. 현실적이고 간결하게 답한다."
            " 과장, 이모지, 군말 금지."
        )
    }
    messages = [base_sys]
    if history:
        messages.extend(history)

    if followup:
        # ---- 대화 모드 ----
        messages.append({
            "role": "system",
            "content": (
                "지금부터는 '대화 모드'.\n"
                "- 숫자/불릿/팁 라벨 금지\n"
                "- 1–2문장, 공감 + 핵심\n"
                "- 사용자가 '추천/레시피'를 요구하지 않으면 메뉴 제안 금지\n"
                f"- 답변에 '{ingredient}'를 자연스럽게 1회 이상 언급"
            )
        })
        messages.append({
            "role": "user",
            "content": f"재료: {ingredient}\n질문: {followup}"
        })
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.5,
            max_tokens=140,
            frequency_penalty=0.6,
            messages=messages,
        )
        text = resp.choices[0].message.content.strip()
        return text

    # ---- 초기 제안 모드 ----
    messages.append({
        "role": "system",
        "content": (
            "지금부터는 '초기 제안 모드, 말투는 상냥하면서 약간 귀엽게"
            "아래 [형식]으로 딱 2가지 출력:\n"
            "[형식]\n"
            "1. 요리명\n"
            "• 핵심 조리 포인트 1줄\n"
            "• 맛/식감/상황 설명 1줄\n"
            "TIP : 있으면 1줄\n\n"
            "2. 요리명\n"
            "• 핵심 조리 포인트 1줄\n"
            "• 맛/식감/상황 설명 1줄\n"
            "TIP : 있으면 1줄\n\n"
            "- 불릿은 '•'만 사용, 각 블록 사이 빈 줄 1줄"
            f"- 모든 요리에 '{ingredient}'를 실제로 사용하는 지점을 명시"
            + extra_hint
        )
    })
    messages.append({
        "role": "user",
        "content": f"재료: {ingredient}\n위 [형식]대로 출력해. 말투는 상냥하면서 약간 귀엽게"

    })

    resp = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.35,
        max_tokens=520,
        frequency_penalty=0.4,
        messages=messages,
    )
    text = resp.choices[0].message.content.strip()

    # ---- 사후검증: 재료명이 없으면 1회 재시도 ----
    # (한글/영문 혼용 대비 소문자 비교도 수행)
    if not re.search(re.escape(ingredient), text, flags=re.IGNORECASE):
        messages.append({
            "role": "system",
            "content": (
                f"응답에 '{ingredient}' 사용이 **반드시** 포함되어야 한다. "
                "각 요리 블록에서 이 재료가 어디에 들어가는지 명확히 언급하라."
                "말투는 상냥하면서 약간 귀엽게"
            )
        })
        resp = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.3,
            max_tokens=520,
            messages=messages,
        )
        text = resp.choices[0].message.content.strip()

    return text
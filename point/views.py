from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, IntegrityError
from django.db.models import Sum, Count, F
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.crypto import get_random_string
from point.models import *  
from accounts.models import CustomUser
from .utils import *
from food.utils import get_user_total_point, cart_items_count
from datetime import timedelta

# =============================================================================
# A. 포인트 홈
# =============================================================================
@login_required
def point_home(request):
    user = request.user

    # 총 보유 포인트
    up, _ = UserPoint.objects.get_or_create(user=user)
    my_total = up.total_point

    # 이번 주, 같은 구의 로그 집합
    weekly_base = base_logs_this_week(user)

    weekly_points = weekly_points_of(weekly_base, user)
    my_rank = weekly_rank_among(weekly_base, weekly_points)

    items_count = cart_items_count(user)
    total_point = get_user_total_point(user)

    return render(request, "point/home.html", {
        "district": my_district(user),
        "total_points": my_total,
        "weekly_points": weekly_points,
        "my_rank": my_rank,
        "cart_items_count": items_count,
        "total_point": total_point,
    })


# =============================================================================
# B. 포인트 히스토리
# =============================================================================
PERIODS = {
    "1m": 30, "3m": 90, "6m": 180, "1y": 365, "all": None,
}

@login_required
def point_history(request):
    user = request.user

    period = request.GET.get("period", "1m")   # 1m,3m,6m,1y,all
    sort   = request.GET.get("sort", "latest") # latest, points

    qs = ActivityLog.objects.filter(user=user)
    qs = filter_history_period(qs, period, PERIODS)
    qs = order_history(qs, sort)

    summary = qs.aggregate(total_points=Sum("point_earned"), count=Count("id"))

    items_count = cart_items_count(user)
    total_point = get_user_total_point(user)

    return render(request, "point/history.html", {
        "logs": qs,
        "summary": summary,
        "selected": {"period": period, "sort": sort},
        "PERIODS": PERIODS,
        "cart_items_count": items_count,
        "total_point": total_point,
    })


# =============================================================================
# C. 포인트 랭킹
# =============================================================================
@login_required
def point_ranking(request):
    user = request.user

    # 이번 주 기준 로그 (같은 구)
    base_qs = base_logs_this_week(user)

    weekly_stats = weekly_stats_qs(base_qs)
    total_stats  = overall_stats_qs(user)
    weekly_top30 = weekly_top_n(base_qs, n=30)

    items_count = cart_items_count(user)
    total_point = get_user_total_point(user)

    return render(request, "point/ranking.html", {
        "district": my_district(user),
        "weekly_top30": weekly_top30,
        "weekly_stats": weekly_stats,
        "total_stats": total_stats,
        "cart_items_count": items_count,
        "total_point": total_point,
    })


# =============================================================================
# D. 바코드 사용
# =============================================================================
@login_required
def barcode_view(request):
    user_point, _ = UserPoint.objects.get_or_create(user=request.user)

    if request.method == "POST":
        # 1) PIN 확인
        code = (request.POST.get("code") or "").strip()
        if not valid_4digit(code):
            messages.error(request, "인증번호는 4자리 숫자여야 합니다.")
            return redirect("point:barcode")
        if not verify_staff_pin(code):
            messages.error(request, "인증번호가 올바르지 않습니다.")
            return redirect("point:barcode")

        # 2) 사용할 포인트 파싱/검증
        try:
            use_point = parse_use_point(request.POST.get("use_point", "0"))
        except Exception:
            messages.error(request, "포인트 입력이 올바르지 않습니다.")
            return redirect("point:barcode")

        # 3) 중복 방지 키
        request_id = ensure_request_id(request.POST.get("request_id"))
        if PointUsage.objects.filter(request_id=request_id).exists():
            messages.info(request, "이미 처리된 요청입니다.")
            return redirect("point:barcode")

        # 4) 원자적 차감 + 사용 이력
        try:
            remaining = deduct_points_and_log(request.user, use_point, request_id, memo="바코드 차감")
        except RuntimeError as e:  # 잔액 부족
            if str(e) == "INSUFFICIENT":
                messages.error(request, "포인트가 부족합니다.")
                return redirect("point:barcode")
            messages.error(request, "처리 중 오류가 발생했습니다.")
            return redirect("point:barcode")
        except IntegrityError:
            messages.info(request, "이미 처리된 요청입니다.")
            return redirect("point:barcode")
        except Exception:
            messages.error(request, "처리 중 오류가 발생했습니다.")
            return redirect("point:barcode")

        # 5) 성공 모달 데이터 세션에 저장
        request.session["point_processed"] = {
            "used": use_point,
            "remaining": remaining,
        }
        return redirect("point:barcode")

    # GET: 성공 정보 있으면 모달로 표시
    success_info = request.session.pop("point_processed", None)
    return render(request, "point/barcode.html", {
        "total_point": user_point.total_point,
        "success_info": success_info,
        "request_id": get_random_string(24),  # 중복 방지용
    })

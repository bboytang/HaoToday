from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST, require_safe

from .models import Favorite, Offer


@require_safe
def feed(request):
    channel = Offer.Channel.LEAD if request.GET.get("channel") == "lead" else Offer.Channel.VERIFIED
    now = timezone.now()
    active = Offer.objects.filter(Q(starts_at__isnull=True) | Q(starts_at__lte=now),
        channel=channel, review_state=Offer.ReviewState.AVAILABLE, ends_at__gt=now)
    q = request.GET.get("q", "").strip()[:100]
    selected = {key: request.GET.get(key, "").strip()[:80] for key in ("category", "platform", "region")}
    zero = request.GET.get("zero") == "1"
    offers = active.filter(**{k: v for k, v in selected.items() if v})
    if q:
        offers = offers.filter(Q(title__icontains=q) | Q(conditions__icontains=q) | Q(platform__icontains=q))
    if zero:
        offers = offers.filter(channel=Offer.Channel.VERIFIED, payable_fen=0, shipping_fen=0, membership_fen=0)
    choices = {}
    for field in selected:
        values = active.exclude(**{field: ""}).order_by(field).values_list(field, flat=True).distinct()
        choices[field] = sorted(set(values) | ({selected[field]} if selected[field] else set()))
    page = Paginator(offers.order_by("-checked_at", "-id"), 24).get_page(request.GET.get("page"))
    return render(request, "discovery/feed.html", {
        "offers": page, "channel": channel, "q": q, "selected": selected, "choices": choices,
        "zero": zero, "filtered": bool(q or any(selected.values()) or zero),
    })


@require_safe
def detail(request, pk):
    offer = get_object_or_404(Offer.objects.exclude(channel=Offer.Channel.DRAFT), pk=pk)
    now = timezone.now()
    if offer.review_state != Offer.ReviewState.AVAILABLE:
        status, reason = offer.get_review_state_display(), offer.status_reason
    elif offer.ends_at <= now:
        status, reason = "已结束展示", "本站记录的有效时间已结束。"
    elif offer.starts_at and offer.starts_at > now:
        status, reason = "尚未开始", "请在活动开始后再次查看。"
    else:
        status, reason = "", ""
    saved = request.user.is_authenticated and Favorite.objects.filter(user=request.user, offer=offer).exists()
    return render(request, "discovery/detail.html", {"offer": offer, "status": status, "reason": reason, "saved": saved})


@login_required
@require_safe
def account(request):
    favorites = Favorite.objects.filter(user=request.user).exclude(offer__channel=Offer.Channel.DRAFT)
    page = Paginator(favorites.select_related("offer").order_by("-saved_at", "-id"), 24).get_page(request.GET.get("page"))
    return render(request, "discovery/account.html", {"favorites": page})


@login_required
@require_POST
def favorite(request, pk):
    offer = get_object_or_404(Offer.objects.exclude(channel=Offer.Channel.DRAFT), pk=pk)
    if request.POST.get("action") == "save":
        Favorite.objects.get_or_create(user=request.user, offer=offer)
    elif request.POST.get("action") == "remove":
        Favorite.objects.filter(user=request.user, offer=offer).delete()
    else:
        from django.http import HttpResponseBadRequest
        return HttpResponseBadRequest("无效的收藏操作")
    return redirect("offer", pk=pk)

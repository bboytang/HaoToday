from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST, require_safe, require_http_methods

from .forms import SubscriptionForm
from .models import Favorite, Feedback, Offer, Subscription


def available_offers():
    now = timezone.now()
    return Offer.objects.filter(Q(starts_at__isnull=True) | Q(starts_at__lte=now),
        review_state=Offer.ReviewState.AVAILABLE, ends_at__gt=now)


@require_safe
def feed(request):
    channel = Offer.Channel.LEAD if request.GET.get("channel") == "lead" else Offer.Channel.VERIFIED
    active = available_offers().filter(channel=channel)
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
    return render(request, "discovery/detail.html", {"offer": offer, "status": status, "reason": reason, "saved": saved,
        "revision_id": offer.revisions.values_list("pk", flat=True).first(), "kinds": Feedback.Kind.choices})


@login_required
@require_safe
def account(request):
    favorites = Favorite.objects.filter(user=request.user).exclude(offer__channel=Offer.Channel.DRAFT)
    page = Paginator(favorites.select_related("offer").order_by("-saved_at", "-id"), 24).get_page(request.GET.get("page"))
    return render(request, "discovery/account.html", {"favorites": page, "reports": Feedback.objects.filter(
        user=request.user).exclude(revision__offer__channel=Offer.Channel.DRAFT).select_related("revision__offer").order_by("-pk")[:24]})


@login_required
@require_POST
def favorite(request, pk):
    offer = get_object_or_404(Offer.objects.exclude(channel=Offer.Channel.DRAFT), pk=pk)
    if request.POST.get("action") == "save":
        Favorite.objects.get_or_create(user=request.user, offer=offer)
    elif request.POST.get("action") == "remove":
        Favorite.objects.filter(user=request.user, offer=offer).delete()
    else:
        return HttpResponseBadRequest("无效的收藏操作")
    return redirect("offer", pk=pk)


@login_required
@require_POST
def feedback(request, pk):
    offer = get_object_or_404(Offer.objects.exclude(channel=Offer.Channel.DRAFT), pk=pk)
    kind = request.POST.get("kind")
    version = request.POST.get("revision", "")
    if kind not in Feedback.Kind.values or not version.isascii() or not version.isdigit() or len(version) > 18:
        return HttpResponseBadRequest("反馈类型或版本无效")
    revision = get_object_or_404(offer.revisions, pk=int(version))
    Feedback.objects.get_or_create(user=request.user, revision=revision, kind=kind)
    return redirect("account")


@login_required
@require_http_methods(["GET", "POST"])
def subscriptions(request):
    form = SubscriptionForm(request.POST if request.method == "POST" else None)
    items = Subscription.objects.filter(user=request.user).order_by("-id")
    if request.method == "POST" and form.is_valid():
        if items.count() >= 30:
            form.add_error(None, "最多保存 30 条订阅。")
        else:
            Subscription.objects.get_or_create(user=request.user, **form.cleaned_data)
            return redirect("subscriptions")
    # 只预览本人选择的一条规则，而不是为每一条订阅重复扫描活动表。
    preview = None
    if selected := request.GET.get("preview"):
        if not selected.isascii() or not selected.isdigit() or len(selected) > 18:
            return HttpResponseBadRequest("订阅编号无效")
        rule = get_object_or_404(items, pk=int(selected))
        preview = rule.matching(available_offers()).order_by("-checked_at", "-id")[:10]
    return render(request, "discovery/subscriptions.html", {"form": form, "items": items, "preview": preview})


@login_required
@require_POST
def unsubscribe(request, pk):
    get_object_or_404(Subscription, pk=pk, user=request.user).delete()
    return redirect("subscriptions")


@login_required
@require_safe
def inbox(request):
    from .models import InboxMessage
    items = InboxMessage.objects.filter(user=request.user).select_related("revision__offer").order_by("-pk")
    page = Paginator(items, 24).get_page(request.GET.get("page"))
    return render(request, "discovery/inbox.html", {"items": page})


@login_required
@require_POST
def read_message(request, pk):
    from .models import InboxMessage
    item = get_object_or_404(InboxMessage, pk=pk, user=request.user)
    InboxMessage.objects.filter(pk=item.pk, read_at__isnull=True).update(read_at=timezone.now())
    return redirect("inbox")

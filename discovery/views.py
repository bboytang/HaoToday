from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_safe

from .models import Offer


@require_safe
def feed(request):
    channel = Offer.Channel.LEAD if request.GET.get("channel") == "lead" else Offer.Channel.VERIFIED
    now = timezone.now()
    offers = Offer.objects.filter(Q(starts_at__isnull=True) | Q(starts_at__lte=now),
        channel=channel, review_state=Offer.ReviewState.AVAILABLE, ends_at__gt=now).order_by("-checked_at", "-id")[:60]
    return render(request, "discovery/feed.html", {"offers": offers, "channel": channel})


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
    return render(request, "discovery/detail.html", {"offer": offer, "status": status, "reason": reason})

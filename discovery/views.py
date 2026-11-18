from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_safe

from .models import Offer


@require_safe
def feed(request):
    channel = Offer.Channel.LEAD if request.GET.get("channel") == "lead" else Offer.Channel.VERIFIED
    offers = Offer.objects.filter(channel=channel, ends_at__gt=timezone.now()).order_by("-checked_at", "-id")[:60]
    return render(request, "discovery/feed.html", {"offers": offers, "channel": channel})


@require_safe
def detail(request, pk):
    offer = get_object_or_404(Offer.objects.exclude(channel=Offer.Channel.DRAFT), pk=pk)
    return render(request, "discovery/detail.html", {"offer": offer, "expired": offer.ends_at <= timezone.now()})

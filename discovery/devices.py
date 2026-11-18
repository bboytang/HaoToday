from datetime import timedelta
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import FileResponse, Http404, HttpResponseBadRequest, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_safe, require_POST

from .models import PushDevice, PushDelivery
from .push import cipher, public_key, validate

ASSETS = Path(__file__).with_name("pwa")


@require_safe
def asset(request, name):
    types = {"sw.js":"text/javascript","manifest.webmanifest":"application/manifest+json",
             "icon-192.png":"image/png","icon-512.png":"image/png"}
    if name not in types:
        raise Http404
    return FileResponse((ASSETS/name).open("rb"),content_type=types[name], headers={"Cache-Control":"no-cache"})


@login_required
@require_safe
def devices(request):
    items = PushDevice.objects.filter(user=request.user).order_by("-id")
    jobs = PushDelivery.objects.filter(device__user=request.user).order_by("-pk")[:12]
    return render(request,"discovery/devices.html",{"items":items,"jobs":jobs,"public_key":public_key()})


@login_required
@require_POST
def register(request):
    if not public_key() or len(request.body)>8192:
        return HttpResponseBadRequest("配置不可用或输入过长")
    try:
        data=json.loads(request.body)
        info=validate(data["subscription"])
        zone=data.get("timezone","Asia/Shanghai")
        if not isinstance(zone,str) or len(zone)>64:
            raise ValueError()
        ZoneInfo(zone)
    except (TypeError, ValueError, KeyError, ZoneInfoNotFoundError):
        return HttpResponseBadRequest("订阅格式、时区或推送服务不在支持范围")
    digest=hashlib.sha256(info["endpoint"].encode()).hexdigest()
    sealed=cipher().encrypt(json.dumps(info).encode())
    with transaction.atomic():
        if PushDevice.objects.filter(user=request.user).exclude(endpoint_hash=digest).count()>=8:
            return HttpResponseBadRequest("请先移除不使用的设备")
        item,_=PushDevice.objects.get_or_create(endpoint_hash=digest,defaults={
            "user":request.user,"sealed":sealed,"timezone":zone})
        if item.user_id!=request.user.pk:
            return HttpResponseBadRequest("请先在原账号移除此设备")
        PushDevice.objects.filter(pk=item.pk).update(sealed=sealed,timezone=zone)
    return JsonResponse({"registered":True})


@login_required
@require_POST
def action(request,pk):
    with transaction.atomic():
        item=get_object_or_404(PushDevice.objects.select_for_update(),pk=pk,user=request.user)
        mode=request.POST.get("action")
        if mode=="remove":
            item.delete()
        elif mode in ("quiet","normal"):
            was_quiet=item.quiet
            item.quiet=mode=="quiet"
            item.save(update_fields=["quiet"])
            if was_quiet and not item.quiet:
                now = timezone.now()
                PushDelivery.objects.filter(device=item, state="pending", attempts=0,
                    message__isnull=False, next_at__gt=now).update(next_at=now)
        elif mode=="test" and item.sealed:
            if not PushDelivery.objects.filter(device=item,message=None,
                    created_at__gte=timezone.now()-timedelta(minutes=1)).exists():
                PushDelivery.objects.create(device=item,next_at=timezone.now())
        else:
            return HttpResponseBadRequest("设备状态或操作无效")
    return redirect("devices")

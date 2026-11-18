"""仅支持受信推送服务；订阅信息加密存储，不记录 URL、授权头或第三方错误正文。"""
import base64
import json
import os
import re
from datetime import timedelta
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import requests
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac
from py_vapid import Vapid
from pywebpush import WebPushException, webpush

from .models import Offer, PushDelivery, Subscription


def key():
    raw = os.environ.get("HAOTODAY_VAPID_KEY")
    return Vapid.from_string(raw) if raw else None


def public_key():
    k = key()
    return base64.urlsafe_b64encode(k.public_key.public_bytes(
        Encoding.X962, PublicFormat.UncompressedPoint)).decode().rstrip("=") if k else ""


def cipher():
    return Fernet(base64.urlsafe_b64encode(salted_hmac("subscription-encryption-v1", "push",
        secret=settings.SECRET_KEY, algorithm="sha256").digest()))


def validate(data):
    endpoint = data["endpoint"]
    if not isinstance(endpoint, str) or len(endpoint)>4096 or not endpoint.isascii() or re.search(r"[\s\\#]",endpoint):
        raise ValueError("endpoint")
    u = urlsplit(endpoint)
    if u.scheme != "https" or u.netloc not in {
        "web.push.apple.com","fcm.googleapis.com","updates.push.services.mozilla.com"} or u.path in ("","/"):
        raise ValueError("provider")
    keys = {}
    for field, size in (("auth",16),("p256dh",65)):
        v = data["keys"][field]
        if not isinstance(v,str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}={0,2}",v):
            raise ValueError("encoding")
        raw = base64.urlsafe_b64decode(v.rstrip("=")+"="*(-len(v.rstrip("="))%4))
        if len(raw)!=size:
            raise ValueError("length")
        if field == "p256dh":
            ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), raw)
        keys[field]=v
    return {"endpoint":endpoint,"keys":keys}


class NoRedirect(requests.Session):
    def request(self, method, url, **kwargs):
        return super().request(method, url, **(kwargs | {"allow_redirects":False}))


def transmit(subscription, payload, ttl):
    with NoRedirect() as session:
        try:
            resp = webpush(validate(subscription), json.dumps(payload, ensure_ascii=False),
                vapid_private_key=key(), vapid_claims={"sub":"https://8kraw.cloud"}, requests_session=session,
                timeout=7, ttl=ttl)
            return resp.status_code
        except WebPushException as exc:
            return exc.response.status_code if exc.response is not None else 0
        except requests.RequestException:
            return 0


def dispatch_one():
    # 同一时间只锁一条。异常退出回滚；网络受理后意外退出可能重试，设备按 tag 折叠。
    with transaction.atomic():
        now = timezone.now()
        job = PushDelivery.objects.select_for_update(of=("self",), skip_locked=True).filter(
            state="pending",next_at__lte=now).order_by("next_at","id").first()
        if job is None:
            return False
        device = job.device
        ttl = 300
        msg = job.message
        payload = {"title":"HaoToday 测试提醒","body":"此设备已收到测试消息。","path":"/devices/","tag":f"test-{job.pk}"}
        cancel = now >= job.created_at+timedelta(hours=12) or (not msg and now >= job.created_at+timedelta(minutes=5))
        if msg:
            offer = msg.revision.offer
            payload = {"title":msg.get_kind_display(),"body":"打开 HaoToday 查看活动最新状态。",
                       "path":"/inbox/", "tag":f"offer-{offer.pk}"}
            if msg.kind != "correction":
                ttl = min(ttl, int((offer.ends_at-now).total_seconds()))
                cancel |= (ttl<=0 or offer.review_state!="available" or offer.channel=="draft" or
                    bool(offer.starts_at and offer.starts_at>now) or not any(
                    rule.matching(Offer.objects.filter(pk=offer.pk)).exists()
                    for rule in Subscription.objects.filter(user_id=device.user_id)))
            if not cancel and device.quiet and now.astimezone(ZoneInfo(device.timezone)).hour in (22,23,0,1,2,3,4,5,6,7):
                job.next_at=now+timedelta(minutes=5)
                job.save(update_fields=["next_at"])
                return True
        if cancel:
            job.state="cancelled"
        elif not key():
            job.state="failed"
        else:
            job.attempts+=1
            status = transmit(json.loads(cipher().decrypt(bytes(device.sealed))), payload, ttl)
            job.http_status = status or None
            if status in (200,201,202,204):
                job.state="accepted"
            elif status in (404,410):
                job.state="expired"
                # 保留状态记录但销毁端点材料，后续不会为其排队。
                from .models import PushDevice
                PushDevice.objects.filter(pk=device.pk).update(sealed=b"")
                PushDelivery.objects.filter(device=device,state="pending").exclude(pk=job.pk).update(state="cancelled")
            elif (not status or status==429 or status>=500) and job.attempts<3:
                job.next_at=now+timedelta(minutes=2**job.attempts)
            else:
                job.state="failed"
        job.save()
        return True

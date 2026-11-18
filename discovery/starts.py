from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from .models import Offer, StartWake


@transaction.atomic
def open_one():
    now = timezone.now()
    # 与编辑共用活动行锁。撤回/改期先提交即按新状态判断，不额外制造版本。
    offer = Offer.objects.select_for_update(of=("self",), skip_locked=True).filter(
        startwake__isnull=False).filter(Q(starts_at__lte=now) | Q(starts_at=None)).order_by("starts_at","pk").first()
    if not offer:
        return False
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT haotoday_notify_revision(r, true, %s) FROM discovery_offerrevision r
            WHERE offer_id=%s ORDER BY id DESC LIMIT 1
        """, [now, offer.pk])
    StartWake.objects.filter(offer=offer).delete()
    return True

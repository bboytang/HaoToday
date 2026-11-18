"""只读取 GamerPower 游戏赠送目录；不跟踪活动跳转、不自动发布。"""
import json
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from django.db import transaction
from django.utils import timezone

from .models import Observation, Run, Source

URL = "https://www.gamerpower.com/api/giveaways?type=game"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def fetch():
    req = Request(URL, headers={"User-Agent": "HaoToday/1.0", "Accept": "application/json"})
    with build_opener(NoRedirect).open(req, timeout=20) as response:
        if response.status == 201:
            return []
        raw = response.read(2_000_001)
        if response.status != 200 or len(raw) > 2_000_000:
            raise ValueError("unexpected catalog response")
        rows = json.loads(raw)
        if not isinstance(rows, list) or not rows:
            raise ValueError("unexpected or empty catalog")
        return rows


def sync():
    source, _ = Source.objects.get_or_create(key="gamerpower")
    if not source.enabled:
        return {"paused": True}
    run = Run.objects.create(source=source)
    try:
        with transaction.atomic():
            source = Source.objects.select_for_update().get(pk=source.pk)
            counts = dict(baseline=0, new=0, changed=0, unchanged=0)
            if source.enabled:
                ids = set()
                for row in fetch():
                    key = row["id"]
                    facts = {k: row[k] for k in ("title", "gamerpower_url", "end_date", "published_date", "platforms", "type")}
                    if type(key) is not int or key <= 0 or key in ids or not all(isinstance(v, str) and v.strip() for v in facts.values()):
                        raise ValueError("invalid catalog record")
                    link = urlsplit(facts["gamerpower_url"])
                    if (link.scheme, link.netloc) != ("https", "www.gamerpower.com") or facts["type"].lower() != "game":
                        raise ValueError("unexpected source link or type")
                    ids.add(key)
                    first = source.last_success is None
                    obj, created = Observation.objects.get_or_create(source=source, external_id=key,
                        defaults=dict(facts=facts, first_run=run, baseline=first))
                    if created:
                        counts["baseline" if first else "new"] += 1
                    elif obj.facts != facts:
                        obj.facts = facts
                        obj.save(update_fields=["facts", "updated"])
                        counts["changed"] += 1
                    else:
                        counts["unchanged"] += 1
                source.last_success = timezone.now()
                source.save(update_fields=["last_success"])
            run.status = "ok" if source.enabled else "paused"
            run.finished = timezone.now()
            run.counts = counts
            run.save()
    except Exception as exc:
        Run.objects.filter(pk=run.pk).update(status="failed", finished=timezone.now(), error=type(exc).__name__)
        raise
    return counts

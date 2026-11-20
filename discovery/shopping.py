"""折淘客京东有限窗口候选；不是完整目录，不判消失、不发布。"""
import hashlib
import html
import json
import re
import time
from urllib.parse import urlencode
from urllib.request import Request, build_opener

from django.db import transaction
from django.utils import timezone
from .gamerpower import NoRedirect
from .models import Observation, Run, Source


def fetch_page(key, page):
    query=urlencode(dict(appkey=key,plat=2,type=0,page=page,page_size=10,msg=1,interval=10))
    req=Request("https://api.zhetaoke.com:10001/api/api_xianbao.ashx?"+query,
        headers={"User-Agent":"HaoToday/1.0"})
    with build_opener(NoRedirect).open(req,timeout=25) as response:
        raw=response.read(2000001)
    if len(raw)>2000000:
        raise ValueError("oversized response")
    data=json.loads(raw)
    if data.get("status")==301:
        return []
    rows=data.get("msg")
    if data.get("status")!=200 or not isinstance(rows,list) or len(rows)>10:
        raise ValueError("unexpected response")
    return rows


def normalize(row):
    code=str(row["code"])
    content=row["content"]
    if not code.isascii() or not code.isdigit() or not 0<int(code)<2**63 or str(row["plat"])!="2":
        raise ValueError("invalid record")
    if not isinstance(content,str) or not content.strip() or len(content)>20000:
        raise ValueError("invalid content")
    text=" ".join(html.unescape(re.sub("<[^>]*>"," ",content)).split())
    # 文本相同仅标记供复核，不合并不同 SKU/规格；不保存群号和图片。
    grouped=re.sub(r"https?://\S+","[链接]",text)
    facts=dict(title=grouped[:180],text=text,product_ref=str(row.get("num_id",""))[:512],
        source_time=str(row.get("add_time",""))[:80],
        text_group=hashlib.sha256(grouped.encode()).hexdigest(),
        triage={"tier":"review","reason":"购物线报待核对规格、总实付和配送条件"})
    return int(code),facts


def sync(key):
    if not key or len(key)>512 or any(c.isspace() for c in key):
        raise ValueError("invalid key")
    # 尚未自动获准的源默认暂停，由操作员显式启用。
    source,_=Source.objects.get_or_create(key="zhetaoke-jd",defaults={"enabled":False})
    if not source.enabled:
        return {"paused":True}
    run=Run.objects.create(source=source)
    try:
        with transaction.atomic():
            source=Source.objects.select_for_update().get(pk=source.pk)
            if not source.enabled:
                run.status="paused"
                run.finished=timezone.now()
                run.save()
                return {"paused":True}
            baseline=not Observation.objects.filter(source=source).exists()
            entries={}
            counts=dict(rows=0,duplicate_code=0,baseline=0,new=0,changed=0,unchanged=0)
            for page in (1,2):
                if page==2:
                    time.sleep(6)
                rows=fetch_page(key,page)
                counts["rows"]+=len(rows)
                for row in rows:
                    code,facts=normalize(row)
                    if code in entries:
                        counts["duplicate_code"]+=1
                        # 实时窗口漂移时保留同批首次看到的版本，不凭页序倒退。
                        continue
                    entries[code]=facts
                if len(rows)<10:
                    break
            counts["page_cap_reached"]=len(rows)==10 and page==2
            for code,facts in entries.items():
                item,created=Observation.objects.get_or_create(source=source,external_id=code,
                    defaults=dict(facts=facts,first_run=run,baseline=baseline))
                if created:
                    counts["baseline" if baseline else "new"]+=1
                elif item.facts!=facts:
                    item.facts=facts
                    item.save(update_fields=["facts","updated"])
                    counts["changed"]+=1
                else:
                    counts["unchanged"]+=1
            # 即使最后一页不满也非完整目录；不标记已知商品消失或推进完整性水位。
            run.status="partial"
            run.finished=timezone.now()
            run.counts=counts
            run.save()
            return counts
    except Exception as exc:
        Run.objects.filter(pk=run.pk).update(status="failed",finished=timezone.now(),error=type(exc).__name__)
        raise

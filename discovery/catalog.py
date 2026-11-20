"""仅需供应方 key 的淘系低价目录；报价不是实付，不发布。"""
import json
import re
from decimal import Decimal
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener

from django.db import transaction
from django.utils import timezone
from .gamerpower import NoRedirect
from .models import Observation, Run, Source


def fen(value):
    if not isinstance(value,str) or not re.fullmatch(r"(?:0|[1-9]\d{0,7})(?:\.\d{1,2})?",value):
        raise ValueError("invalid amount")
    return int(Decimal(value)*100)


def normalize(row):
    code=str(row["code"])
    if not code.isascii() or not code.isdigit() or not 0<int(code)<2**63:
        raise ValueError("invalid code")
    fields=("title","jianjie","tao_id","item_url","coupon_info","coupon_end_time")
    if any(not isinstance(row.get(k),str) or len(row[k])>4000 for k in fields):
        raise ValueError("invalid fields")
    if not row["title"].strip() or not row["tao_id"]:
        raise ValueError("missing product")
    link=urlsplit(row["item_url"])
    if link.scheme!="https" or link.hostname not in ("uland.taobao.com","item.taobao.com","detail.tmall.com") or link.username or link.password:
        raise ValueError("unexpected product link")
    original,quote,coupon=(fen(row[k]) for k in ("size","quanhou_jiage","coupon_info_money"))
    text=row["title"]+" "+row["jianjie"]
    match=re.fullmatch(r"满(\d+(?:\.\d{1,2})?)元减(\d+(?:\.\d{1,2})?)元",row["coupon_info"])
    threshold=fen(match[1]) if match else None
    if re.search("虚拟商品|手机壁纸|发货升级",text):
        tier,reason="exclude","非目标实物或补差类商品"
    elif "瑕疵" in text:
        tier,reason="hold","明示瑕疵品，先核实质量与规格"
    elif re.search("工业橡胶|垫片|垫圈|绝缘柱",text):
        tier,reason="exclude","工业零配件，不因单价低认定大众高价值"
    elif original-coupon!=quote or (coupon and (
            not match or fen(match[2])!=coupon or threshold>original)):
        tier,reason="hold","供应方券门槛或报价计算待核对"
    else:
        tier,reason="review","供应方报价可复算；规格、运费、账号资格及券状态仍待核实"
    return int(code),dict(title=row["title"],description=row["jianjie"],product_ref=row["tao_id"],
        item_url=row["item_url"],quoted_original_fen=original,quoted_after_coupon_fen=quote,
        quoted_coupon_fen=coupon,quoted_threshold_fen=threshold,coupon_rule=row["coupon_info"],
        coupon_end_raw=row["coupon_end_time"],shipping_fen=None,
        triage={"tier":tier,"reason":reason,"version":1})


def fetch(key):
    query=urlencode(dict(appkey=key,page=1,page_size=10,sort="price_asc",price="0.0-1.0"))
    req=Request("https://api.zhetaoke.com:10001/api/api_all.ashx?"+query,headers={"User-Agent":"HaoToday/1.0"})
    with build_opener(NoRedirect).open(req,timeout=25) as response:
        raw=response.read(2000001)
    if len(raw)>2000000:
        raise ValueError("oversized response")
    data=json.loads(raw)
    if data.get("status")==301:
        return []
    rows=data.get("content")
    if data.get("status")!=200 or not isinstance(rows,list) or len(rows)>10:
        raise ValueError("unexpected catalog")
    return rows


def sync(key):
    if not key or len(key)>512 or any(c.isspace() for c in key):
        raise ValueError("invalid key")
    source,_=Source.objects.get_or_create(key="zhetaoke-tb-catalog",defaults={"enabled":False})
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
            rows=fetch(key)
            entries=[normalize(row) for row in rows]
            if len({code for code,_ in entries})!=len(entries):
                raise ValueError("duplicate catalog code")
            first=not Observation.objects.filter(source=source).exists()
            counts=dict(baseline=0,new=0,changed=0,unchanged=0,exclude=0,hold=0,review=0,page_cap_reached=len(rows)==10)
            for code,facts in entries:
                counts[facts["triage"]["tier"]]+=1
                item,created=Observation.objects.get_or_create(source=source,external_id=code,
                    defaults=dict(facts=facts,first_run=run,baseline=first))
                if created:
                    counts["baseline" if first else "new"]+=1
                elif item.facts!=facts:
                    item.facts=facts
                    item.save(update_fields=["facts","updated"])
                    counts["changed"]+=1
                else:
                    counts["unchanged"]+=1
            run.status="partial"
            run.finished=timezone.now()
            run.counts=counts
            run.save()
            return counts
    except Exception as exc:
        Run.objects.filter(pk=run.pk).update(status="failed",finished=timezone.now(),error=type(exc).__name__)
        raise

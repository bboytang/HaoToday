"""人工核对的公开公告录入。只读 JSON，不抓取网址，不自动升为已验证。"""
import json
import sys

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from discovery.models import Observation, Offer, Run, Source


class Command(BaseCommand):
    help = "从标准输入校验人工公告；默认不写库，--save-draft 才保存草稿"

    def add_arguments(self, parser):
        parser.add_argument("--save-draft", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        raw = sys.stdin.read(20001)
        try:
            if len(raw)>20000:
                raise ValueError()
            data = json.loads(raw)
            required = {"external_id","publisher","title","category","cost","conditions","steps",
                "official_url","evidence_url","evidence","checked_at","ends_at"}
            if not isinstance(data,dict) or not required<=data.keys()<=required|{"starts_at","platform","region"}:
                raise ValueError()
            ref = data.pop("external_id")
            if type(ref) is not int or not 0<ref<2**63 or not all(isinstance(v,str) and v.strip() for v in data.values()):
                raise ValueError()
            publisher = data.pop("publisher").strip()
            for field in ("checked_at","ends_at","starts_at"):
                if field in data:
                    dt = parse_datetime(data[field])
                    if dt is None or timezone.is_naive(dt):
                        raise ValueError()
                    data[field]=dt
            if data["checked_at"]>timezone.now() or data["ends_at"]<=timezone.now():
                raise ValueError()
            if not all(data[f].startswith("https://") for f in ("official_url","evidence_url")):
                raise ValueError()
        except ValueError as exc:
            raise CommandError("字段、HTTPS 入口或带时区的时间无效；请核对录入说明。") from exc

        source,_=Source.objects.select_for_update().get_or_create(key="manual-official",defaults={"enabled":False})
        if source.enabled:
            raise CommandError("人工来源不能启用自动采集")
        ob=Observation.objects.filter(source=source,external_id=ref).first()
        if ob:
            if ob.facts.get("url")!=data["evidence_url"] or ob.facts.get("publisher")!=publisher:
                raise CommandError("人工编号已被其他来源依据占用")
            existing=Offer.objects.filter(observation=ob).first()
            if not existing or any(getattr(existing,k)!=v for k,v in data.items()):
                raise CommandError("同编号已有不同记录；请在审核后台复核，不覆盖")
            return f"已存在 #{existing.pk}，未写入"
        run=Run.objects.create(source=source,status="manual",finished=timezone.now(),counts={"manual":1})
        ob=Observation.objects.create(source=source,external_id=ref,first_run=run,baseline=False,
            facts={"url":data["evidence_url"],"publisher":publisher,"title":data["title"],"method":"人工核对公开公告"})
        offer=Offer(observation=ob,channel=Offer.Channel.DRAFT,**data)
        try:
            offer.full_clean()
        except ValidationError as exc:
            raise CommandError("草稿校验失败："+str(exc)) from exc
        if not options["save_draft"]:
            transaction.set_rollback(True)
            return "校验通过，未保存记录"
        offer.save(force_insert=True)
        return f"已保存草稿 #{offer.pk}，未发布"

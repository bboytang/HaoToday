import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from discovery.shopping import sync, review_saved
from discovery.catalog import sync as sync_catalog


class Command(BaseCommand):
    help="有限采样京东线报，只存内部候选，不发布、不通知"
    def add_arguments(self,parser):
        parser.add_argument("--catalog",action="store_true",help="有限淘系商品目录，仅候选，不发布")
        parser.add_argument("--review-saved",action="store_true",help="仅重审内部存量，不联网、不发布")
        parser.add_argument("--key-file",default="/run/secrets/zhetaoke-key")
    def handle(self,*args,**options):
        try:
            if options["catalog"] and options["review_saved"]:
                raise ValueError("incompatible options")
            if options["review_saved"]:
                return json.dumps(review_saved())
            return json.dumps((sync_catalog if options["catalog"] else sync)(Path(options["key_file"]).read_text().strip()))
        except Exception as exc:
            # HTTP 异常字符串可能包含带 appkey 的 URL，禁止输出原文和 traceback。
            raise CommandError("购物采样失败："+type(exc).__name__) from None

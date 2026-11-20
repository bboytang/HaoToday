import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from discovery.shopping import sync


class Command(BaseCommand):
    help="有限采样京东线报，只存内部候选，不发布、不通知"
    def add_arguments(self,parser):
        parser.add_argument("--key-file",default="/run/secrets/zhetaoke-key")
    def handle(self,*args,**options):
        try:
            return json.dumps(sync(Path(options["key_file"]).read_text().strip()))
        except Exception as exc:
            # HTTP 异常字符串可能包含带 appkey 的 URL，禁止输出原文和 traceback。
            raise CommandError("购物采样失败："+type(exc).__name__) from None

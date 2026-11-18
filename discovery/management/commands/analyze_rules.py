import json
import sys
from urllib.error import URLError

from django.core.management.base import BaseCommand, CommandError

from discovery.glm import analyze


class Command(BaseCommand):
    help = "从标准输入读取经人工脱敏的公开条款，用智谱摘录，不发布。"

    def handle(self, *args, **options):
        try:
            item = analyze(sys.stdin.read(8001))
        except (ValueError, KeyError, TypeError, IndexError, URLError, TimeoutError) as exc:
            raise CommandError(f"AI 分析不可用（{type(exc).__name__}）；仍可人工核验。") from None
        return json.dumps({"digest": item.digest, "excerpts": item.excerpts, "usage": item.usage}, ensure_ascii=False)

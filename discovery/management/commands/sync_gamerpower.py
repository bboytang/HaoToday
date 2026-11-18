import json

from django.core.management.base import BaseCommand

from discovery.gamerpower import sync


class Command(BaseCommand):
    help = "采集 GamerPower 游戏线索；不发布、不通知。"

    def handle(self, *args, **options):
        return json.dumps(sync())

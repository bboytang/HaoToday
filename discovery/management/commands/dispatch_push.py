from django.core.management.base import BaseCommand
from discovery.starts import open_one
from discovery.push import dispatch_one


class Command(BaseCommand):
    help = "处理最多 20 条到期设备投递，不输出端点。"

    def handle(self, *args, **options):
        opened = 0
        while opened < 20 and open_one():
            opened += 1
        n = 0
        while n < 20 and dispatch_one():
            n += 1
        return f"opened={opened} processed={n}"

import io
import json
from datetime import timedelta
from unittest.mock import patch

from django.core.management import call_command, CommandError
from django.test import TestCase
from django.utils import timezone
from .models import Observation, Offer, Run, Source


class NoticeTests(TestCase):
    def setUp(self):
        now=timezone.now()
        self.data=dict(external_id=15,publisher="示例机构",title="测试场次",category="生活服务",
            cost="未知",conditions="待确认",steps="查看原文",evidence="核对时间但未实领",
            official_url="https://example.org/event",evidence_url="https://example.org/event",
            checked_at=now.isoformat(),ends_at=(now+timedelta(days=1)).isoformat())

    def record(self,save=False):
        with patch("sys.stdin",io.StringIO(json.dumps(self.data))):
            return call_command("record_notice",save_draft=save,stdout=io.StringIO())

    def test_preview_replay_and_conflict(self):
        self.record()
        self.assertFalse(Source.objects.exists())
        self.record(True)
        self.record(True)
        self.assertEqual((Run.objects.count(),Observation.objects.count(),Offer.objects.count()),(1,1,1))
        offer=Offer.objects.get()
        self.assertEqual(self.client.get(f"/offers/{offer.pk}/").status_code,404)
        self.data["conditions"]="换条件"
        with self.assertRaises(CommandError): self.record(True)
        self.assertEqual(Offer.objects.get().conditions,"待确认")

    def test_no_channel_override_or_invalid_category(self):
        self.data["channel"]="verified"
        with self.assertRaises(CommandError): self.record(True)
        del self.data["channel"]
        self.data["category"]="支付"
        with self.assertRaises(CommandError): self.record(True)
        self.assertFalse(Run.objects.exists())

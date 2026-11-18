from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from .models import Observation, Offer, Run, Source


class PublicTests(TestCase):
    def setUp(self):
        source = Source.objects.create(key="gamerpower")
        observation = Observation.objects.create(source=source, external_id=2, facts={"title": "内部测试原文"},
            baseline=True, first_run=Run.objects.create(source=source))
        self.offer = Offer.objects.create(observation=observation, title="测试权益", category="数字权益",
            official_url="https://example.org/claim", checked_at=timezone.now(),
            ends_at=timezone.now() + timedelta(hours=1))
        self.url = f"/offers/{self.offer.pk}/"

    def test_internal_data_never_public(self):
        self.assertNotContains(self.client.get("/?channel=draft"), self.offer.title)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_lead_only_in_its_channel(self):
        self.offer.channel = "lead"
        self.offer.save()
        self.assertNotContains(self.client.get("/"), self.offer.title)
        self.assertContains(self.client.get("/?channel=lead"), self.offer.title)
        detail = self.client.get(self.url)
        self.assertContains(detail, self.offer.official_url)
        self.assertContains(detail, "https://www.gamerpower.com/")
        self.assertNotContains(detail, "内部测试原文")

    def test_expired_not_actionable(self):
        self.offer.channel = "verified"
        self.offer.ends_at = timezone.now() - timedelta(seconds=1)
        self.offer.save()
        self.assertNotContains(self.client.get("/"), self.offer.title)
        response = self.client.get(self.url)
        self.assertContains(response, "已结束展示")
        self.assertNotContains(response, 'class="go"')

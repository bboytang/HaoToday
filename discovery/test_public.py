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

    def prepare_verified(self):
        for field in ("conditions", "evidence", "steps", "reward_basis", "price_basis", "eligibility_basis", "time_basis"):
            setattr(self.offer, field, "已核对测试条款")
        self.offer.evidence_url = "https://example.org/rules"
        self.offer.payable_fen = 1
        self.offer.shipping_fen = 600
        self.offer.membership_fen = 0
        self.offer.channel = "verified"

    def test_unknown_shipping_or_missing_eligibility_cannot_publish(self):
        from django.db import IntegrityError, transaction
        self.prepare_verified()
        self.offer.save()
        for invalid in ({"shipping_fen": None}, {"membership_fen": None}, {"eligibility_basis": "   "}, {"time_basis": ""}):
            with self.subTest(invalid=invalid), self.assertRaises(IntegrityError), transaction.atomic():
                Offer.objects.filter(pk=self.offer.pk).update(**invalid)
        self.assertContains(self.client.get("/"), "¥6.01")
        self.assertContains(self.client.get(self.url), "资格依据")

    def test_expired_not_actionable(self):
        self.prepare_verified()
        self.offer.channel = "verified"
        self.offer.ends_at = timezone.now() - timedelta(seconds=1)
        self.offer.save()
        self.assertNotContains(self.client.get("/"), self.offer.title)
        response = self.client.get(self.url)
        self.assertContains(response, "已结束展示")
        self.assertNotContains(response, 'class="go"')

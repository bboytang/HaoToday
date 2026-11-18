from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase
from django.utils import timezone

from .models import InboxMessage, Observation, Offer, Run, Source, Subscription


class InboxTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("reader")
        self.other = get_user_model().objects.create_user("other")
        source = Source.objects.create(key="test")
        observation = Observation.objects.create(source=source, external_id=1, facts={}, baseline=True,
            first_run=Run.objects.create(source=source))
        self.offer = Offer.objects.create(observation=observation, title="PC 权益", platform="商店", category="数字权益",
            region="上海", checked_at=timezone.now(), ends_at=timezone.now()+timedelta(days=1),
            payable_fen=1000, shipping_fen=0, membership_fen=0, official_url="https://example.org/",
            evidence_url="https://example.org/rules", cost="示例", conditions="账号", steps="领取", evidence="规则",
            reward_basis="权益", price_basis="价格", eligibility_basis="资格", time_basis="时间")
        Subscription.objects.create(user=self.user, keyword="pc")
        Subscription.objects.create(user=self.user, region="上海", platform="商店")
        Subscription.objects.create(user=self.other, keyword="PC", region="北京", leads=True)

    def change(self, **kwargs):
        Offer.objects.filter(pk=self.offer.pk).update(**kwargs)

    def test_delivery_price_threshold_correction_and_privacy(self):
        self.change(channel="lead")
        self.assertFalse(InboxMessage.objects.exists())
        self.change(channel="verified")
        self.change(title="PC 标题润色")
        self.change(payable_fen=950)
        self.assertEqual(InboxMessage.objects.count(), 1)
        self.change(payable_fen=800)
        self.change(payable_fen=0)
        Subscription.objects.filter(user=self.user).delete()
        self.change(review_state="withdrawn",status_reason="优惠条件更正")
        qs = InboxMessage.objects.order_by("id")
        self.assertEqual(list(qs.values_list("kind",flat=True)),["published","price_drop","price_drop","correction"])
        self.assertFalse(qs.exclude(user=self.user).exists())
        self.client.force_login(self.other)
        path = f"/inbox/{qs.first().pk}/read/"
        self.assertEqual(self.client.post(path).status_code, 404)
        self.client.force_login(self.user)
        self.assertContains(self.client.get("/inbox/"), "优惠条件更正")
        self.assertRedirects(self.client.post(path), "/inbox/")
        self.assertIsNotNone(qs.first().read_at)

    def test_no_expired_backfill_or_phantom_delivery(self):
        self.change(ends_at=timezone.now()-timedelta(seconds=1),channel="verified")
        self.assertFalse(InboxMessage.objects.exists())
        self.change(channel="draft")
        with transaction.atomic():
            self.change(channel="verified", ends_at=timezone.now()+timedelta(days=1))
            self.assertEqual(InboxMessage.objects.count(),1)
            transaction.set_rollback(True)
        self.assertFalse(InboxMessage.objects.exists())

    def test_devices_queue_and_recheck_subscription_before_network(self):
        from unittest.mock import patch
        from .models import PushDevice,PushDelivery
        from .push import dispatch_one
        PushDevice.objects.create(user=self.user,endpoint_hash="fixture",sealed=b"test-only")
        self.change(channel="verified")
        job=PushDelivery.objects.get()
        self.assertEqual(job.message.user_id,self.user.pk)
        Subscription.objects.filter(user=self.user).delete()
        with patch("discovery.push.transmit") as network:
            self.assertTrue(dispatch_one())
            network.assert_not_called()
        job.refresh_from_db()
        self.assertEqual(job.state,"cancelled")

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

    def test_quiet_queue_only_sends_current_price(self):
        from datetime import timezone as tz
        from unittest.mock import patch
        from .models import PushDevice, PushDelivery
        from .push import cipher, dispatch_one
        # 上海 21:59 发出的三次更新，在 22:00 首次被 worker 处理。
        night = timezone.now().astimezone(tz.utc).replace(hour=14,minute=0,second=0,microsecond=0)
        wake = night + timedelta(hours=10)
        PushDevice.objects.create(user=self.user,endpoint_hash="test",quiet=True,
            timezone="Asia/Shanghai",sealed=cipher().encrypt(b"{}"))
        self.change(channel="verified",ends_at=wake+timedelta(hours=3))
        self.change(payable_fen=800)
        self.change(payable_fen=0)
        PushDelivery.objects.update(created_at=night-timedelta(minutes=1),next_at=night)
        with patch("discovery.push.timezone.now",return_value=night), patch("discovery.push.transmit") as network:
            while dispatch_one(): pass
            network.assert_not_called()
        qs=PushDelivery.objects.order_by("id")
        self.assertEqual(list(qs.values_list("state",flat=True)),["cancelled","cancelled","pending"])
        self.assertEqual(qs.last().next_at,wake)
        # 早晨网络恢复前，免费已经变成收费；不能把昨晚的降价当成当前价格发送。
        self.change(payable_fen=900)
        with patch("discovery.push.timezone.now",return_value=wake), patch("discovery.push.transmit") as network:
            self.assertTrue(dispatch_one())
            network.assert_not_called()
        self.assertEqual(qs.last().state,"cancelled")

    def test_device_timezone_wake_or_expire_without_network(self):
        from datetime import timezone as tz
        from unittest.mock import patch
        from .models import PushDevice, PushDelivery
        from .push import cipher, dispatch_one
        night = (timezone.now()+timedelta(days=1)).astimezone(tz.utc).replace(hour=14,minute=0,second=0,microsecond=0)
        wake = night+timedelta(hours=10)
        for zone in ("Asia/Shanghai","UTC"):
            PushDevice.objects.create(user=self.user,endpoint_hash=zone,quiet=True,
                timezone=zone,sealed=cipher().encrypt(b"{}"))
        self.change(channel="verified",ends_at=wake+timedelta(minutes=1))
        PushDelivery.objects.update(created_at=night,next_at=night)
        with patch("discovery.push.key",return_value=True), patch("discovery.push.transmit",return_value=201) as net:
            with patch("discovery.push.timezone.now",return_value=night):
                while dispatch_one(): pass
            self.assertEqual(net.call_count,1)  # UTC 14:00 的设备正常发送。
            with patch("discovery.push.timezone.now",return_value=wake-timedelta(seconds=1)):
                self.assertFalse(dispatch_one())
            with patch("discovery.push.timezone.now",return_value=wake):
                self.assertTrue(dispatch_one())
            self.assertEqual(net.call_count,2)
            self.assertEqual(net.call_args.args[-1],60)
            self.change(payable_fen=0)
            PushDelivery.objects.update(created_at=night,next_at=night)
            self.change(ends_at=wake)
            with patch("discovery.push.timezone.now",return_value=night):
                while dispatch_one(): pass
            self.assertEqual(net.call_count,3)
            self.assertEqual(PushDelivery.objects.get(device__timezone="Asia/Shanghai",message__kind="price_drop").state,"cancelled")

    def test_turning_off_quiet_wakes_waiting_job(self):
        from .models import PushDevice, PushDelivery
        d=PushDevice.objects.create(user=self.user,endpoint_hash="quiet",quiet=True,sealed=b"test")
        self.change(channel="verified")
        later=timezone.now()+timedelta(hours=3)
        PushDelivery.objects.update(next_at=later)
        self.client.force_login(self.user)
        self.client.post(f"/devices/{d.pk}/action/",{"action":"normal"})
        self.assertLess(PushDelivery.objects.get().next_at,later)

    def test_scheduled_start_wakes_once_without_new_revision(self):
        from io import StringIO
        from unittest.mock import patch
        from django.core.management import call_command
        from .models import PushDevice, PushDelivery
        PushDevice.objects.create(user=self.user,endpoint_hash="fixture",sealed=b"test")
        start = timezone.now()+timedelta(minutes=5)
        self.change(channel="verified", starts_at=start)
        self.change(title="PC 预告更新")
        revision=self.offer.revisions.first()
        # 通过启动命令驱动；不需要为已到点的活动再改一次标题。
        for now in (start-timedelta(seconds=1),start,start+timedelta(seconds=1)):
            with patch("django.utils.timezone.now",return_value=now), patch(
                    "discovery.management.commands.dispatch_push.dispatch_one",return_value=False):
                call_command("dispatch_push",stdout=StringIO())
            self.assertEqual(InboxMessage.objects.count(),int(now>=start))
        self.assertEqual(InboxMessage.objects.get().revision,revision)
        self.assertEqual(self.offer.revisions.first(),revision)
        self.assertEqual(PushDelivery.objects.count(),1)

    def test_scheduled_cancel_reschedule_expire_and_unsubscribe(self):
        from unittest.mock import patch
        from .models import StartWake
        from .starts import open_one
        start = timezone.now()+timedelta(minutes=5)
        self.change(channel="verified", starts_at=start)
        self.change(review_state="withdrawn",status_reason="取消")
        with patch("django.utils.timezone.now",return_value=start):
            self.assertFalse(open_one())
        later = start+timedelta(minutes=20)
        self.change(review_state="available",starts_at=later)
        with patch("django.utils.timezone.now",return_value=start):
            self.assertFalse(open_one())
        Subscription.objects.filter(user=self.user).delete()
        with patch("django.utils.timezone.now",return_value=later):
            self.assertTrue(open_one())
        self.assertFalse(InboxMessage.objects.exists())
        Subscription.objects.create(user=self.user, keyword="pc")
        self.change(starts_at=later+timedelta(hours=1), ends_at=later+timedelta(hours=2))
        with patch("django.utils.timezone.now",return_value=later+timedelta(hours=2)):
            self.assertTrue(open_one())
        self.assertFalse(StartWake.objects.exists())
        self.assertFalse(InboxMessage.objects.exists())

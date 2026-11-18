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

    def test_manual_official_notice_not_attributed_to_game_directory(self):
        Source.objects.update(key="manual-official")
        self.offer.channel = "lead"
        self.offer.evidence_url = "https://example.org/notice"
        self.offer.save()
        for path in (self.url, "/?channel=lead"):
            page = self.client.get(path)
            self.assertContains(page, "人工核对公告")
            self.assertContains(page, self.offer.evidence_url)
            self.assertNotContains(page, "GamerPower")

    def test_home_separates_verified_picks_from_lead_count(self):
        self.offer.channel = "lead"
        self.offer.save()
        home = self.client.get("/")
        self.assertContains(home, "今日手记")
        self.assertContains(home, "查看 1 条抢先线索")
        self.assertNotContains(home, self.offer.title)
        self.assertContains(self.client.get("/feed/?channel=lead"), self.offer.title)
        self.assertContains(self.client.get("/?channel=lead"), self.offer.title)
        Offer.objects.update(ends_at=timezone.now()-timedelta(seconds=1))
        self.assertNotContains(self.client.get("/"), "查看 1 条抢先线索")

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

    def test_shopping_gift_cannot_hide_required_purchase(self):
        from django.db import IntegrityError, transaction
        self.prepare_verified()
        self.offer.category="购物"
        self.offer.no_asset_exchange=True
        self.offer.payable_fen=0
        self.offer.shipping_fen=0
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.offer.save()  # 赠品未标明是否需要另购，不得进入已验证。
        self.offer.required_purchase_fen=9900
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.offer.save()
        self.offer.payable_fen=9900
        self.offer.save()
        self.assertContains(self.client.get(self.url),"¥99.00")
        self.assertNotContains(self.client.get("/feed/?zero=1"),self.offer.title)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Offer.objects.filter(pk=self.offer.pk).update(payable_fen=0)
        self.offer.required_purchase_fen=0
        self.offer.payable_fen=0
        self.offer.save()
        self.assertContains(self.client.get("/feed/?zero=1"),self.offer.title)

    def test_trade_in_is_not_free_merely_because_no_cash_changes_hands(self):
        from django.db import IntegrityError, transaction
        self.prepare_verified()
        self.offer.category="购物"
        self.offer.conditions="须交付三本符合条件的旧书才能换一本"
        self.offer.required_purchase_fen=self.offer.payable_fen=self.offer.shipping_fen=0
        self.offer.channel="lead"
        self.offer.save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Offer.objects.filter(pk=self.offer.pk).update(channel="verified")
        self.assertContains(self.client.get("/feed/?channel=lead"),self.offer.title)
        self.assertNotContains(self.client.get("/feed/?zero=1"),self.offer.title)

    def test_expired_not_actionable(self):
        self.prepare_verified()
        self.offer.channel = "verified"
        self.offer.ends_at = timezone.now() - timedelta(seconds=1)
        self.offer.save()
        self.assertNotContains(self.client.get("/"), self.offer.title)
        response = self.client.get(self.url)
        self.assertContains(response, "已结束展示")
        self.assertNotContains(response, 'class="go"')

    def test_unavailable_link_has_explanation_without_stale_directions(self):
        self.offer.channel = "lead"
        self.offer.steps = "不应再展示的步骤"
        for state in ("suspect", "withdrawn"):
            self.offer.review_state = state
            self.offer.status_reason = "资格规则有误，已暂停"
            self.offer.save()
            self.assertNotContains(self.client.get("/?channel=lead"), self.offer.title)
            response = self.client.get(self.url)
            self.assertContains(response, self.offer.status_reason)
            self.assertNotContains(response, self.offer.official_url)
            self.assertNotContains(response, self.offer.steps)

    def test_future_offer_not_actionable(self):
        self.offer.channel = "lead"
        self.offer.conditions = "仅限指定设备"
        self.offer.evidence = "未验证个人资格"
        self.offer.steps = "未到点请勿办理"
        self.offer.starts_at = timezone.now() + timedelta(minutes=10)
        self.offer.save()
        self.assertNotContains(self.client.get("/?channel=lead"), self.offer.title)
        response = self.client.get(self.url)
        self.assertContains(self.client.get("/"), "即将开始")
        self.assertContains(self.client.get("/"), self.offer.title)
        self.assertContains(response, self.offer.conditions)
        self.assertContains(response, self.offer.evidence)
        self.assertNotContains(response, self.offer.steps)
        self.assertContains(response, "尚未开始")
        self.assertNotContains(response, self.offer.official_url)

    def test_hidden_previews_not_listed(self):
        self.offer.starts_at = timezone.now() + timedelta(minutes=10)
        self.offer.save()
        self.assertNotContains(self.client.get("/"), self.offer.title)
        self.offer.channel = "lead"
        self.offer.review_state = "withdrawn"
        self.offer.status_reason = "活动取消"
        self.offer.conditions = "已作废的规则"
        self.offer.save()
        self.assertNotContains(self.client.get("/"), self.offer.title)
        self.assertNotContains(self.client.get(self.url), self.offer.conditions)

    def test_filtered_feed_uses_only_visible_public_fields(self):
        self.offer.platform = "测试商店"
        self.offer.region = "上海"
        self.offer.save()
        params = dict(channel="lead", q="测试权益", category="数字权益", platform="测试商店", region="上海")
        self.assertNotContains(self.client.get("/"), "测试商店")
        self.offer.channel = "lead"
        self.offer.save()
        response = self.client.get("/", params)
        self.assertEqual(list(response.context["offers"]), [self.offer])
        for other in ({"region":"北京"}, {"platform":"其他"}, {"category":"购物"}, {"q":"内部测试原文"}, {"zero":"1"}):
            self.assertEqual(list(self.client.get("/", params | other).context["offers"]), [])
        self.offer.review_state = "withdrawn"
        self.offer.status_reason = "测试撤回"
        self.offer.save()
        self.assertNotContains(self.client.get("/?channel=lead"), "测试商店")

    def test_free_filter_counts_all_required_fees(self):
        self.prepare_verified()
        self.offer.payable_fen = 0
        self.offer.save()
        self.assertEqual(list(self.client.get("/?zero=1").context["offers"]), [])
        self.offer.shipping_fen = 0
        self.offer.save()
        self.assertEqual(list(self.client.get("/?zero=1").context["offers"]), [self.offer])

    def test_private_favorites_and_draft_visibility(self):
        from django.contrib.auth import get_user_model
        from .models import Favorite
        users = [get_user_model().objects.create_user(name) for name in ("one", "two")]
        path = f"{self.url}favorite/"
        self.assertEqual(self.client.post(path, {"action":"save"}).status_code, 302)
        self.client.force_login(users[0])
        self.assertEqual(self.client.post(path, {"action":"save"}).status_code, 404)
        self.offer.channel = "lead"
        self.offer.save()
        self.assertEqual(self.client.get(path).status_code, 405)
        for _ in range(2):
            self.assertRedirects(self.client.post(path, {"action":"save"}), self.url)
        self.assertEqual(Favorite.objects.count(), 1)
        self.assertContains(self.client.get("/account/"), self.offer.title)
        self.client.force_login(users[1])
        self.assertNotContains(self.client.get("/account/"), self.offer.title)
        self.client.post(path, {"action":"remove","user":users[0].pk})
        self.assertEqual(Favorite.objects.count(), 1)
        self.offer.channel = "draft"
        self.offer.save()
        self.client.force_login(users[0])
        self.assertNotContains(self.client.get("/account/"), self.offer.title)

    def test_session_login_and_csrf(self):
        from django.contrib.auth import get_user_model
        from django.test import Client
        get_user_model().objects.create_user("tester", password="Only-For-Test-123")
        c = Client(enforce_csrf_checks=True)
        self.assertContains(c.get("/account/login/"), "个人账号")
        self.assertEqual(c.post("/account/login/", {"username":"tester"}).status_code, 403)
        self.assertRedirects(c.post("/account/login/", {"username":"tester","password":"Only-For-Test-123",
            "csrfmiddlewaretoken":c.cookies["csrftoken"].value}), "/account/")
        self.assertEqual(c.post(f"{self.url}favorite/", {"action":"save"}).status_code, 403)
        self.assertEqual(c.post("/account/logout/", {"csrfmiddlewaretoken":c.cookies["csrftoken"].value}).status_code, 302)
        self.assertEqual(c.get("/account/").status_code, 302)

    def test_feedback_is_private_versioned_and_not_automatic_withdrawal(self):
        from django.contrib.auth import get_user_model
        from .models import Feedback
        self.offer.channel = "lead"
        self.offer.save()
        version = self.offer.revisions.first().pk
        self.client.force_login(get_user_model().objects.create_user("reporter"))
        data = dict(revision=version, kind="price")
        for _ in range(2):
            self.assertRedirects(self.client.post(self.url+"feedback/", data), "/account/")
        self.assertEqual(Feedback.objects.count(), 1)
        self.assertContains(self.client.get("/account/"), "待复核")
        self.offer.refresh_from_db()
        self.assertEqual(self.offer.review_state, "available")
        self.assertEqual(self.client.post(self.url+"feedback/", data | {"revision":0}).status_code, 404)
        self.client.force_login(get_user_model().objects.create_user("other"))
        self.assertNotContains(self.client.get("/account/"), "待复核")

    def test_subscription_preview_and_ownership(self):
        from django.contrib.auth import get_user_model
        from .models import Subscription
        self.offer.channel = "lead"
        self.offer.save()
        self.client.force_login(get_user_model().objects.create_user("subscriber"))
        path = "/subscriptions/"
        self.assertContains(self.client.post(path, {}), "至少填写一个")
        for _ in range(2):
            self.assertRedirects(self.client.post(path, {"keyword":"测试"}), path)
        rule = Subscription.objects.get()
        preview = f"{path}?preview={rule.pk}"
        self.assertContains(self.client.get(preview), "暂无符合条件")
        rule.leads = True
        rule.save()
        self.assertContains(self.client.get(preview), self.offer.title)
        self.offer.review_state = "suspect"
        self.offer.status_reason = "测试暂停"
        self.offer.save()
        self.assertNotContains(self.client.get(preview), self.offer.title)
        self.client.force_login(get_user_model().objects.create_user("other-sub"))
        self.assertEqual(self.client.get(preview).status_code, 404)
        self.assertEqual(self.client.post(f"{path}{rule.pk}/remove/").status_code, 404)

    def test_feed_change_signal_respects_filters_and_public_state(self):
        path="/feed/state/?channel=lead&q=测试"
        def check(tag):
            return self.client.head(path,HTTP_IF_NONE_MATCH=tag)
        initial=self.client.get("/feed/?channel=lead&q=测试")
        tag=initial.context["feed_etag"]
        self.assertEqual(check(tag).status_code,304)
        Offer.objects.filter(pk=self.offer.pk).update(title="测试草稿修改")
        self.assertEqual(check(tag).status_code,304)
        Offer.objects.filter(pk=self.offer.pk).update(channel="lead",title="无关")
        self.assertEqual(check(tag).status_code,304)
        Offer.objects.filter(pk=self.offer.pk).update(title="测试权益")
        response=check(tag)
        self.assertEqual(response.status_code,200)
        updated=response["ETag"]
        self.assertEqual(check(updated).status_code,304)
        Offer.objects.filter(pk=self.offer.pk).update(cost="需要运费")
        self.assertNotEqual(check(updated)["ETag"],updated)
        Offer.objects.filter(pk=self.offer.pk).update(ends_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(check(tag).status_code,304)

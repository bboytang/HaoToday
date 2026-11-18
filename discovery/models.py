from django.db import models


class Source(models.Model):
    key = models.SlugField(unique=True)
    enabled = models.BooleanField(default=True)
    last_success = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.key


class Run(models.Model):
    source = models.ForeignKey(Source, on_delete=models.PROTECT)
    started = models.DateTimeField(auto_now_add=True)
    finished = models.DateTimeField(null=True)
    status = models.CharField(max_length=12, default="running")
    counts = models.JSONField(default=dict)
    error = models.CharField(max_length=300, blank=True)


class Observation(models.Model):
    source = models.ForeignKey(Source, on_delete=models.PROTECT)
    external_id = models.PositiveBigIntegerField()
    facts = models.JSONField()
    first_run = models.ForeignKey(Run, on_delete=models.PROTECT)
    baseline = models.BooleanField()
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["source", "external_id"], name="unique_source_entry")]


class Offer(models.Model):
    class Channel(models.TextChoices):
        DRAFT = "draft", "未发布"
        LEAD = "lead", "抢先线索"
        VERIFIED = "verified", "已验证"

    class ReviewState(models.TextChoices):
        AVAILABLE = "available", "正常展示"
        SUSPECT = "suspect", "疑似失效，正在复查"
        WITHDRAWN = "withdrawn", "已撤回"

    review_state = models.CharField("复查状态", max_length=10, choices=ReviewState, default=ReviewState.AVAILABLE, db_default="available")
    status_reason = models.CharField("停展原因（公开）", max_length=240, blank=True, db_default="", default="")
    starts_at = models.DateTimeField("活动开始时间（未知可不填）", null=True, blank=True)

    observation = models.OneToOneField(Observation, on_delete=models.PROTECT, verbose_name="发现记录")
    channel = models.CharField("频道", max_length=10, choices=Channel, default=Channel.DRAFT)
    title = models.CharField("权益", max_length=180)
    category = models.CharField("板块", max_length=10, choices=[(s, s) for s in ("数字权益", "生活服务", "购物")])
    platform = models.CharField("领取平台（未核对时留空）", max_length=80, blank=True, default="", db_default="")
    region = models.CharField("适用地区（未核对时留空）", max_length=80, blank=True, default="", db_default="")
    cost = models.CharField("实际支出或待确认项", max_length=200)
    conditions = models.TextField("适用条件")
    steps = models.TextField("参与步骤")
    official_url = models.URLField("原始参与入口")
    evidence_url = models.URLField("核验依据")
    evidence = models.TextField("证据摘要和核验边界")
    checked_at = models.DateTimeField("核验时间")
    ends_at = models.DateTimeField("停止展示活动入口时间")

    # None 表示未知；已核实无需支付的项目须明确填 0。
    payable_fen = models.PositiveIntegerField("商品或服务实付（分，不含运费及另购会员）", null=True, blank=True)
    required_purchase_fen = models.PositiveIntegerField("购物领取所需另购商品的最低新增实付（分，已计入商品实付）",
        null=True, blank=True, help_text="购物已验证必填。无须另购填 0；券前满额不等于实付，未知请保持线索。")
    no_asset_exchange = models.BooleanField("购物：已核对无需交付旧物或消耗已有资产", default=False, db_default=False,
        help_text="查看原文和价格依据；必须用旧物、积分、储值余额或已付费券兑换的，先保留线索。可免费当场领取的普通折扣券不在此列。")
    shipping_fen = models.PositiveIntegerField("运费或配送费（分）", null=True, blank=True)
    membership_fen = models.PositiveIntegerField("必须新增会员费（分）", null=True, blank=True)
    reward_basis = models.TextField("权益证据（核验原文要点）", blank=True)
    price_basis = models.TextField("成本证据（含配送费、续费条件）", blank=True)
    eligibility_basis = models.TextField("资格证据（地区、账号及适用范围）", blank=True)
    time_basis = models.TextField("有效期证据（原始时区）", blank=True)

    class Meta:
        constraints = [models.CheckConstraint(
            name="status_requires_public_reason",
            condition=models.Q(review_state="available") | (
                models.Q(review_state__in=["suspect", "withdrawn"]) & models.Q(status_reason__regex=r"\S")),
        ), models.CheckConstraint(
            name="verified_shopping_without_asset_exchange",
            condition=~models.Q(channel="verified", category="购物") | models.Q(no_asset_exchange=True),
            violation_error_message="现阶段无法计价旧物或已持有的积分、储值等资产；购物已验证须确认无需消耗这些资产。",
        ), models.CheckConstraint(
            name="verified_shopping_requires_purchase_floor",
            condition=~models.Q(channel="verified",category="购物") | models.Q(
                required_purchase_fen__isnull=False, payable_fen__gte=models.F("required_purchase_fen")),
            violation_error_message="购物已验证须核实另购门槛，且商品实付不能低于领取所需的最低新增实付。",
        ), models.CheckConstraint(
            name="end_after_known_start",
            condition=models.Q(starts_at__isnull=True) | models.Q(ends_at__gt=models.F("starts_at")),
        ), models.CheckConstraint(
            name="verified_requires_price_and_evidence",
            condition=~models.Q(channel="verified") | models.Q(
                payable_fen__isnull=False, shipping_fen__isnull=False, membership_fen__isnull=False,
                reward_basis__regex=r"\S", price_basis__regex=r"\S",
                eligibility_basis__regex=r"\S", time_basis__regex=r"\S",
                official_url__startswith="https://", evidence_url__startswith="https://",
                evidence__regex=r"\S", conditions__regex=r"\S", steps__regex=r"\S",
            ),
            violation_error_message="已验证须填写实付、配送费、新增会员费及各项证据，并提供 HTTPS 原始入口和核验依据。",
        )]

    @property
    def display_cost(self):
        if self.channel != self.Channel.VERIFIED:
            return self.cost
        total = self.payable_fen + self.shipping_fen + self.membership_fen
        purchase = self.required_purchase_fen
        if self.category == "购物" and purchase:
            return (f"必要支出 ¥{total // 100}.{total % 100:02d}，"
                    f"其中至少 ¥{purchase // 100}.{purchase % 100:02d} 为领取所需另购实付")
        return f"必要支出 ¥{total // 100}.{total % 100:02d}（含配送费及必须新增的会员费）"

    def __str__(self):
        return self.title


class OfferRevision(models.Model):
    """一次活动内容变更后的完整副本；数据库触发器与原写入处于同一事务。"""

    offer = models.ForeignKey(Offer, on_delete=models.PROTECT, related_name="revisions")
    recorded_at = models.DateTimeField(auto_now_add=True)
    snapshot = models.JSONField()

    class Meta:
        ordering = ["-id"]


class RuleAnalysis(models.Model):
    digest = models.CharField(max_length=64, unique=True)
    model = models.CharField(max_length=48)
    prompt_version = models.CharField(max_length=24)
    excerpts = models.JSONField()
    usage = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class Favorite(models.Model):
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "offer"], name="one_favorite_per_user_offer")]


class Feedback(models.Model):
    class Kind(models.TextChoices):
        PRICE = "price", "实际价格不符"
        ELIGIBILITY = "eligibility", "参与条件不符"
        EXPIRED = "expired", "活动已失效"

    user = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    revision = models.ForeignKey(OfferRevision, on_delete=models.PROTECT)
    kind = models.CharField("问题类型", max_length=12, choices=Kind)
    reviewed = models.BooleanField("已处理", default=False)
    reply = models.CharField("给反馈者的说明", max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "revision", "kind"], name="unique_feedback_kind_version")]


class Subscription(models.Model):
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    category = models.CharField("板块", max_length=10, choices=Offer._meta.get_field("category").choices, blank=True)
    keyword = models.CharField("关键词", max_length=100, blank=True)
    platform = models.CharField("平台", max_length=80, blank=True)
    region = models.CharField("地区", max_length=80, blank=True)
    leads = models.BooleanField("同时包含待核线索", default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "category", "keyword", "platform", "region", "leads"],
            name="unique_subscription_terms")]

    def matching(self, offers):
        channels = [Offer.Channel.VERIFIED, Offer.Channel.LEAD] if self.leads else [Offer.Channel.VERIFIED]
        offers = offers.filter(channel__in=channels)
        for field in ("category", "platform", "region"):
            if value := getattr(self, field):
                offers = offers.filter(**{field: value})
        if self.keyword:
            offers = offers.filter(models.Q(title__icontains=self.keyword) | models.Q(conditions__icontains=self.keyword)
                                   | models.Q(platform__icontains=self.keyword))
        return offers


class SignupTicket(models.Model):
    email = models.EmailField(max_length=150, unique=True)
    digest = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()


class AccountRateWindow(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(db_index=True)


class InboxMessage(models.Model):
    class Kind(models.TextChoices):
        PUBLISHED = "published", "新情报"
        PRICE_DROP = "price_drop", "实付降价"
        CORRECTION = "correction", "更正提醒"

    user = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    revision = models.ForeignKey(OfferRevision, on_delete=models.PROTECT)
    kind = models.CharField(max_length=12, choices=Kind)
    total_fen = models.PositiveBigIntegerField(null=True)
    read_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "revision"], name="one_inbox_per_user_revision")]
        indexes = [models.Index(fields=["user", "-id"], name="inbox_user_recent")]


class PushDevice(models.Model):
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    endpoint_hash = models.CharField(max_length=64, unique=True)
    sealed = models.BinaryField()
    created_at = models.DateTimeField(auto_now_add=True)
    timezone = models.CharField(max_length=64, default="Asia/Shanghai")
    quiet = models.BooleanField(default=False)


class PushDelivery(models.Model):
    device = models.ForeignKey(PushDevice, on_delete=models.CASCADE)
    message = models.ForeignKey(InboxMessage, null=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    state = models.CharField(max_length=12, default="pending")
    attempts = models.PositiveSmallIntegerField(default=0)
    next_at = models.DateTimeField(db_index=True)
    http_status = models.PositiveSmallIntegerField(null=True)
    accepted_at = models.DateTimeField("收到推送服务受理响应的时间", null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["device", "message"], name="one_device_delivery_per_message")]

class StartWake(models.Model):
    """仅预先发布、等待时间跨过开始点的活动。"""
    offer = models.OneToOneField(Offer, primary_key=True, on_delete=models.CASCADE)

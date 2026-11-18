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

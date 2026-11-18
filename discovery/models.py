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

    def __str__(self):
        return self.title

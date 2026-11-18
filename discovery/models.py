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

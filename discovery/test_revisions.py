from datetime import timedelta

from django.db import transaction
from django.test import TestCase
from django.utils import timezone

from .models import Observation, Offer, Run, Source


class RevisionTests(TestCase):
    def test_snapshot_change_noop_and_rollback(self):
        source = Source.objects.create(key="revision-fixture")
        obs = Observation.objects.create(source=source, external_id=1, facts={},
            first_run=Run.objects.create(source=source), baseline=True)
        offer = Offer.objects.create(observation=obs, title="活动", cost="运费待核",
            checked_at=timezone.now(), ends_at=timezone.now()+timedelta(days=1))
        self.assertEqual(offer.revisions.get().snapshot["cost"], "运费待核")
        rows = Offer.objects.filter(pk=offer.pk)
        rows.update(cost="运费待核")
        self.assertEqual(offer.revisions.count(), 1)
        rows.update(cost="实付含运费 6.01 元")
        self.assertEqual(list(offer.revisions.values_list("snapshot__cost", flat=True)),
            ["实付含运费 6.01 元", "运费待核"])
        with transaction.atomic():
            rows.update(channel="lead")
            transaction.set_rollback(True)
        self.assertEqual(offer.revisions.count(), 2)
        self.assertEqual(rows.get().channel, "draft")

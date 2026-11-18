from unittest.mock import patch

from django.test import TestCase

from .gamerpower import sync
from .models import Observation, Run, Source


def row(i):
    return dict(id=i, title=f"fixture {i}", gamerpower_url="https://www.gamerpower.com/detail", end_date="N/A", published_date="2026-01-01", platforms="PC", type="Game")


@patch("discovery.gamerpower.fetch")
class SyncTests(TestCase):
    def test_baseline_repeat_change_new(self, fetch):
        fetch.return_value = [row(1)]
        self.assertEqual(sync()["baseline"], 1)
        self.assertEqual(sync()["unchanged"], 1)
        fetch.return_value = [dict(row(1), title="updated"), row(2)]
        result = sync()
        self.assertEqual((result["changed"], result["new"]), (1, 1))
        self.assertFalse(Observation.objects.get(external_id=2).baseline)

    def test_failure_rolls_back_and_recovers(self, fetch):
        fetch.return_value = [row(1), row(1)]
        with self.assertRaises(ValueError):
            sync()
        self.assertFalse(Observation.objects.exists())
        self.assertIsNone(Source.objects.get().last_success)
        self.assertEqual(Run.objects.get().status, "failed")
        fetch.return_value = [row(1)]
        self.assertEqual(sync()["baseline"], 1)

    def test_pause_does_not_fetch(self, fetch):
        Source.objects.create(key="gamerpower", enabled=False)
        self.assertTrue(sync()["paused"])
        fetch.assert_not_called()

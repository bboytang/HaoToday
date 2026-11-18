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

    def test_catalog_recheck_is_cautious_and_does_not_auto_restore(self, fetch):
        from datetime import timedelta
        from django.utils import timezone
        from .models import Offer
        fetch.return_value = [row(1), row(2)]
        sync()
        offer = Offer.objects.create(observation=Observation.objects.get(external_id=1),
            channel="lead", checked_at=timezone.now(), ends_at=timezone.now()+timedelta(days=1))
        fetch.side_effect = TimeoutError()
        with self.assertRaises(TimeoutError):
            sync()
        offer.refresh_from_db()
        self.assertEqual(offer.review_state, "available")
        fetch.side_effect = None
        fetch.return_value = [row(2)]
        self.assertEqual(sync()["missing_for_review"], 1)
        offer.refresh_from_db()
        self.assertEqual(offer.review_state, "suspect")
        fetch.return_value = [row(1), row(2)]
        sync()
        offer.refresh_from_db()
        self.assertEqual(offer.review_state, "suspect")
        offer.review_state = "available"
        offer.save()
        fetch.return_value = [dict(row(1), platforms="iOS"), row(2)]
        sync()
        offer.refresh_from_db()
        self.assertEqual(offer.review_state, "suspect")

    def test_review_priority_not_publication(self, fetch):
        fetch.return_value=[
            dict(row(1), instructions="Add the game to your library.", end_date="2027-01-01 23:00:00"),
            dict(row(2), instructions="Unlock your key (10 ARP required)."),
            dict(row(3), instructions="Enter for a chance to win the game."),
            dict(row(4), instructions="Unlock instructions unavailable"),
        ]
        result=sync()
        self.assertEqual(result["triage"],{"priority":1,"review":1,"hold":1,"exclude":1})
        from .models import Offer
        self.assertFalse(Offer.objects.exists())
        self.assertEqual(sync()["unchanged"],4)
        fetch.return_value=fetch.return_value[1:]
        sync()
        self.assertEqual(Observation.objects.get(external_id=1).facts["triage"]["tier"],"absent")

    def test_changed_claim_steps_pause_published_offer(self, fetch):
        from datetime import timedelta
        from django.utils import timezone
        from .models import Offer
        fetch.return_value=[dict(row(1),instructions="Add the game to your library.")]
        sync()
        offer=Offer.objects.create(observation=Observation.objects.get(),channel="lead",
            checked_at=timezone.now(),ends_at=timezone.now()+timedelta(days=1))
        fetch.return_value[0]["instructions"]="Purchase required to get the game."
        self.assertEqual(sync()["triage"]["hold"],1)
        offer.refresh_from_db()
        self.assertEqual(offer.review_state,"suspect")

    def test_no_purchase_required_is_not_a_spend_gate(self, fetch):
        fetch.return_value=[dict(row(1),instructions="No purchase required. Add it to your library.",
            end_date="2027-01-01 23:00:00")]
        self.assertEqual(sync()["triage"]["priority"],1)

    def test_description_cost_change_pauses_offer_without_copying_description(self, fetch):
        from datetime import timedelta
        from django.utils import timezone
        from .models import Offer
        entry = dict(row(1),instructions="Add it to your library.",description="Free until Friday.",
            end_date="2027-01-01 23:00:00")
        fetch.return_value=[entry]
        sync()
        ob=Observation.objects.get()
        offer=Offer.objects.create(observation=ob,channel="lead",checked_at=timezone.now(),
            ends_at=timezone.now()+timedelta(days=1))
        # 从旧初筛版本补摘要不应撤下原有公开项，也不计新发现。
        old=ob.facts["triage"]
        del old["description_sha256"]
        old["version"]=1
        ob.save()
        self.assertEqual(sync()["enriched"],1)
        offer.refresh_from_db()
        self.assertEqual(offer.review_state,"available")
        entry["description"]="  FREE until friday.  "
        self.assertEqual(sync()["unchanged"],1)
        entry["description"]="This giveaway requires 10 ARP to claim."
        self.assertEqual(sync()["triage"]["hold"],1)
        offer.refresh_from_db()
        ob.refresh_from_db()
        self.assertEqual(offer.review_state,"suspect")
        self.assertNotIn(entry["description"],str(ob.facts))
        # 不靠关键词：即使等级未变，描述中的地区限制变化也必须触发复核。
        entry["description"]="Offer available in selected regions."
        sync()
        offer.review_state="available"
        offer.save()
        entry["description"]="Offer available in Japan only."
        self.assertEqual(sync()["triage"]["priority"],1)
        offer.refresh_from_db()
        self.assertEqual(offer.review_state,"suspect")

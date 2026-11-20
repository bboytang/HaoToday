from unittest.mock import patch
from django.test import TestCase
from .models import Observation,Offer,Run,Source
from .shopping import sync, assess, review_saved

def row(code):
    return dict(code=str(code),plat="2",content="测试实物 1元 https://example.org/item",
        num_id="sku-1",add_time="2026/11/20 10:00:00",id="not-stored")

@patch("discovery.shopping.time.sleep")
@patch("discovery.shopping.fetch_page")
class ShoppingTests(TestCase):
    def setUp(self):
        Source.objects.create(key="zhetaoke-jd")
    def test_window_replay_and_no_publication(self,fetch,sleep):
        fetch.side_effect=[[row(i) for i in range(1,11)],[row(i) for i in range(5,15)]]
        result=sync("fixture")
        self.assertEqual((result["rows"],result["duplicate_code"],result["baseline"]),(20,6,14))
        self.assertTrue(result["page_cap_reached"])
        self.assertFalse(Offer.objects.exists())
        self.assertEqual(Run.objects.get().status,"partial")
        self.assertIsNone(Source.objects.get().last_success)
        fetch.side_effect=None
        fetch.return_value=[row(1)]
        self.assertEqual(sync("fixture")["unchanged"],1)
        self.assertEqual(Observation.objects.count(),14)
        self.assertNotIn("id",Observation.objects.first().facts)
    def test_bad_batch_rolls_back_and_can_resume(self,fetch,sleep):
        fetch.return_value=[row(1),dict(row(2),plat="1")]
        with self.assertRaises(ValueError): sync("fixture")
        self.assertFalse(Observation.objects.exists())
        self.assertEqual(Run.objects.get().status,"failed")
        fetch.return_value=[row(1)]
        self.assertEqual(sync("fixture")["baseline"],1)
    def test_disabled_never_requests(self,fetch,sleep):
        Source.objects.update(enabled=False)
        self.assertTrue(sync("fixture")["paused"])
        fetch.assert_not_called()

    def test_rebate_is_not_low_cash_price(self,fetch,sleep):
        for text in ("拍下19.9亓，饭10超市卡", "返卡后0.92", "饭卡后到手0.92", "需凑単", "先买后返现"):
            self.assertEqual(assess(text)["tier"],"hold")
        self.assertEqual(assess("无需返卡，实际价格待查")["tier"],"hold")  # 保守召回，交由人复核
        self.assertEqual(assess("1元实物，规则待查")["tier"],"review")
        fetch.return_value=[dict(row(1),content="拍下19.9亓，饭10超市卡")]
        sync("fixture")
        fetch.reset_mock()
        self.assertEqual(review_saved(),{"hold":1,"review":0})
        fetch.assert_not_called()
        self.assertFalse(Offer.objects.exists())

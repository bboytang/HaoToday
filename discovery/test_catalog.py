from unittest.mock import patch
from django.test import TestCase
from .catalog import fen,normalize,sync
from .models import Source,Observation,Offer,Run


def row(code=1):
    return dict(code=str(code),title="棉袜",jianjie="日用实物",tao_id="opaque-id",item_url="https://uland.taobao.com/item/edetail",
        size="3.00",quanhou_jiage="1.00",coupon_info_money="2.00",coupon_info="满3元减2元",coupon_end_time="2026-11-28 23:59:59")


class CatalogTests(TestCase):
    def test_amounts_noise_and_threshold(self):
        self.assertEqual(fen("0.01"),1)
        for v in ("NaN","Infinity","-1","1.001",True,""):
            with self.assertRaises(ValueError): fen(v)
        _,facts=normalize(row())
        self.assertEqual(facts["quoted_after_coupon_fen"],100)
        self.assertIsNone(facts["shipping_fen"])
        self.assertEqual(facts["triage"]["tier"],"review")
        for updates,tier in [
            ({"title":"手机壁纸虚拟商品"},"exclude"),({"title":"瑕疵棉袜"},"hold"),
            ({"title":"工业橡胶垫片"},"exclude"),({"coupon_info":"满30元减2元"},"hold"),
            ({"quanhou_jiage":"0.01"},"hold")]:
            self.assertEqual(normalize(row()|updates)[1]["triage"]["tier"],tier)
        with self.assertRaises(ValueError):normalize(row()|{"item_url":"http://localhost/"})

    @patch("discovery.catalog.fetch")
    def test_idempotent_internal_only_and_atomic_failure(self,fetch):
        Source.objects.create(key="zhetaoke-tb-catalog")
        fetch.return_value=[row()]
        self.assertEqual(sync("fixture")["baseline"],1)
        self.assertEqual(sync("fixture")["unchanged"],1)
        self.assertFalse(Offer.objects.exists())
        self.assertIsNone(Source.objects.get().last_success)
        fetch.return_value=[row(2),row(3)|{"size":"NaN"}]
        with self.assertRaises(ValueError):sync("fixture")
        self.assertEqual(Observation.objects.count(),1)
        self.assertEqual(Run.objects.order_by("-id").first().status,"failed")

    @patch("discovery.catalog.fetch")
    def test_source_defaults_paused(self,fetch):
        self.assertTrue(sync("fixture")["paused"])
        fetch.assert_not_called()

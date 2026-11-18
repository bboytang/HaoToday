import io
import json
from unittest.mock import patch
from django.test import TestCase
from .glm import analyze
from .models import Offer, RuleAnalysis


class GlmTests(TestCase):
    def test_no_key_no_request(self):
        with patch.dict("os.environ", {"ZHIPUAI_API_KEY": ""}), patch("discovery.glm.build_opener") as client:
            with self.assertRaises(ValueError):
                analyze("免费")
            client.assert_not_called()

    @patch.dict("os.environ", {"ZHIPUAI_API_KEY": "test-only"})
    @patch("discovery.glm.build_opener")
    def test_quote_validation_and_cache(self, client):
        def reply(cost):
            result = dict(cost=cost, reward=None, eligibility=None, deadline=None)
            return io.BytesIO(json.dumps({"choices":[{"message":{"content":json.dumps(result)}}]}).encode())
        client.return_value.open.side_effect = [reply("免费"), reply("运费6元")]
        with self.assertRaises(ValueError):
            analyze("运费6元")
        self.assertFalse(RuleAnalysis.objects.exists())
        item = analyze("运费6元")
        self.assertEqual(item.pk, analyze("运费6元").pk)
        self.assertEqual(client.return_value.open.call_count, 2)
        self.assertFalse(Offer.objects.exists())

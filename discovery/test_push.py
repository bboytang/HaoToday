import base64
import json
from datetime import timedelta
from unittest.mock import patch
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from .models import PushDevice, PushDelivery
from .push import dispatch_one


@patch.dict("os.environ", {"HAOTODAY_VAPID_KEY":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAE"})
class PushTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user("tester")
        self.client.force_login(self.user)
        point=ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(Encoding.X962,PublicFormat.UncompressedPoint)
        self.sub={"endpoint":"https://web.push.apple.com/test-only", "keys":{
            "auth":base64.urlsafe_b64encode(bytes(16)).decode(),"p256dh":base64.urlsafe_b64encode(point).decode()}}

    def register(self):
        return self.client.post("/devices/register/",{"subscription":self.sub,"timezone":"Asia/Shanghai"},content_type="application/json")

    def test_provider_validation_and_no_account_transfer(self):
        ok=self.sub["endpoint"]
        for url in ("http://web.push.apple.com/test","https://example.org/path","https://web.push.apple.com@localhost/a"):
            self.sub["endpoint"]=url
            self.assertEqual(self.register().status_code,400)
        self.sub["endpoint"]=ok
        self.assertEqual(self.register().status_code,200)
        device=PushDevice.objects.get()
        self.assertNotIn(ok.encode(),bytes(device.sealed))
        self.client.force_login(get_user_model().objects.create_user("other"))
        self.assertEqual(self.register().status_code,400)
        self.assertEqual(self.client.post(f"/devices/{device.pk}/action/",{"action":"remove"}).status_code,404)

    @patch("discovery.push.transmit")
    def test_test_delivery_retry_and_expiry(self, send):
        self.register()
        device=PushDevice.objects.get()
        path=f"/devices/{device.pk}/action/"
        for _ in range(2): self.client.post(path,{"action":"test"})
        job=PushDelivery.objects.get()
        send.side_effect=[503,410]
        dispatch_one()
        job.refresh_from_db()
        self.assertEqual((job.state,job.attempts),("pending",1))
        self.assertFalse(dispatch_one())
        PushDelivery.objects.update(next_at=timezone.now()-timedelta(seconds=1))
        dispatch_one()
        job.refresh_from_db()
        device.refresh_from_db()
        self.assertEqual((job.state,job.attempts),("expired",2))
        self.assertFalse(device.sealed)

    @patch("discovery.push.transmit")
    def test_only_provider_success_records_acceptance_time(self, send):
        self.register()
        device=PushDevice.objects.get()
        self.client.post(f"/devices/{device.pk}/action/",{"action":"test"})
        job=PushDelivery.objects.get()
        send.side_effect=[503,201]
        dispatch_one()
        job.refresh_from_db()
        self.assertIsNone(job.accepted_at)
        retry = timezone.now()
        PushDelivery.objects.update(next_at=retry)
        dispatch_one()
        job.refresh_from_db()
        self.assertEqual((job.state,job.attempts),("accepted",2))
        self.assertGreaterEqual(job.accepted_at,retry)
        self.assertContains(self.client.get("/devices/"),"服务受理 "+timezone.localtime(job.accepted_at).strftime("%m-%d %H:%M:%S"))

    def test_assets(self):
        self.assertEqual(self.client.get("/sw.js").status_code,200)
        self.assertEqual(json.loads(b"".join(self.client.get("/manifest.webmanifest").streaming_content))["display"],"standalone")

    def test_builds_encrypted_vapid_request_without_following_redirects(self):
        from requests import Response
        from .push import transmit
        response=Response()
        response.status_code=201
        response._content=b""
        with patch("requests.Session.request",return_value=response) as wire:
            self.assertEqual(transmit(self.sub,{"body":"private-text"},45),201)
        kwargs=wire.call_args.kwargs
        self.assertFalse(kwargs["allow_redirects"])
        self.assertTrue(kwargs["headers"]["authorization"].lower().startswith("vapid "))
        self.assertEqual(str(kwargs["headers"]["ttl"]), "45")
        self.assertNotIn(b"private-text",kwargs["data"])

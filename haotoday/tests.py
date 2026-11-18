from unittest.mock import patch

from django.db import OperationalError
from django.test import TestCase


class HealthTests(TestCase):
    def test_ready(self):
        self.assertEqual(self.client.get("/health/").json(), {"status": "ok"})

    def test_not_ready(self):
        with patch("haotoday.urls.connection.cursor", side_effect=OperationalError):
            self.assertEqual(self.client.get("/health/").status_code, 503)

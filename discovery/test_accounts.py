import re
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from .models import AccountRateWindow, Subscription


class AccountTests(TestCase):
    def test_switches_closed(self):
        for path in ("signup", "reset"):
            self.assertEqual(self.client.post(f"/account/{path}/", {"email":"test@example.org"}).status_code, 404)

    @override_settings(REGISTRATION_OPEN=True, ACCOUNT_MAIL_ENABLED=True,
                       EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", DEFAULT_FROM_EMAIL="test@example.org")
    def test_verify_set_password_reset_and_delete(self):
        email = "spring@example.org"
        self.client.post("/account/signup/", {"email":email.upper()})
        user_model = get_user_model()
        self.assertFalse(user_model.objects.filter(username=email).exists())
        link = re.search(r"https://8kraw.cloud([^\s]+)", mail.outbox[0].body)[1]
        self.assertContains(self.client.get(link), "设置密码")
        p = "Genuine-test-only-1325"
        self.assertRedirects(self.client.post(link, {"new_password1":p,"new_password2":p}), "/account/login/")
        self.assertEqual(self.client.get(link).status_code, 404)
        self.client.post("/account/reset/", {"email":email})
        link = re.search(r"https://8kraw.cloud([^\s]+)", mail.outbox[1].body)[1]
        clean_link = self.client.get(link).url
        new = "Different-test-only-9854"
        self.assertRedirects(self.client.post(clean_link, {"new_password1":new,"new_password2":new}), "/account/reset/complete/")
        self.assertFalse(self.client.login(username=email,password=p))
        self.assertRedirects(self.client.post("/account/login/", {"username":email.upper(),"password":new}), "/account/")
        u = user_model.objects.get(username=email)
        Subscription.objects.create(user=u, keyword="复核")
        self.client.post("/account/delete/", {"password":"wrong"})
        self.assertTrue(user_model.objects.filter(pk=u.pk).exists())
        self.assertRedirects(self.client.post("/account/delete/", {"password":new}), "/")
        self.assertFalse(user_model.objects.filter(pk=u.pk).exists())
        self.assertFalse(Subscription.objects.filter(user_id=u.pk).exists())

    def test_rate_limit_shared_across_clients(self):
        from django.test import Client
        with patch("discovery.accounts.timezone.now", return_value=__import__("datetime").datetime.fromtimestamp(
                1700000000, __import__("datetime").timezone.utc)):
            for _ in range(12):
                self.assertEqual(Client().post("/account/login/", {"username":"bad","password":"wrong"}).status_code, 200)
            self.assertEqual(Client().post("/account/login/", {"username":"bad","password":"wrong"}).status_code, 429)
        self.assertEqual(AccountRateWindow.objects.count(), 2)

    def test_password_policy_only_requires_six_characters(self):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        for password in ("123456", "abcdef", "测试密码六字符"):
            validate_password(password)
        with self.assertRaises(ValidationError):
            validate_password("12345")

    @override_settings(REGISTRATION_OPEN=True, ACCOUNT_MAIL_ENABLED=True,
                       EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", DEFAULT_FROM_EMAIL="test@example.org")
    def test_activation_accepts_six_digits_but_rejects_five(self):
        self.client.post("/account/signup/", {"email":"six@example.org"})
        link = re.search(r"https://8kraw.cloud([^\s]+)", mail.outbox[0].body)[1]
        self.assertEqual(self.client.post(link, {"new_password1":"12345","new_password2":"12345"}).status_code,200)
        self.assertFalse(get_user_model().objects.filter(username="six@example.org").exists())
        self.assertRedirects(self.client.post(link, {"new_password1":"123456","new_password2":"123456"}), "/account/login/")
        self.assertTrue(self.client.login(username="six@example.org",password="123456"))

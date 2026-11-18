from datetime import timedelta
from hashlib import sha256
import secrets
import logging

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.views import LoginView, PasswordResetView
from django.core.mail import send_mail
from django.db import transaction
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .models import AccountRateWindow, SignupTicket


class EmailForm(forms.Form):
    email = forms.EmailField(label="邮箱", max_length=150)


def limited(request, scope, identity, limit):
    now = timezone.now()
    window = int(now.timestamp()) // 600
    # 线上 app 只由 Caddy 访问；只信任代理追加的最后一段，不取客户端自报的首段。
    ip = request.META.get("REMOTE_ADDR", "")
    if settings.SECURE_PROXY_SSL_HEADER:
        ip = request.META.get("HTTP_X_FORWARDED_FOR", ip).rsplit(",", 1)[-1].strip()
    AccountRateWindow.objects.filter(expires_at__lte=now).delete()
    with transaction.atomic():
        for prefix, value, maximum in (("ip", ip, limit*4), ("account", identity.lower().strip()[:254], limit)):
            key = salted_hmac("account-rate", f"{scope}:{window}:{prefix}:{value}", algorithm="sha256").hexdigest()
            obj, _ = AccountRateWindow.objects.select_for_update().get_or_create(
                key=key, defaults={"expires_at": now + timedelta(minutes=11)})
            if obj.count >= maximum:
                return True
            obj.count += 1
            obj.save(update_fields=["count"])
    return False


def slow_down():
    return HttpResponse("请求过于频繁，请十分钟后再试。", status=429, headers={"Retry-After": "600"})


class AccountLogin(LoginView):
    template_name = "discovery/login.html"

    def post(self, request, *args, **kwargs):
        if limited(request, "login", request.POST.get("username", ""), 12):
            return slow_down()
        return super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.method == "POST":
            data = kwargs["data"].copy()
            if "@" in data.get("username", ""):
                data["username"] = data["username"].strip().lower()
            kwargs["data"] = data
        return kwargs

    def get_context_data(self, **kwargs):
        return super().get_context_data(registration=settings.REGISTRATION_OPEN,
            recovery=settings.ACCOUNT_MAIL_ENABLED, **kwargs)


@never_cache
@require_http_methods(["GET", "POST"])
def signup(request):
    if not settings.REGISTRATION_OPEN:
        raise Http404
    form = EmailForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].lower()
        if limited(request, "signup", email, 3):
            return slow_down()
        if not get_user_model().objects.filter(username=email).exists():
            secret = secrets.token_urlsafe(32)
            SignupTicket.objects.filter(expires_at__lte=timezone.now()).delete()
            SignupTicket.objects.update_or_create(email=email, defaults={
                "digest": sha256(secret.encode()).hexdigest(), "expires_at":timezone.now()+timedelta(minutes=30)})
            url = settings.ACCOUNT_ORIGIN + reverse("activate", args=[secret])
            try:
                send_mail("验证 HaoToday 邮箱", f"请在30分钟内打开链接设置密码。若非本人操作，请忽略。\n{url}",
                    settings.DEFAULT_FROM_EMAIL, [email])
            except (OSError, ValueError):
                logging.getLogger(__name__).warning("注册邮件投递失败，请检查 SMTP")
        return render(request, "discovery/mail_form.html", {"title":"请检查邮箱", "note":"如果该地址可注册，你将收到验证邮件。"})
    return render(request, "discovery/mail_form.html", {"title":"邮箱注册", "form":form})


@never_cache
@require_http_methods(["GET", "POST"])
def activate(request, token):
    if not settings.REGISTRATION_OPEN:
        raise Http404
    with transaction.atomic():
        ticket = SignupTicket.objects.select_for_update().filter(
            digest=sha256(token.encode()).hexdigest(), expires_at__gt=timezone.now()).first()
        if not ticket:
            raise Http404
        user = get_user_model()(username=ticket.email, email=ticket.email)
        form = SetPasswordForm(user, request.POST if request.method == "POST" else None)
        if request.method == "POST" and form.is_valid():
            if not get_user_model().objects.filter(username=ticket.email).exists():
                form.save()
            ticket.delete()
            return redirect("login")
    return render(request, "discovery/mail_form.html", {"title":"邮箱已验证，设置密码", "form":form})


class AccountReset(PasswordResetView):
    template_name = "discovery/mail_form.html"
    extra_context = {"title":"找回个人账号密码"}
    email_template_name = "discovery/reset_email.txt"
    subject_template_name = "discovery/reset_subject.txt"
    success_url = reverse_lazy("password_reset_done")

    def dispatch(self, request, *args, **kwargs):
        if not settings.ACCOUNT_MAIL_ENABLED:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if limited(request, "reset", request.POST.get("email", ""), 3):
            return slow_down()
        return super().post(request, *args, **kwargs)



@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def delete_account(request):
    error = ""
    if request.method == "POST":
        if limited(request, "delete", request.user.username, 5):
            return slow_down()
        if request.user.is_staff or request.user.is_superuser:
            error = "管理员账号不能在此注销。"
        elif not request.user.check_password(request.POST.get("password", "")):
            error = "密码不正确，账号未注销。"
        else:
            user = request.user
            with transaction.atomic():
                logout(request)
                user.delete()
            return redirect("feed")
    return render(request, "discovery/delete_account.html", {"error":error})

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.db import OperationalError, connection
from django.http import JsonResponse
from django.urls import path
from django.views.decorators.http import require_safe


@require_safe
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except OperationalError:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


from discovery import accounts, views

urlpatterns = [
    path("", views.feed, name="feed"),
    path("offers/<int:pk>/", views.detail, name="offer"),
    path("account/", views.account, name="account"),
    path("inbox/", views.inbox, name="inbox"),
    path("inbox/<int:pk>/read/", views.read_message, name="read-message"),
    path("subscriptions/", views.subscriptions, name="subscriptions"),
    path("subscriptions/<int:pk>/remove/", views.unsubscribe, name="unsubscribe"),
    path("offers/<int:pk>/feedback/", views.feedback, name="feedback"),
    path("account/login/", accounts.AccountLogin.as_view(), name="login"),
    path("account/signup/", accounts.signup, name="signup"),
    path("account/activate/<slug:token>/", accounts.activate, name="activate"),
    path("account/delete/", accounts.delete_account, name="delete-account"),
    path("account/reset/", accounts.AccountReset.as_view(), name="password_reset"),
    path("account/reset/sent/", auth_views.PasswordResetDoneView.as_view(template_name="discovery/mail_form.html",
        extra_context={"title":"请检查邮箱", "note":"如果邮箱关联有效账号，将收到重置链接。"}), name="password_reset_done"),
    path("account/new-password/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="discovery/mail_form.html", extra_context={"title":"设置新密码"}), name="password_reset_confirm"),
    path("account/reset/complete/", auth_views.PasswordResetCompleteView.as_view(template_name="discovery/mail_form.html",
        extra_context={"title":"密码已更新"}), name="password_reset_complete"),
    path("account/logout/", auth_views.LogoutView.as_view(next_page="feed"), name="logout"),
    path("offers/<int:pk>/favorite/", views.favorite, name="favorite"),
    path("admin/", admin.site.urls),
    path("health/", health),
]

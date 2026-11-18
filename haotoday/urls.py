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


from discovery import views

urlpatterns = [
    path("", views.feed, name="feed"),
    path("offers/<int:pk>/", views.detail, name="offer"),
    path("account/", views.account, name="account"),
    path("account/login/", auth_views.LoginView.as_view(template_name="discovery/login.html"), name="login"),
    path("account/logout/", auth_views.LogoutView.as_view(next_page="feed"), name="logout"),
    path("offers/<int:pk>/favorite/", views.favorite, name="favorite"),
    path("admin/", admin.site.urls),
    path("health/", health),
]

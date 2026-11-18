from django.contrib import admin
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
    path("admin/", admin.site.urls),
    path("health/", health),
]

from django.contrib import admin

from .models import Observation, Run, Source


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("key", "enabled", "last_success")
    readonly_fields = ("key", "last_success")

    def has_add_permission(self, request):
        return False


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Run)
class RunAdmin(ReadOnlyAdmin):
    list_display = ("source", "started", "status", "counts")


@admin.register(Observation)
class ObservationAdmin(ReadOnlyAdmin):
    list_display = ("source", "external_id", "baseline", "updated")

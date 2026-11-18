from django.contrib import admin

from .models import Observation, Offer, OfferRevision, Run, Source


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


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "channel", "review_state", "ends_at")
    list_filter = ("channel", "category", "review_state")
    raw_id_fields = ("observation",)


@admin.register(OfferRevision)
class OfferRevisionAdmin(ReadOnlyAdmin):
    list_display = ("id", "offer_id", "recorded_at")

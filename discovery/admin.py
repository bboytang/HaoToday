from django.contrib import admin

from .models import Feedback, Observation, Offer, OfferRevision, Run, Source


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


class ReviewTier(admin.SimpleListFilter):
    title = "初筛队列"
    parameter_name = "tier"

    def lookups(self, request, model_admin):
        return (("priority","优先查原始规则"),("review","常规复核"),("hold","高门槛待查"),
                ("exclude","疑似营销"),("absent","目录已移除"))

    def queryset(self, request, queryset):
        return queryset.filter(facts__triage__tier=self.value()) if self.value() else queryset


@admin.register(Observation)
class ObservationAdmin(ReadOnlyAdmin):
    list_display = ("source", "external_id", "candidate_title", "review_reason", "baseline", "updated")
    list_filter = (ReviewTier, "baseline", "source")
    ordering = ("baseline", "-updated")

    @admin.display(description="候选")
    def candidate_title(self, obj):
        return obj.facts.get("title", "—")

    @admin.display(description="初筛原因")
    def review_reason(self, obj):
        return obj.facts.get("triage", {}).get("reason", "未分类")


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "channel", "review_state", "ends_at")
    list_filter = ("channel", "category", "review_state")
    raw_id_fields = ("observation",)


@admin.register(OfferRevision)
class OfferRevisionAdmin(ReadOnlyAdmin):
    list_display = ("id", "offer_id", "recorded_at")


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("id", "revision_id", "kind", "reviewed", "created_at")
    list_filter = ("reviewed", "kind")
    readonly_fields = ("user", "revision", "kind", "created_at")

    def has_add_permission(self, request):
        return False

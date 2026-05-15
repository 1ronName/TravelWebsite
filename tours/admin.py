from django.contrib import admin, messages

from .models import Route, TourGroup, RouteChangeHistory, PriceChangeHistory


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("name", "destination", "status", "version", "season", "parent", "created_at")
    list_filter = ("status", "season", "created_at")
    search_fields = ("name", "destination", "description")
    autocomplete_fields = ("parent", "previous_version")
    actions = ("mark_active", "mark_canceled")
    fieldsets = (
        ("基本信息", {"fields": ("name", "destination", "description")}),
        ("版本管理", {"fields": ("version", "previous_version", "status")}),
        ("分类", {"fields": ("season", "parent")}),
    )
    readonly_fields = ("created_at",)

    @admin.action(description="标记为活跃")
    def mark_active(self, request, queryset):
        updated = queryset.update(status=Route.Status.ACTIVE)
        self.message_user(request, f"已标记 {updated} 条路线为活跃。", level=messages.SUCCESS)

    @admin.action(description="标记为已取消")
    def mark_canceled(self, request, queryset):
        updated = queryset.update(status=Route.Status.CANCELED)
        self.message_user(request, f"已标记 {updated} 条路线为已取消。", level=messages.SUCCESS)


@admin.register(TourGroup)
class TourGroupAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "route",
        "start_date",
        "deadline",
        "max_capacity",
        "price_adult",
        "price_child",
        "is_price_published",
        "is_deleted",
    )
    list_filter = ("is_price_published", "is_deleted", "start_date", "deadline", "route")
    search_fields = ("code", "route__name", "route__destination")
    autocomplete_fields = ("route",)
    actions = ("publish_price", "mark_deleted")
    readonly_fields = ("created_at", "updated_at")

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.is_price_published:
            readonly_fields.extend(["price_adult", "price_child"])
        return readonly_fields

    @admin.action(description="公开价格")
    def publish_price(self, request, queryset):
        updated = queryset.filter(is_price_published=False).update(is_price_published=True)
        self.message_user(request, f"已公开 {updated} 个旅游团的价格。", level=messages.SUCCESS)

    @admin.action(description="标记为已删除")
    def mark_deleted(self, request, queryset):
        updated = queryset.update(is_deleted=True)
        self.message_user(request, f"已标记 {updated} 个旅游团为已删除。", level=messages.SUCCESS)


@admin.register(RouteChangeHistory)
class RouteChangeHistoryAdmin(admin.ModelAdmin):
    list_display = ("route", "changed_field", "old_value", "new_value", "changed_by", "changed_at")
    list_filter = ("route", "changed_field", "changed_at")
    search_fields = ("route__name", "changed_by", "reason")
    readonly_fields = ("route", "changed_field", "old_value", "new_value", "changed_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PriceChangeHistory)
class PriceChangeHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "tour_group",
        "old_price_adult",
        "new_price_adult",
        "is_rejected",
        "reason",
        "changed_at",
    )
    list_filter = ("is_rejected", "changed_at", "tour_group")
    search_fields = ("tour_group__code", "changed_by", "reason")
    readonly_fields = ("tour_group", "old_price_adult", "old_price_child", "new_price_adult", "new_price_child", "changed_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
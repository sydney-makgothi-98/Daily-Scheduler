from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from scheduler.models import PersonalTask, PrayerSchedule, TaskCompletion


@admin.register(PersonalTask)
class PersonalTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "date", "start_time", "end_time", "category", "is_completed", "created_at")
    list_filter = ("category", "date", "is_completed", "created_at")
    search_fields = ("title", "description")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "date"
    fieldsets = (
        (_("Task Information"), {
            "fields": ("title", "description", "category")
        }),
        (_("Schedule"), {
            "fields": ("date", "start_time", "end_time")
        }),
        (_("Status"), {
            "fields": ("is_completed",)
        }),
        (_("Timestamps"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )


@admin.register(PrayerSchedule)
class PrayerScheduleAdmin(admin.ModelAdmin):
    list_display = ("prayer_name", "start_time", "end_time")
    list_filter = ("prayer_name",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (_("Prayer"), {
            "fields": ("prayer_name",)
        }),
        (_("Times"), {
            "fields": ("start_time", "end_time")
        }),
        (_("Timestamps"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )


@admin.register(TaskCompletion)
class TaskCompletionAdmin(admin.ModelAdmin):
    list_display = ("task", "is_completed", "completed_at")
    list_filter = ("is_completed", "completed_at", "task__category")
    search_fields = ("task__title",)
    readonly_fields = ("completed_at",)
    date_hierarchy = "completed_at"
    fieldsets = (
        (_("Completion Record"), {
            "fields": ("task", "is_completed")
        }),
        (_("Timestamp"), {
            "fields": ("completed_at",),
            "classes": ("collapse",)
        }),
    )

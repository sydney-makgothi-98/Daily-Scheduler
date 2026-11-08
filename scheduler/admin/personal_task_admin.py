from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from scheduler.models import (
    AlarmSetting,
    DayPlan,
    PersonalTask,
    PrayerCompletion,
    PrayerSchedule,
    RecurringTask,
    SubTask,
    TaskCompletion,
)


class SubTaskInline(admin.TabularInline):
    model = SubTask
    extra = 1
    fields = ("title", "is_completed", "order")
    ordering = ("order",)


@admin.register(PersonalTask)
class PersonalTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "date", "start_time", "end_time", "category", "task_type", "is_completed", "created_at")
    list_filter = ("category", "task_type", "date", "is_completed", "created_at")
    search_fields = ("title", "description")
    readonly_fields = ("created_at", "updated_at")
    inlines = [SubTaskInline]
    date_hierarchy = "date"
    fieldsets = (
        (_("Task Information"), {
            "fields": ("title", "description", "category", "task_type")
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
    list_display = ("task", "is_completed", "performance_rating", "completed_at")
    list_filter = ("is_completed", "completed_at", "task__category", "performance_rating")
    search_fields = ("task__title",)
    readonly_fields = ("completed_at",)
    date_hierarchy = "completed_at"
    fieldsets = (
        (_("Completion Record"), {
            "fields": ("task", "is_completed", "performance_rating")
        }),
        (_("Timestamp"), {
            "fields": ("completed_at",),
            "classes": ("collapse",)
        }),
    )


@admin.register(PrayerCompletion)
class PrayerCompletionAdmin(admin.ModelAdmin):
    list_display = ("prayer_name", "date", "is_completed", "completed_at")
    list_filter = ("prayer_name", "date", "is_completed")
    search_fields = ("prayer_name",)
    readonly_fields = ("created_at", "updated_at", "completed_at")
    date_hierarchy = "date"
    fieldsets = (
        (_("Prayer"), {
            "fields": ("prayer_name", "date")
        }),
        (_("Status"), {
            "fields": ("is_completed", "completed_at")
        }),
        (_("Timestamps"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )


@admin.register(RecurringTask)
class RecurringTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "weekdays", "start_time", "end_time", "task_type", "is_active")
    list_filter = ("task_type", "is_active")
    search_fields = ("title",)


@admin.register(DayPlan)
class DayPlanAdmin(admin.ModelAdmin):
    list_display = ("date", "day_type")
    list_filter = ("day_type",)
    date_hierarchy = "date"


@admin.register(AlarmSetting)
class AlarmSettingAdmin(admin.ModelAdmin):
    list_display = ("enabled", "break_alarm", "prayer_alarm", "task_alarm", "snooze_minutes", "volume")

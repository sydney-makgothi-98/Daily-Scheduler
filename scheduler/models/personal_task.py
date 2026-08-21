from django.db import models
from django.utils.translation import gettext_lazy as _


class TaskCategory(models.TextChoices):
    NON_NEGOTIABLE = "non_negotiable", _("Non-Negotiable")
    SECONDARY = "secondary", _("Secondary")
    FUN = "fun", _("Fun Activity")


class PersonalTask(models.Model):
    title = models.CharField(
        _("title"),
        max_length=255,
        help_text=_("Task title or description")
    )
    description = models.TextField(
        _("description"),
        blank=True,
        null=True,
        help_text=_("Detailed task description (optional)")
    )
    date = models.DateField(
        _("date"),
        help_text=_("Date of the task")
    )
    start_time = models.TimeField(
        _("start time"),
        help_text=_("Task start time")
    )
    end_time = models.TimeField(
        _("end time"),
        help_text=_("Task end time")
    )
    category = models.CharField(
        _("category"),
        max_length=20,
        choices=TaskCategory.choices,
        default=TaskCategory.SECONDARY,
        help_text=_("Task category")
    )
    is_completed = models.BooleanField(
        _("is completed"),
        default=False,
        help_text=_("Whether the task is completed")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "start_time"]
        verbose_name = _("Personal Task")
        verbose_name_plural = _("Personal Tasks")
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["category"]),
            models.Index(fields=["date", "category"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.date} {self.start_time})"


class PrayerName(models.TextChoices):
    FAJR = "fajr", _("Fajr")
    ZHOR = "zhor", _("Zhor")
    ASR = "asr", _("Asr")
    MAGRIB = "magrib", _("Magrib")
    EISHA = "eisha", _("Eisha")


class PrayerSchedule(models.Model):
    prayer_name = models.CharField(
        _("prayer name"),
        max_length=20,
        choices=PrayerName.choices,
        unique=True,
        help_text=_("Name of the prayer")
    )
    start_time = models.TimeField(
        _("start time"),
        help_text=_("Prayer start time")
    )
    end_time = models.TimeField(
        _("end time"),
        help_text=_("Prayer end time")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Prayer Schedule")
        verbose_name_plural = _("Prayer Schedules")
        ordering = ["start_time"]

    def __str__(self) -> str:
        return f"{self.get_prayer_name_display()} ({self.start_time} - {self.end_time})"


class TaskCompletion(models.Model):
    task = models.ForeignKey(
        PersonalTask,
        on_delete=models.CASCADE,
        related_name="completions",
        help_text=_("Associated personal task")
    )
    is_completed = models.BooleanField(
        _("is completed"),
        help_text=_("Whether the task was marked as completed")
    )
    completed_at = models.DateTimeField(
        _("completed at"),
        auto_now_add=True,
        help_text=_("When the completion status was recorded")
    )

    class Meta:
        verbose_name = _("Task Completion")
        verbose_name_plural = _("Task Completions")
        ordering = ["-completed_at"]
        indexes = [
            models.Index(fields=["task", "-completed_at"]),
        ]

    def __str__(self) -> str:
        status = "✓ Completed" if self.is_completed else "✗ Not Completed"
        return f"{self.task.title} - {status} ({self.completed_at})"

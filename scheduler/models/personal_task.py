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
    is_break = models.BooleanField(
        _("is break"),
        default=False,
        help_text=_("Whether this is an auto-inserted break task")
    )
    parent_task = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="breaks",
        help_text=_("Parent task if this is a break")
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

    def get_performance_rating(self):
        """Calculate performance rating based on subtask completion percentage"""
        subtasks = self.subtasks.all()
        if not subtasks.exists():
            return {"rating": "N/A", "percentage": 0, "label": "No subtasks"}

        completed = subtasks.filter(is_completed=True).count()
        total = subtasks.count()
        percentage = (completed / total) * 100

        if percentage == 0:
            return {"rating": "0%", "percentage": 0, "label": "No Performance", "emoji": "❌"}
        elif percentage < 50:
            return {"rating": f"{percentage:.0f}%", "percentage": percentage, "label": "Poor Performance", "emoji": "⚠️"}
        elif percentage < 60:
            return {"rating": "50%", "percentage": 50, "label": "Average Performance", "emoji": "📊"}
        elif percentage < 70:
            return {"rating": "60%", "percentage": 60, "label": "Above Average", "emoji": "👍"}
        elif percentage < 80:
            return {"rating": "70%", "percentage": percentage, "label": "Fairly Successful", "emoji": "😊"}
        elif percentage < 90:
            return {"rating": "80%", "percentage": percentage, "label": "Excellent", "emoji": "⭐"}
        else:
            return {"rating": "90%+", "percentage": 100, "label": "Fully Successful", "emoji": "🏆"}


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


class SubTask(models.Model):
    personal_task = models.ForeignKey(
        PersonalTask,
        on_delete=models.CASCADE,
        related_name="subtasks",
        help_text=_("Parent task")
    )
    title = models.CharField(
        _("title"),
        max_length=255,
        help_text=_("Subtask title")
    )
    is_completed = models.BooleanField(
        _("is completed"),
        default=False,
        help_text=_("Whether the subtask is completed")
    )
    order = models.PositiveIntegerField(
        _("order"),
        default=0,
        help_text=_("Order of subtask within parent task")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]
        verbose_name = _("Sub-Task")
        verbose_name_plural = _("Sub-Tasks")
        indexes = [
            models.Index(fields=["personal_task", "order"]),
        ]

    def __str__(self) -> str:
        status = "✓" if self.is_completed else "○"
        return f"{status} {self.title}"


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
    performance_rating = models.CharField(
        _("performance rating"),
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Performance rating based on subtask completion percentage")
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
        rating = f" - {self.performance_rating}" if self.performance_rating else ""
        return f"{self.task.title} - {status}{rating} ({self.completed_at})"


class PrayerCompletionStatus(models.TextChoices):
    PRAYED = "prayed", _("Prayed")
    NOT_YET = "not_yet", _("Not Yet")
    MISSED = "missed", _("Missed")


class PrayerCompletion(models.Model):
    prayer_name = models.CharField(
        _("prayer name"),
        max_length=20,
        choices=PrayerName.choices,
        help_text=_("Name of the prayer")
    )
    date = models.DateField(
        _("date"),
        help_text=_("Date of completion record")
    )
    is_completed = models.BooleanField(
        _("is completed"),
        default=False,
        help_text=_("Whether the prayer was completed")
    )
    status = models.CharField(
        _("completion status"),
        max_length=20,
        choices=PrayerCompletionStatus.choices,
        default=PrayerCompletionStatus.NOT_YET,
        help_text=_("Status of prayer completion")
    )
    completed_at = models.DateTimeField(
        _("completed at"),
        blank=True,
        null=True,
        help_text=_("When the prayer was completed")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Prayer Completion")
        verbose_name_plural = _("Prayer Completions")
        ordering = ["-date", "prayer_name"]
        unique_together = ["prayer_name", "date"]
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["prayer_name", "date"]),
        ]

    def __str__(self) -> str:
        status = "✓" if self.is_completed else "✗"
        return f"{status} {self.get_prayer_name_display()} ({self.date})"


class ProjectStatus(models.TextChoices):
    PLANNED = "planned", _("Planned")
    IN_PROGRESS = "in_progress", _("In Progress")
    COMPLETED = "completed", _("Completed")
    ON_HOLD = "on_hold", _("On Hold")


class Project(models.Model):
    title = models.CharField(
        _("title"),
        max_length=255,
        help_text=_("Project title")
    )
    description = models.TextField(
        _("description"),
        blank=True,
        null=True,
        help_text=_("Project description and notes")
    )
    start_date = models.DateField(
        _("start date"),
        help_text=_("Project start date")
    )
    end_date = models.DateField(
        _("end date"),
        help_text=_("Project end date")
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=ProjectStatus.choices,
        default=ProjectStatus.PLANNED,
        help_text=_("Current project status")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["-start_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.start_date} - {self.end_date})"

    def get_progress_percentage(self):
        """Calculate project progress based on task scheduling"""
        total_days = (self.end_date - self.start_date).days + 1
        if total_days <= 0:
            return 0
        scheduled_tasks = self.tasks.filter(is_scheduled=True).count()
        total_tasks = self.tasks.count()
        if total_tasks == 0:
            return 0
        return int((scheduled_tasks / total_tasks) * 100)


class ProjectTask(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="tasks",
        help_text=_("Parent project")
    )
    title = models.CharField(
        _("title"),
        max_length=255,
        help_text=_("Task title")
    )
    description = models.TextField(
        _("description"),
        blank=True,
        null=True,
        help_text=_("Task description")
    )
    duration_hours = models.FloatField(
        _("duration (hours)"),
        default=1.0,
        help_text=_("Duration in hours per work session")
    )
    order = models.PositiveIntegerField(
        _("order"),
        default=0,
        help_text=_("Order within project")
    )
    is_scheduled = models.BooleanField(
        _("is scheduled"),
        default=False,
        help_text=_("Whether this task has been scheduled in the main scheduler")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]
        verbose_name = _("Project Task")
        verbose_name_plural = _("Project Tasks")
        indexes = [
            models.Index(fields=["project", "order"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.project.title})"


class ProjectSchedule(models.Model):
    WEEKDAY_CHOICES = [
        (0, _("Monday")),
        (1, _("Tuesday")),
        (2, _("Wednesday")),
        (3, _("Thursday")),
        (4, _("Friday")),
        (5, _("Saturday")),
        (6, _("Sunday")),
    ]

    project_task = models.ForeignKey(
        ProjectTask,
        on_delete=models.CASCADE,
        related_name="schedules",
        help_text=_("Associated project task")
    )
    day_of_week = models.IntegerField(
        _("day of week"),
        choices=WEEKDAY_CHOICES,
        help_text=_("Day of week to schedule (0=Monday, 6=Sunday)")
    )
    start_time = models.TimeField(
        _("start time"),
        help_text=_("Task start time")
    )
    duration_hours = models.FloatField(
        _("duration (hours)"),
        default=1.0,
        help_text=_("Duration in hours")
    )
    weeks = models.PositiveIntegerField(
        _("weeks"),
        default=1,
        help_text=_("How many weeks to repeat")
    )
    is_active = models.BooleanField(
        _("is active"),
        default=True,
        help_text=_("Whether this schedule is active")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Project Schedule")
        verbose_name_plural = _("Project Schedules")
        unique_together = ["project_task", "day_of_week"]

    def __str__(self) -> str:
        day_name = dict(self.WEEKDAY_CHOICES)[self.day_of_week]
        return f"{self.project_task.title} - {day_name} {self.start_time}"

    def get_end_time(self):
        from datetime import datetime, timedelta, time
        start = datetime.combine(datetime.today(), self.start_time)
        end = start + timedelta(hours=self.duration_hours)
        return end.time()

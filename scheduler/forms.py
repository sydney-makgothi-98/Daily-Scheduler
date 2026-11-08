from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from scheduler.models import FOCUS_MAX_PER_DAY, PersonalTask, TaskCategory, TaskMode, SubTask, PrayerCompletion
from scheduler.planning import focus_task_count, prayer_conflict


class PersonalTaskForm(forms.ModelForm):
    class Meta:
        model = PersonalTask
        fields = ["title", "description", "date", "start_time", "end_time", "category", "task_type"]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Task title",
                "required": True,
            }),
            "description": forms.Textarea(attrs={
                "class": "form-textarea",
                "placeholder": "Optional description (e.g., what to do, resources needed)",
                "rows": 4,
            }),
            "date": forms.DateInput(attrs={
                "class": "form-input",
                "type": "date",
                "required": True,
            }),
            "start_time": forms.TimeInput(attrs={
                "class": "form-input",
                "type": "time",
                "required": True,
            }),
            "end_time": forms.TimeInput(attrs={
                "class": "form-input",
                "type": "time",
                "required": True,
            }),
            "category": forms.Select(attrs={
                "class": "form-select",
                "required": True,
            }),
            "task_type": forms.Select(attrs={
                "class": "form-select",
                "required": True,
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        date = cleaned_data.get("date")
        category = cleaned_data.get("category")

        # Validate start_time < end_time
        if start_time and end_time:
            if start_time >= end_time:
                raise ValidationError(
                    "End time must be after start time."
                )

        # Prayer times are non-negotiable in every mode: nothing may overlap a prayer window.
        if start_time and end_time and start_time < end_time:
            prayer = prayer_conflict(start_time, end_time)
            if prayer:
                raise ValidationError(
                    f"This overlaps {prayer.get_prayer_name_display()} "
                    f"({prayer.start_time:%H:%M}-{prayer.end_time:%H:%M}). Prayer time can't be scheduled over."
                )

        # Focus mode: at most FOCUS_MAX_PER_DAY focus tasks per day.
        if cleaned_data.get("task_type") == TaskMode.FOCUS and date:
            if focus_task_count(date, exclude_pk=self.instance.pk) >= FOCUS_MAX_PER_DAY:
                raise ValidationError(
                    f"Focus days allow at most {FOCUS_MAX_PER_DAY} focus tasks. "
                    "Change one of the existing ones to Multi-Task, or pick another day."
                )

        # Store late task warning in cleaned data (don't block submission)
        if start_time and start_time.hour >= 20:
            cleaned_data['late_task_warning'] = True

        # Validate date is not in the past
        if date and date < timezone.now().date():
            raise ValidationError(
                "Cannot create tasks for past dates."
            )

        # Validate NON-NEGOTIABLE tasks limit (max 3 per day)
        if category == TaskCategory.NON_NEGOTIABLE and date:
            existing_non_negotiable = PersonalTask.objects.filter(
                date=date,
                category=TaskCategory.NON_NEGOTIABLE
            ).count()

            if existing_non_negotiable >= 3:
                raise ValidationError(
                    "You already have 3 non-negotiable tasks for this day (the maximum recommended). "
                    "Consider marking some as secondary or rescheduling."
                )

        return cleaned_data


class SubTaskForm(forms.ModelForm):
    class Meta:
        model = SubTask
        fields = ["title", "is_completed", "order"]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Sub-task title",
                "required": True,
            }),
            "is_completed": forms.CheckboxInput(attrs={
                "class": "form-checkbox",
            }),
            "order": forms.NumberInput(attrs={
                "class": "form-input",
                "type": "number",
                "min": "0",
            }),
        }


class PrayerCompletionForm(forms.ModelForm):
    class Meta:
        model = PrayerCompletion
        fields = ["prayer_name", "date", "is_completed", "completed_at"]
        widgets = {
            "prayer_name": forms.Select(attrs={
                "class": "form-select",
                "required": True,
            }),
            "date": forms.DateInput(attrs={
                "class": "form-input",
                "type": "date",
                "required": True,
            }),
            "is_completed": forms.CheckboxInput(attrs={
                "class": "form-checkbox",
            }),
            "completed_at": forms.DateTimeInput(attrs={
                "class": "form-input",
                "type": "datetime-local",
            }),
        }

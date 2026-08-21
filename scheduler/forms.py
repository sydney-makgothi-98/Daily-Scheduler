from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from scheduler.models import PersonalTask, TaskCategory


class PersonalTaskForm(forms.ModelForm):
    class Meta:
        model = PersonalTask
        fields = ["title", "description", "date", "start_time", "end_time", "category"]
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

        # Warn about late tasks (past 20:00)
        if start_time and start_time.hour >= 20:
            self.add_error(
                "start_time",
                "⚠️ Warning: Tasks after 20:00 are detrimental to sleep. Consider rescheduling."
            )

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

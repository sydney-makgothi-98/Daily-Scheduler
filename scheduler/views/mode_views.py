import json
from datetime import datetime

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from scheduler.models import (
    FOCUS_MAX_PER_DAY,
    POMODORO_BREAK_MINUTES,
    POMODORO_WORK_MINUTES,
    DayPlan,
    PersonalTask,
    PrayerSchedule,
    TaskMode,
)
from scheduler.planning import focus_slots_left


def home(request):
    """Landing page: choose Multi-Task or Focus for today."""
    today = timezone.now().date()
    tasks = PersonalTask.objects.filter(date=today, is_break=False)
    context = {
        "today": today,
        "day_type": DayPlan.type_for(today),
        "multi_count": tasks.filter(task_type=TaskMode.MULTI).count(),
        "focus_count": tasks.filter(task_type=TaskMode.FOCUS).count(),
        "focus_max": FOCUS_MAX_PER_DAY,
    }
    return render(request, "admin/scheduler/home.html", context)


def focus_day(request, year=None, month=None, day=None):
    """Focus view: only the (at most two) focus tasks of a day, with prayers as fixed markers."""
    if year is None:
        date = timezone.now().date()
    else:
        try:
            date = datetime(year, month, day).date()
        except ValueError:
            return redirect("focus_today")

    tasks = list(
        PersonalTask.objects.filter(date=date, task_type=TaskMode.FOCUS, is_break=False)
        .order_by("start_time")
        .prefetch_related("subtasks")
    )
    prayers = PrayerSchedule.objects.all().order_by("start_time")
    context = {
        "date": date,
        "date_display": date.strftime("%A, %B %d, %Y"),
        "is_today": date == timezone.now().date(),
        "tasks": tasks,
        "prayers": prayers,
        "slots_left": focus_slots_left(date),
        "focus_max": FOCUS_MAX_PER_DAY,
        "work_minutes": POMODORO_WORK_MINUTES,
        "break_minutes": POMODORO_BREAK_MINUTES,
        "day_type": DayPlan.type_for(date),
    }
    return render(request, "admin/scheduler/focus_day.html", context)


@require_http_methods(["POST"])
def set_day_type(request, year, month, day):
    """Set whether a day is a Multi or Focus day (JSON body: {"day_type": "focus"})."""
    try:
        date = datetime(year, month, day).date()
        value = json.loads(request.body or b"{}").get("day_type")
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid request"}, status=400)
    if value not in TaskMode.values:
        return JsonResponse({"error": "day_type must be 'multi' or 'focus'"}, status=400)
    DayPlan.objects.update_or_create(date=date, defaults={"day_type": value})
    return JsonResponse({"success": True, "date": date.isoformat(), "day_type": value})

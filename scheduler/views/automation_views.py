import json
from datetime import datetime, timedelta

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from scheduler.automation import carry_over_incomplete, generate_recurring, quick_add
from scheduler.models import DayPlan, RecurringTask, TaskCategory, TaskMode

WEEKDAYS = [(0, "Mon"), (1, "Tue"), (2, "Wed"), (3, "Thu"), (4, "Fri"), (5, "Sat"), (6, "Sun")]


@require_http_methods(["GET", "POST"])
def recurring_list(request):
    """List recurring templates and create new ones."""
    if request.method == "POST":
        days = sorted({int(d) for d in request.POST.getlist("weekdays") if d.isdigit() and 0 <= int(d) <= 6})
        title = request.POST.get("title", "").strip()
        try:
            start = datetime.strptime(request.POST.get("start_time", ""), "%H:%M").time()
            end = datetime.strptime(request.POST.get("end_time", ""), "%H:%M").time()
        except ValueError:
            start = end = None
        if not title or not days or not start or not end or start >= end:
            messages.error(request, "Give it a title, at least one weekday and a start time before the end time.")
        else:
            category = request.POST.get("category")
            task_type = request.POST.get("task_type")
            RecurringTask.objects.create(
                title=title,
                weekdays=",".join(map(str, days)),
                start_time=start,
                end_time=end,
                category=category if category in TaskCategory.values else TaskCategory.SECONDARY,
                task_type=task_type if task_type in TaskMode.values else TaskMode.MULTI,
            )
            report = generate_recurring(datetime.now().date())  # create today's copy right away if it applies
            messages.success(request, f"Recurring task '{title}' saved." + (" Today's copy was added." if report.created else ""))
            for skipped in report.skipped:
                messages.warning(request, skipped)
            return redirect("recurring_list")
    return render(
        request,
        "admin/scheduler/recurring.html",
        {
            "items": RecurringTask.objects.all(),
            "weekdays": WEEKDAYS,
            "categories": TaskCategory.choices,
            "modes": TaskMode.choices,
        },
    )


@require_POST
def recurring_delete(request, pk):
    get_object_or_404(RecurringTask, pk=pk).delete()
    messages.success(request, "Recurring task deleted. Tasks already generated were kept.")
    return redirect("recurring_list")


@require_POST
def recurring_toggle(request, pk):
    rt = get_object_or_404(RecurringTask, pk=pk)
    rt.is_active = not rt.is_active
    rt.save(update_fields=["is_active"])
    return redirect("recurring_list")


@require_POST
def quick_add_api(request, year, month, day):
    """POST {"text": "Study maths 4pm 1h #focus"} -> creates the task using the normal form rules."""
    try:
        date = datetime(year, month, day).date()
        text = json.loads(request.body or b"{}").get("text", "")
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({"success": False, "error": "Invalid request"}, status=400)
    task, error = quick_add(text, date, default_type=DayPlan.type_for(date))
    if error:
        return JsonResponse({"success": False, "error": error}, status=400)
    return JsonResponse(
        {
            "success": True,
            "id": task.id,
            "title": task.title,
            "start_time": task.start_time.strftime("%H:%M"),
            "end_time": task.end_time.strftime("%H:%M"),
            "task_type": task.task_type,
        }
    )


@require_POST
def carry_over_api(request, year, month, day):
    """Move yesterday's unfinished tasks into today's free slots."""
    try:
        date = datetime(year, month, day).date()
    except ValueError:
        return JsonResponse({"success": False, "error": "Invalid date"}, status=400)
    report = carry_over_incomplete(date - timedelta(days=1), date)
    return JsonResponse(
        {
            "success": True,
            "created": [{"id": t.id, "title": t.title, "start_time": t.start_time.strftime("%H:%M")} for t in report.created],
            "skipped": report.skipped,
        }
    )

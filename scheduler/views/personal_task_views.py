from datetime import datetime, timedelta, time
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.utils import timezone
from django.db import models
import json

from scheduler.models import PersonalTask, PrayerSchedule, TaskCategory, TaskCompletion, SubTask, PrayerCompletion, PrayerName
from scheduler.forms import PersonalTaskForm


def auto_insert_breaks(task):
    """Automatically insert a 10-minute break after tasks >= 1 hour"""
    if task.is_break:
        return

    start = datetime.combine(task.date, task.start_time)
    end = datetime.combine(task.date, task.end_time)
    duration = (end - start).total_seconds() / 60

    if duration >= 60:
        break_start = task.end_time
        break_end_time = (datetime.combine(task.date, task.end_time) + timedelta(minutes=10)).time()

        existing_break = PersonalTask.objects.filter(
            date=task.date,
            start_time=break_start,
            is_break=True,
            parent_task=task
        ).exists()

        if not existing_break:
            conflicting_tasks = PersonalTask.objects.filter(
                date=task.date,
                start_time__lt=break_end_time,
                end_time__gt=break_start
            ).exclude(id=task.id).exists()

            if not conflicting_tasks:
                PersonalTask.objects.create(
                    title="🔔 Break",
                    description="Auto-inserted break to prevent burnout",
                    date=task.date,
                    start_time=break_start,
                    end_time=break_end_time,
                    category=TaskCategory.FUN,
                    is_break=True,
                    parent_task=task,
                    is_completed=False
                )


def calendar_view(request):
    """Display monthly calendar with task indicators"""
    today = timezone.now().date()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))

    # Get first day of month and calculate calendar grid
    first_day = datetime(year, month, 1).date()
    start_of_week = first_day - timedelta(days=first_day.weekday())

    # Generate calendar grid (6 weeks)
    calendar_days = []
    current_date = start_of_week
    while len(calendar_days) < 42:
        calendar_days.append(current_date)
        current_date += timedelta(days=1)

    # Get task counts for each day
    task_counts = {}
    for day in calendar_days:
        tasks = PersonalTask.objects.filter(date=day)
        completed = tasks.filter(is_completed=True).count()
        total = tasks.count()
        task_counts[day] = {
            "total": total,
            "completed": completed,
            "percentage": (completed / total * 100) if total > 0 else 0,
        }

    # Group days into weeks
    weeks = []
    for i in range(0, len(calendar_days), 7):
        weeks.append(calendar_days[i : i + 7])

    # Navigation
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year

    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year

    context = {
        "year": year,
        "month": month,
        "month_name": datetime(year, month, 1).strftime("%B"),
        "weeks": weeks,
        "task_counts": task_counts,
        "today": today,
        "prev_url": f"?year={prev_year}&month={prev_month}",
        "next_url": f"?year={next_year}&month={next_month}",
    }

    return render(request, "admin/scheduler/calendar_view.html", context)


def task_data_view(request, year, month, day):
    """Display tasks for a specific date with timeline"""
    try:
        date = datetime(year, month, day).date()
    except ValueError:
        messages.error(request, "Invalid date")
        return redirect("calendar_view")

    # Get all tasks for this date
    tasks = PersonalTask.objects.filter(date=date).order_by("start_time")

    # Get prayer times
    prayers = PrayerSchedule.objects.all().order_by("start_time")

    # Create timeline items (tasks + prayers)
    timeline_items = []

    # Add prayers with completion status
    for prayer in prayers:
        # Check if prayer was completed today
        prayer_completion = PrayerCompletion.objects.filter(
            prayer_name=prayer.prayer_name,
            date=date
        ).first()

        timeline_items.append({
            "type": "prayer",
            "name": prayer.get_prayer_name_display(),
            "prayer_name": prayer.prayer_name,
            "start_time": prayer.start_time,
            "end_time": prayer.end_time,
            "icon": "🕌",
            "is_completed": prayer_completion.is_completed if prayer_completion else False,
        })

    # Add tasks
    for task in tasks:
        timeline_items.append({
            "type": "task",
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "start_time": task.start_time,
            "end_time": task.end_time,
            "category": task.category,
            "category_display": task.get_category_display(),
            "is_completed": task.is_completed,
            "icon": get_category_icon(task.category),
        })

    # Sort by start time
    timeline_items.sort(key=lambda x: x["start_time"])

    # Check for late tasks (past 20:00)
    late_tasks = [item for item in timeline_items if item.get("start_time", time()) >= time(20, 0) and item["type"] == "task"]

    # Count tasks by category
    task_stats = {
        "non_negotiable": tasks.filter(category=TaskCategory.NON_NEGOTIABLE).count(),
        "secondary": tasks.filter(category=TaskCategory.SECONDARY).count(),
        "fun": tasks.filter(category=TaskCategory.FUN).count(),
    }

    context = {
        "date": date,
        "date_display": date.strftime("%A, %B %d, %Y"),
        "timeline_items": timeline_items,
        "late_tasks": late_tasks,
        "task_stats": task_stats,
        "today": timezone.now().date(),
    }

    return render(request, "admin/scheduler/task_data_view.html", context)


def get_category_icon(category):
    """Get icon for task category"""
    icons = {
        TaskCategory.NON_NEGOTIABLE: "⭐",
        TaskCategory.SECONDARY: "📋",
        TaskCategory.FUN: "🎉",
    }
    return icons.get(category, "📝")


def get_tasks_by_date_api(request, year, month, day):
    """API endpoint to fetch tasks for a specific date"""
    try:
        date = datetime(year, month, day).date()
    except ValueError:
        return JsonResponse({"error": "Invalid date"}, status=400)

    tasks = PersonalTask.objects.filter(date=date).values(
        "id", "title", "start_time", "end_time", "category", "is_completed"
    )

    return JsonResponse({
        "date": date.isoformat(),
        "tasks": list(tasks)
    })


@require_http_methods(["GET", "POST"])
def create_personal_task(request, year, month, day):
    """Create a new personal task for a specific date"""
    try:
        date = datetime(year, month, day).date()
    except ValueError:
        messages.error(request, "Invalid date")
        return redirect("calendar_view")

    if request.method == "POST":
        form = PersonalTaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.save()

            # Handle subtasks if provided
            subtasks_json = request.POST.get("subtasks_json")
            if subtasks_json:
                try:
                    subtasks_data = json.loads(subtasks_json)
                    for subtask_data in subtasks_data:
                        SubTask.objects.create(
                            personal_task=task,
                            title=subtask_data.get("title"),
                            order=subtask_data.get("order", 0)
                        )
                except (json.JSONDecodeError, KeyError) as e:
                    messages.warning(request, "Task created, but some subtasks could not be added.")

            # Auto-insert breaks for tasks >= 1 hour
            auto_insert_breaks(task)

            messages.success(request, f"Task '{task.title}' created successfully!")
            return redirect("task_data_view", year=date.year, month=date.month, day=date.day)
    else:
        initial_data = {"date": date}
        form = PersonalTaskForm(initial=initial_data)

    context = {
        "form": form,
        "date": date,
        "date_display": date.strftime("%A, %B %d, %Y"),
    }
    return render(request, "admin/scheduler/create_personal_task.html", context)


@require_http_methods(["GET", "POST"])
def edit_personal_task(request, task_id):
    """Edit an existing personal task"""
    task = get_object_or_404(PersonalTask, id=task_id)

    if request.method == "POST":
        form = PersonalTaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()

            # Handle subtasks if provided
            subtasks_json = request.POST.get("subtasks_json")
            if subtasks_json:
                try:
                    subtasks_data = json.loads(subtasks_json)
                    # Delete existing subtasks and recreate them
                    task.subtasks.all().delete()
                    for subtask_data in subtasks_data:
                        SubTask.objects.create(
                            personal_task=task,
                            title=subtask_data.get("title"),
                            order=subtask_data.get("order", 0)
                        )
                except (json.JSONDecodeError, KeyError) as e:
                    messages.warning(request, "Task updated, but some subtasks could not be updated.")

            # Delete old break and create new one if needed
            task.breaks.all().delete()
            auto_insert_breaks(task)

            messages.success(request, f"Task '{task.title}' updated successfully!")
            return redirect("task_data_view", year=task.date.year, month=task.date.month, day=task.date.day)
    else:
        form = PersonalTaskForm(instance=task)

    context = {
        "form": form,
        "task": task,
        "date": task.date,
        "date_display": task.date.strftime("%A, %B %d, %Y"),
        "is_edit": True,
        "existing_subtasks": list(task.subtasks.values("id", "title", "is_completed", "order")),
    }
    return render(request, "admin/scheduler/create_personal_task.html", context)


@require_http_methods(["POST"])
def delete_personal_task(request, task_id):
    """Delete a personal task"""
    task = get_object_or_404(PersonalTask, id=task_id)
    date = task.date
    title = task.title

    task.delete()
    messages.success(request, f"Task '{title}' deleted successfully!")
    return redirect("task_data_view", year=date.year, month=date.month, day=date.day)


@csrf_exempt
@require_http_methods(["POST"])
def toggle_task_completion(request, task_id):
    """Toggle task completion status via AJAX"""
    task = get_object_or_404(PersonalTask, id=task_id)

    try:
        data = json.loads(request.body)
        is_completed = data.get("is_completed", False)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

    try:
        # Update task completion status
        task.is_completed = is_completed
        task.save()

        # Calculate performance rating
        performance_data = task.get_performance_rating()
        performance_rating = performance_data.get("label", "N/A")

        # Record completion in history with performance rating
        TaskCompletion.objects.create(
            task=task,
            is_completed=is_completed,
            performance_rating=performance_rating
        )

        # Get all subtasks for response
        subtasks = task.subtasks.all().values("id", "title", "is_completed")

        return JsonResponse({
            "success": True,
            "task_id": task.id,
            "is_completed": task.is_completed,
            "performance_rating": performance_rating,
            "performance_data": performance_data,
            "subtasks": list(subtasks),
            "message": f"Task marked as {'completed' if is_completed else 'incomplete'}"
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def create_subtask(request, task_id):
    """Create a subtask for a personal task via AJAX"""
    task = get_object_or_404(PersonalTask, id=task_id)

    try:
        data = json.loads(request.body)
        title = data.get("title", "").strip()
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if not title:
        return JsonResponse({"error": "Subtask title is required"}, status=400)

    try:
        # Get the maximum order number for this task
        max_order = task.subtasks.aggregate(models.Max("order"))["order__max"] or 0

        subtask = SubTask.objects.create(
            personal_task=task,
            title=title,
            order=max_order + 1
        )

        return JsonResponse({
            "success": True,
            "subtask_id": subtask.id,
            "title": subtask.title,
            "is_completed": subtask.is_completed,
            "order": subtask.order,
            "message": "Subtask created successfully"
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def toggle_subtask_completion(request, subtask_id):
    """Toggle subtask completion status via AJAX"""
    subtask = get_object_or_404(SubTask, id=subtask_id)

    try:
        data = json.loads(request.body)
        is_completed = data.get("is_completed", False)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    try:
        subtask.is_completed = is_completed
        subtask.save()

        # Get updated performance rating for parent task
        task = subtask.personal_task
        performance_data = task.get_performance_rating()

        return JsonResponse({
            "success": True,
            "subtask_id": subtask.id,
            "is_completed": subtask.is_completed,
            "task_id": task.id,
            "performance_data": performance_data,
            "message": f"Subtask marked as {'completed' if is_completed else 'incomplete'}"
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def delete_subtask(request, subtask_id):
    """Delete a subtask via AJAX"""
    subtask = get_object_or_404(SubTask, id=subtask_id)
    task_id = subtask.personal_task.id

    try:
        subtask.delete()

        # Get updated performance rating
        task = PersonalTask.objects.get(id=task_id)
        performance_data = task.get_performance_rating()

        return JsonResponse({
            "success": True,
            "subtask_id": subtask_id,
            "task_id": task_id,
            "performance_data": performance_data,
            "message": "Subtask deleted successfully"
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_task_subtasks(request, task_id):
    """Get all subtasks for a task via AJAX"""
    task = get_object_or_404(PersonalTask, id=task_id)

    try:
        subtasks = task.subtasks.all().values("id", "title", "is_completed", "order")
        performance_data = task.get_performance_rating()

        return JsonResponse({
            "success": True,
            "task_id": task_id,
            "subtasks": list(subtasks),
            "performance_data": performance_data,
            "subtask_count": len(list(subtasks))
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_yesterday_tasks(request, year, month, day):
    """Fetch tasks from the previous day"""
    try:
        current_date = datetime(year, month, day).date()
        yesterday = current_date - timedelta(days=1)
    except ValueError:
        return JsonResponse({"error": "Invalid date"}, status=400)

    tasks = PersonalTask.objects.filter(date=yesterday).order_by("start_time")

    task_list = []
    for task in tasks:
        task_list.append({
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "start_time": task.start_time.strftime("%H:%M"),
            "end_time": task.end_time.strftime("%H:%M"),
            "category": task.category,
            "category_display": task.get_category_display(),
        })

    return JsonResponse({
        "success": True,
        "date": yesterday.isoformat(),
        "tasks": task_list
    })


@csrf_exempt
@require_http_methods(["POST"])
def copy_tasks_from_yesterday(request, year, month, day):
    """Copy selected tasks from yesterday to today"""
    try:
        current_date = datetime(year, month, day).date()
        yesterday = current_date - timedelta(days=1)
    except ValueError:
        return JsonResponse({"error": "Invalid date"}, status=400)

    try:
        data = json.loads(request.body)
        task_ids = data.get("task_ids", [])
        time_overrides = data.get("time_overrides", {})
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    copied_tasks = []
    errors = []

    for task_id in task_ids:
        try:
            original_task = PersonalTask.objects.get(id=task_id, date=yesterday)

            # Get time overrides if provided
            start_time = original_task.start_time
            end_time = original_task.end_time

            if str(task_id) in time_overrides:
                override = time_overrides[str(task_id)]
                if "start_time" in override:
                    start_time = datetime.strptime(override["start_time"], "%H:%M").time()
                if "end_time" in override:
                    end_time = datetime.strptime(override["end_time"], "%H:%M").time()

            # Create the copied task
            new_task = PersonalTask.objects.create(
                title=original_task.title,
                description=original_task.description,
                date=current_date,
                start_time=start_time,
                end_time=end_time,
                category=original_task.category,
                is_completed=False
            )

            # Copy subtasks if any
            for subtask in original_task.subtasks.all():
                SubTask.objects.create(
                    personal_task=new_task,
                    title=subtask.title,
                    order=subtask.order
                )

            copied_tasks.append({
                "id": new_task.id,
                "title": new_task.title,
                "start_time": new_task.start_time.strftime("%H:%M"),
                "end_time": new_task.end_time.strftime("%H:%M"),
            })
        except PersonalTask.DoesNotExist:
            errors.append(f"Task {task_id} not found for yesterday")
        except Exception as e:
            errors.append(f"Error copying task {task_id}: {str(e)}")

    return JsonResponse({
        "success": len(copied_tasks) > 0,
        "copied_tasks": copied_tasks,
        "errors": errors,
        "message": f"Successfully copied {len(copied_tasks)} task(s)"
    })

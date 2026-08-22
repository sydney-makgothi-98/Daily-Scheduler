from datetime import datetime, timedelta
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count, Q

from scheduler.models import PersonalTask, TaskCompletion, TaskCategory, SubTask, PrayerCompletion, PrayerName


def get_date_range(filter_type):
    """Get start and end dates based on filter type"""
    today = timezone.now().date()

    if filter_type == "week":
        # Get current week (Monday to Sunday)
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
    elif filter_type == "month":
        # Get current month
        start_date = today.replace(day=1)
        if today.month == 12:
            end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_date = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    else:  # Default to week
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)

    return start_date, end_date


def calculate_completion_stats(start_date, end_date, category=None):
    """Calculate completion statistics for a date range"""
    # Get all tasks in range
    tasks_query = PersonalTask.objects.filter(date__range=[start_date, end_date])

    if category:
        tasks_query = tasks_query.filter(category=category)

    # Get completions
    completed = tasks_query.filter(is_completed=True).count()
    total = tasks_query.count()

    return {
        "completed": completed,
        "incomplete": total - completed,
        "total": total,
        "percentage": (completed / total * 100) if total > 0 else 0,
    }


def get_daily_stats(start_date, end_date, category=None):
    """Get daily completion stats for chart"""
    current_date = start_date
    daily_data = []

    while current_date <= end_date:
        tasks_query = PersonalTask.objects.filter(date=current_date)

        if category:
            tasks_query = tasks_query.filter(category=category)

        completed = tasks_query.filter(is_completed=True).count()
        total = tasks_query.count()

        daily_data.append({
            "date": current_date.isoformat(),
            "day": current_date.strftime("%a"),
            "completed": completed,
            "incomplete": total - completed,
            "total": total,
            "percentage": (completed / total * 100) if total > 0 else 0,
        })

        current_date += timedelta(days=1)

    return daily_data


def calculate_subtask_completion_stats(start_date, end_date):
    """Calculate subtask completion statistics for a date range"""
    # Get all subtasks for tasks within date range
    tasks = PersonalTask.objects.filter(date__range=[start_date, end_date])
    subtasks = SubTask.objects.filter(personal_task__in=tasks)

    completed = subtasks.filter(is_completed=True).count()
    total = subtasks.count()

    return {
        "completed": completed,
        "incomplete": total - completed,
        "total": total,
        "percentage": (completed / total * 100) if total > 0 else 0,
    }


def get_daily_subtask_stats(start_date, end_date):
    """Get daily subtask completion stats for chart"""
    current_date = start_date
    daily_data = []

    while current_date <= end_date:
        tasks = PersonalTask.objects.filter(date=current_date)
        subtasks = SubTask.objects.filter(personal_task__in=tasks)

        completed = subtasks.filter(is_completed=True).count()
        total = subtasks.count()

        daily_data.append({
            "date": current_date.isoformat(),
            "day": current_date.strftime("%a"),
            "completed": completed,
            "incomplete": total - completed,
            "total": total,
            "percentage": (completed / total * 100) if total > 0 else 0,
        })

        current_date += timedelta(days=1)

    return daily_data


def calculate_prayer_completion_stats(start_date, end_date):
    """Calculate prayer completion statistics for a date range"""
    prayers = PrayerCompletion.objects.filter(date__range=[start_date, end_date])

    completed = prayers.filter(is_completed=True).count()
    total = prayers.count()

    return {
        "completed": completed,
        "incomplete": total - completed,
        "total": total,
        "percentage": (completed / total * 100) if total > 0 else 0,
    }


def get_prayer_stats_by_name(start_date, end_date):
    """Get prayer completion stats by prayer name"""
    prayer_stats = []

    for prayer_name, prayer_display in PrayerName.choices:
        prayers = PrayerCompletion.objects.filter(
            prayer_name=prayer_name,
            date__range=[start_date, end_date]
        )

        completed = prayers.filter(is_completed=True).count()
        total = prayers.count()

        prayer_stats.append({
            "prayer_name": prayer_name,
            "prayer_display": prayer_display,
            "completed": completed,
            "incomplete": total - completed,
            "total": total,
            "percentage": (completed / total * 100) if total > 0 else 0,
        })

    return prayer_stats


def get_daily_prayer_stats(start_date, end_date):
    """Get daily prayer completion stats for chart"""
    current_date = start_date
    daily_data = []

    while current_date <= end_date:
        prayers = PrayerCompletion.objects.filter(date=current_date)

        completed = prayers.filter(is_completed=True).count()
        total = prayers.count()

        daily_data.append({
            "date": current_date.isoformat(),
            "day": current_date.strftime("%a"),
            "completed": completed,
            "incomplete": total - completed,
            "total": total,
            "percentage": (completed / total * 100) if total > 0 else 0,
        })

        current_date += timedelta(days=1)

    return daily_data


def analytics_dashboard(request):
    """Main analytics dashboard"""
    filter_type = request.GET.get("filter", "week")
    start_date, end_date = get_date_range(filter_type)

    # Calculate stats for each category
    non_negotiable_stats = calculate_completion_stats(start_date, end_date, TaskCategory.NON_NEGOTIABLE)
    secondary_stats = calculate_completion_stats(start_date, end_date, TaskCategory.SECONDARY)
    fun_stats = calculate_completion_stats(start_date, end_date, TaskCategory.FUN)

    # Calculate subtask stats
    subtask_stats = calculate_subtask_completion_stats(start_date, end_date)

    # Calculate prayer stats
    prayer_stats = calculate_prayer_completion_stats(start_date, end_date)
    prayer_breakdown = get_prayer_stats_by_name(start_date, end_date)

    # Get daily data for charts
    non_negotiable_daily = get_daily_stats(start_date, end_date, TaskCategory.NON_NEGOTIABLE)
    secondary_daily = get_daily_stats(start_date, end_date, TaskCategory.SECONDARY)
    fun_daily = get_daily_stats(start_date, end_date, TaskCategory.FUN)
    subtask_daily = get_daily_subtask_stats(start_date, end_date)
    prayer_daily = get_daily_prayer_stats(start_date, end_date)

    # Determine alerts
    alerts = []

    if non_negotiable_stats["total"] > 0:
        if non_negotiable_stats["incomplete"] > non_negotiable_stats["completed"]:
            alerts.append({
                "type": "danger",
                "icon": "🔴",
                "title": "Non-Negotiables Alert",
                "message": f"You have more incomplete ({non_negotiable_stats['incomplete']}) than complete ({non_negotiable_stats['completed']}) non-negotiable tasks this {filter_type}."
            })

    if secondary_stats["total"] > 0:
        if secondary_stats["incomplete"] > secondary_stats["completed"]:
            alerts.append({
                "type": "warning",
                "icon": "🟡",
                "title": "Secondary Tasks Warning",
                "message": f"More incomplete ({secondary_stats['incomplete']}) than complete ({secondary_stats['completed']}) secondary tasks this {filter_type}."
            })

    if prayer_stats["total"] > 0:
        prayer_percentage = prayer_stats["percentage"]
        if prayer_percentage < 50:
            alerts.append({
                "type": "danger",
                "icon": "🕌",
                "title": "Prayer Completion Alert",
                "message": f"Prayer completion rate is low ({prayer_percentage:.0f}%). Aim for consistency in your daily prayers."
            })
        elif prayer_percentage < 75:
            alerts.append({
                "type": "info",
                "icon": "🕌",
                "title": "Prayer Completion Notice",
                "message": f"Prayer completion rate is {prayer_percentage:.0f}%. Keep improving!"
            })

    context = {
        "filter_type": filter_type,
        "start_date": start_date,
        "end_date": end_date,
        "period": f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}",
        "non_negotiable_stats": non_negotiable_stats,
        "secondary_stats": secondary_stats,
        "fun_stats": fun_stats,
        "subtask_stats": subtask_stats,
        "prayer_stats": prayer_stats,
        "prayer_breakdown": prayer_breakdown,
        "non_negotiable_daily": non_negotiable_daily,
        "secondary_daily": secondary_daily,
        "fun_daily": fun_daily,
        "subtask_daily": subtask_daily,
        "prayer_daily": prayer_daily,
        "alerts": alerts,
    }

    return render(request, "admin/scheduler/analytics_dashboard.html", context)


def get_chart_data_api(request):
    """API endpoint for chart data"""
    filter_type = request.GET.get("filter", "week")
    chart_type = request.GET.get("chart_type", "line")

    start_date, end_date = get_date_range(filter_type)

    # Get daily stats for each category
    non_negotiable_daily = get_daily_stats(start_date, end_date, TaskCategory.NON_NEGOTIABLE)
    secondary_daily = get_daily_stats(start_date, end_date, TaskCategory.SECONDARY)
    fun_daily = get_daily_stats(start_date, end_date, TaskCategory.FUN)
    subtask_daily = get_daily_subtask_stats(start_date, end_date)
    prayer_daily = get_daily_prayer_stats(start_date, end_date)

    # Format for Chart.js
    labels = [item["day"] for item in non_negotiable_daily]

    return JsonResponse({
        "labels": labels,
        "datasets": [
            {
                "label": "Non-Negotiable Completed",
                "data": [item["completed"] for item in non_negotiable_daily],
                "borderColor": "#10b981",
                "backgroundColor": "rgba(16, 185, 129, 0.1)",
                "borderWidth": 2,
                "tension": 0.4,
                "fill": True,
            },
            {
                "label": "Non-Negotiable Incomplete",
                "data": [item["incomplete"] for item in non_negotiable_daily],
                "borderColor": "#ef4444",
                "backgroundColor": "rgba(239, 68, 68, 0.1)",
                "borderWidth": 2,
                "tension": 0.4,
                "fill": True,
            },
            {
                "label": "Secondary Completed",
                "data": [item["completed"] for item in secondary_daily],
                "borderColor": "#0ea5e9",
                "backgroundColor": "rgba(14, 165, 233, 0.1)",
                "borderWidth": 2,
                "tension": 0.4,
                "fill": True,
            },
            {
                "label": "Secondary Incomplete",
                "data": [item["incomplete"] for item in secondary_daily],
                "borderColor": "#f59e0b",
                "backgroundColor": "rgba(245, 158, 11, 0.1)",
                "borderWidth": 2,
                "tension": 0.4,
                "fill": True,
            },
            {
                "label": "Fun Completed",
                "data": [item["completed"] for item in fun_daily],
                "borderColor": "#a78bfa",
                "backgroundColor": "rgba(167, 139, 250, 0.1)",
                "borderWidth": 2,
                "tension": 0.4,
                "fill": True,
            },
            {
                "label": "Fun Incomplete",
                "data": [item["incomplete"] for item in fun_daily],
                "borderColor": "#9ca3af",
                "backgroundColor": "rgba(156, 163, 175, 0.1)",
                "borderWidth": 2,
                "tension": 0.4,
                "fill": True,
            },
            {
                "label": "Sub-tasks Completed",
                "data": [item["completed"] for item in subtask_daily],
                "borderColor": "#ec4899",
                "backgroundColor": "rgba(236, 72, 153, 0.1)",
                "borderWidth": 2,
                "tension": 0.4,
                "fill": True,
                "hidden": False,
            },
            {
                "label": "Prayers Completed",
                "data": [item["completed"] for item in prayer_daily],
                "borderColor": "#8b5cf6",
                "backgroundColor": "rgba(139, 92, 246, 0.1)",
                "borderWidth": 2,
                "tension": 0.4,
                "fill": True,
                "hidden": False,
            },
        ]
    })


def get_subtask_chart_data_api(request):
    """API endpoint for subtask chart data"""
    filter_type = request.GET.get("filter", "week")
    start_date, end_date = get_date_range(filter_type)

    subtask_daily = get_daily_subtask_stats(start_date, end_date)
    labels = [item["day"] for item in subtask_daily]

    return JsonResponse({
        "labels": labels,
        "datasets": [
            {
                "label": "Sub-tasks Completed",
                "data": [item["completed"] for item in subtask_daily],
                "borderColor": "#10b981",
                "backgroundColor": "rgba(16, 185, 129, 0.1)",
                "borderWidth": 2,
                "tension": 0.4,
                "fill": True,
            },
            {
                "label": "Sub-tasks Incomplete",
                "data": [item["incomplete"] for item in subtask_daily],
                "borderColor": "#ef4444",
                "backgroundColor": "rgba(239, 68, 68, 0.1)",
                "borderWidth": 2,
                "tension": 0.4,
                "fill": True,
            },
        ]
    })


def get_prayer_chart_data_api(request):
    """API endpoint for prayer chart data"""
    filter_type = request.GET.get("filter", "week")
    start_date, end_date = get_date_range(filter_type)

    prayer_daily = get_daily_prayer_stats(start_date, end_date)
    labels = [item["day"] for item in prayer_daily]

    return JsonResponse({
        "labels": labels,
        "datasets": [
            {
                "label": "Prayers Completed",
                "data": [item["completed"] for item in prayer_daily],
                "borderColor": "#10b981",
                "backgroundColor": "rgba(16, 185, 129, 0.1)",
                "borderWidth": 2,
                "tension": 0.4,
                "fill": True,
            },
            {
                "label": "Prayers Incomplete",
                "data": [item["incomplete"] for item in prayer_daily],
                "borderColor": "#ef4444",
                "backgroundColor": "rgba(239, 68, 68, 0.1)",
                "borderWidth": 2,
                "tension": 0.4,
                "fill": True,
            },
        ]
    })

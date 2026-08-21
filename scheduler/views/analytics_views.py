from datetime import datetime, timedelta
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count, Q

from scheduler.models import PersonalTask, TaskCompletion, TaskCategory


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


def analytics_dashboard(request):
    """Main analytics dashboard"""
    filter_type = request.GET.get("filter", "week")
    start_date, end_date = get_date_range(filter_type)

    # Calculate stats for each category
    non_negotiable_stats = calculate_completion_stats(start_date, end_date, TaskCategory.NON_NEGOTIABLE)
    secondary_stats = calculate_completion_stats(start_date, end_date, TaskCategory.SECONDARY)
    fun_stats = calculate_completion_stats(start_date, end_date, TaskCategory.FUN)

    # Get daily data for charts
    non_negotiable_daily = get_daily_stats(start_date, end_date, TaskCategory.NON_NEGOTIABLE)
    secondary_daily = get_daily_stats(start_date, end_date, TaskCategory.SECONDARY)
    fun_daily = get_daily_stats(start_date, end_date, TaskCategory.FUN)

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

    context = {
        "filter_type": filter_type,
        "start_date": start_date,
        "end_date": end_date,
        "period": f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}",
        "non_negotiable_stats": non_negotiable_stats,
        "secondary_stats": secondary_stats,
        "fun_stats": fun_stats,
        "non_negotiable_daily": non_negotiable_daily,
        "secondary_daily": secondary_daily,
        "fun_daily": fun_daily,
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
        ]
    })

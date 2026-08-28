from datetime import datetime, timedelta, time
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.utils import timezone
from django.db import models
import json

from scheduler.models import Project, ProjectTask, ProjectSchedule, ProjectStatus, PersonalTask, TaskCategory


@require_http_methods(["GET", "POST"])
def projects_list(request):
    """Display all projects"""
    projects = Project.objects.all().order_by("-start_date")

    context = {
        "projects": projects,
        "status_choices": ProjectStatus.choices,
    }
    return render(request, "admin/scheduler/projects_list.html", context)


@require_http_methods(["GET", "POST"])
def create_project(request):
    """Create a new project"""
    if request.method == "POST":
        try:
            data = json.loads(request.body) if request.content_type == "application/json" else request.POST.dict()

            project = Project.objects.create(
                title=data.get("title", "").strip(),
                description=data.get("description", "").strip(),
                start_date=datetime.strptime(data.get("start_date"), "%Y-%m-%d").date(),
                end_date=datetime.strptime(data.get("end_date"), "%Y-%m-%d").date(),
                status=data.get("status", ProjectStatus.PLANNED)
            )

            if request.content_type == "application/json":
                return JsonResponse({
                    "success": True,
                    "project_id": project.id,
                    "message": f"Project '{project.title}' created successfully!"
                })
            else:
                messages.success(request, f"Project '{project.title}' created successfully!")
                return redirect("project_detail", project_id=project.id)
        except Exception as e:
            if request.content_type == "application/json":
                return JsonResponse({"success": False, "error": str(e)}, status=400)
            messages.error(request, f"Error creating project: {str(e)}")
            return render(request, "admin/scheduler/create_project.html")

    context = {
        "status_choices": ProjectStatus.choices,
    }
    return render(request, "admin/scheduler/create_project.html", context)


@require_http_methods(["GET", "POST"])
def project_detail(request, project_id):
    """View and edit project details"""
    project = get_object_or_404(Project, id=project_id)

    if request.method == "POST":
        try:
            project.title = request.POST.get("title", project.title)
            project.description = request.POST.get("description", project.description)
            project.status = request.POST.get("status", project.status)
            project.save()
            messages.success(request, "Project updated successfully!")
        except Exception as e:
            messages.error(request, f"Error updating project: {str(e)}")

        return redirect("project_detail", project_id=project.id)

    tasks = project.tasks.all().order_by("order")

    context = {
        "project": project,
        "tasks": tasks,
        "status_choices": ProjectStatus.choices,
        "progress": project.get_progress_percentage(),
    }
    return render(request, "admin/scheduler/project_detail.html", context)


@csrf_exempt
@require_http_methods(["POST"])
def create_project_task(request, project_id):
    """Create a task within a project"""
    project = get_object_or_404(Project, id=project_id)

    try:
        data = json.loads(request.body)

        max_order = project.tasks.aggregate(models.Max("order"))["order__max"] or 0

        task = ProjectTask.objects.create(
            project=project,
            title=data.get("title", "").strip(),
            description=data.get("description", "").strip(),
            duration_hours=float(data.get("duration_hours", 1.0)),
            order=max_order + 1
        )

        return JsonResponse({
            "success": True,
            "task_id": task.id,
            "task": {
                "id": task.id,
                "title": task.title,
                "duration_hours": task.duration_hours,
                "is_scheduled": task.is_scheduled,
            }
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_project_task(request, task_id):
    """Delete a project task"""
    task = get_object_or_404(ProjectTask, id=task_id)
    project_id = task.project.id

    try:
        task.delete()
        return JsonResponse({
            "success": True,
            "message": "Task deleted successfully!"
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def create_schedule(request, task_id):
    """Create a schedule for a project task"""
    task = get_object_or_404(ProjectTask, id=task_id)

    try:
        data = json.loads(request.body)
        day_of_week = int(data.get("day_of_week"))

        # Check if schedule already exists for this task on this day
        existing_schedule = ProjectSchedule.objects.filter(
            project_task=task,
            day_of_week=day_of_week
        ).exists()

        if existing_schedule:
            return JsonResponse({
                "success": False,
                "error": "You are scheduling the same task twice in one day"
            }, status=400)

        schedule = ProjectSchedule.objects.create(
            project_task=task,
            day_of_week=day_of_week,
            start_time=datetime.strptime(data.get("start_time"), "%H:%M").time(),
            duration_hours=float(data.get("duration_hours", task.duration_hours)),
            weeks=int(data.get("weeks", 1))
        )

        return JsonResponse({
            "success": True,
            "schedule_id": schedule.id,
            "schedule": {
                "id": schedule.id,
                "day_of_week": schedule.day_of_week,
                "start_time": schedule.start_time.strftime("%H:%M"),
                "end_time": schedule.get_end_time().strftime("%H:%M"),
                "duration_hours": schedule.duration_hours,
                "weeks": schedule.weeks,
            }
        })
    except Exception as e:
        error_msg = str(e)
        # Catch unique constraint errors and provide user-friendly message
        if "UNIQUE constraint failed" in error_msg and "day_of_week" in error_msg:
            error_msg = "You are scheduling the same task twice in one day"
        return JsonResponse({"success": False, "error": error_msg}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def generate_schedule(request, project_id):
    """Generate recurring PersonalTasks from project schedule"""
    project = get_object_or_404(Project, id=project_id)

    try:
        data = json.loads(request.body)
        task_ids = data.get("task_ids", [])

        # Check for conflicts first
        conflicts = []
        created_count = 0

        for project_task in project.tasks.filter(id__in=task_ids):
            for schedule in project_task.schedules.filter(is_active=True):
                current_date = project.start_date
                week_count = 0

                while current_date <= project.end_date and week_count < schedule.weeks:
                    # Find the next occurrence of this day of week
                    days_ahead = (schedule.day_of_week - current_date.weekday()) % 7
                    if days_ahead == 0 and current_date != project.start_date:
                        target_date = current_date + timedelta(days=7)
                    else:
                        target_date = current_date + timedelta(days=days_ahead)

                    if target_date > project.end_date:
                        break

                    end_time = (datetime.combine(target_date, schedule.start_time) +
                               timedelta(hours=schedule.duration_hours)).time()

                    # Check for conflicts
                    conflicting = PersonalTask.objects.filter(
                        date=target_date,
                        start_time__lt=end_time,
                        end_time__gt=schedule.start_time
                    ).exclude(is_break=True).exists()

                    if conflicting:
                        conflicts.append({
                            "task": project_task.title,
                            "date": target_date.isoformat(),
                            "time": f"{schedule.start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}"
                        })
                    else:
                        # Create the PersonalTask
                        PersonalTask.objects.create(
                            title=f"📊 {project.title}: {project_task.title}",
                            description=f"Project task for {project.title}",
                            date=target_date,
                            start_time=schedule.start_time,
                            end_time=end_time,
                            category=TaskCategory.NON_NEGOTIABLE,
                            is_completed=False,
                            is_break=False
                        )
                        created_count += 1

                    current_date = target_date + timedelta(days=1)
                    week_count += 1

                project_task.is_scheduled = True
                project_task.save()

        return JsonResponse({
            "success": True,
            "created": created_count,
            "conflicts": conflicts,
            "message": f"Generated {created_count} recurring tasks"
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_project(request, project_id):
    """Delete a project"""
    project = get_object_or_404(Project, id=project_id)

    try:
        project_title = project.title
        project.delete()

        return JsonResponse({
            "success": True,
            "message": f"Project '{project_title}' deleted successfully!"
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

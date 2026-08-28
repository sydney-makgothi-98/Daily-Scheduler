from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.utils import timezone
from django.db import models
from datetime import datetime
import json

from scheduler.models import PrayerSchedule, PrayerName, PrayerCompletion, PrayerCompletionStatus


def prayer_settings(request):
    prayers = PrayerSchedule.objects.all().order_by("start_time")
    context = {
        "prayers": prayers,
        "prayer_choices": PrayerName.choices,
    }
    return render(request, "admin/scheduler/prayer_settings.html", context)


def get_prayer_times_api(request):
    """API endpoint to fetch all prayer times as JSON"""
    prayers = PrayerSchedule.objects.all().values(
        "id", "prayer_name", "start_time", "end_time"
    )
    prayer_list = list(prayers)
    return JsonResponse({"prayers": prayer_list})


@require_http_methods(["GET", "POST"])
def create_prayer(request):
    if request.method == "POST":
        prayer_name = request.POST.get("prayer_name")
        start_time = request.POST.get("start_time")
        end_time = request.POST.get("end_time")

        if not all([prayer_name, start_time, end_time]):
            messages.error(request, "All fields are required")
            return redirect("prayer_settings")

        # Check if prayer already exists
        if PrayerSchedule.objects.filter(prayer_name=prayer_name).exists():
            messages.error(request, f"Prayer time for {prayer_name} already exists")
            return redirect("prayer_settings")

        try:
            PrayerSchedule.objects.create(
                prayer_name=prayer_name,
                start_time=start_time,
                end_time=end_time,
            )
            messages.success(request, f"Prayer time for {prayer_name} created successfully")
        except Exception as e:
            messages.error(request, f"Error creating prayer: {str(e)}")

        return redirect("prayer_settings")

    context = {
        "prayer_choices": PrayerName.choices,
    }
    return render(request, "admin/scheduler/create_prayer.html", context)


@require_http_methods(["GET", "POST"])
def update_prayer(request, prayer_id):
    prayer = get_object_or_404(PrayerSchedule, id=prayer_id)

    if request.method == "POST":
        start_time = request.POST.get("start_time")
        end_time = request.POST.get("end_time")

        if not all([start_time, end_time]):
            messages.error(request, "All fields are required")
            return redirect("prayer_settings")

        try:
            prayer.start_time = start_time
            prayer.end_time = end_time
            prayer.save()
            messages.success(request, f"Prayer time for {prayer.get_prayer_name_display()} updated successfully")
        except Exception as e:
            messages.error(request, f"Error updating prayer: {str(e)}")

        return redirect("prayer_settings")

    context = {
        "prayer": prayer,
    }
    return render(request, "admin/scheduler/update_prayer.html", context)


@require_http_methods(["POST"])
def delete_prayer(request, prayer_id):
    prayer = get_object_or_404(PrayerSchedule, id=prayer_id)
    prayer_name = prayer.get_prayer_name_display()

    try:
        prayer.delete()
        messages.success(request, f"Prayer time for {prayer_name} deleted successfully")
    except Exception as e:
        messages.error(request, f"Error deleting prayer: {str(e)}")

    return redirect("prayer_settings")


@csrf_exempt
@require_http_methods(["POST"])
def toggle_prayer_completion(request, prayer_name):
    """Toggle prayer completion for a specific date via AJAX"""
    try:
        data = json.loads(request.body)
        date_str = data.get("date")
        is_completed = data.get("is_completed", False)
        status = data.get("status", "not_yet")  # prayed, not_yet, or missed
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if not date_str:
        return JsonResponse({"error": "Date is required"}, status=400)

    try:
        # Parse the date
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

        # Get or create prayer completion record
        prayer_completion, created = PrayerCompletion.objects.get_or_create(
            prayer_name=prayer_name,
            date=date_obj
        )

        # Map status to is_completed and set the status field
        if status == "prayed":
            prayer_completion.is_completed = True
            prayer_completion.status = PrayerCompletionStatus.PRAYED
            prayer_completion.completed_at = timezone.now()
        elif status == "missed":
            prayer_completion.is_completed = False
            prayer_completion.status = PrayerCompletionStatus.MISSED
            prayer_completion.completed_at = None
        else:  # not_yet
            prayer_completion.is_completed = False
            prayer_completion.status = PrayerCompletionStatus.NOT_YET
            prayer_completion.completed_at = None

        prayer_completion.save()

        return JsonResponse({
            "success": True,
            "prayer_name": prayer_name,
            "date": date_str,
            "is_completed": is_completed,
            "status": status,
            "message": f"Prayer marked as {status.replace('_', ' ')}"
        })
    except ValueError:
        return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD"}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["GET"])
def get_daily_prayer_completions(request, year, month, day):
    """Get all prayer completions for a specific date"""
    try:
        date_obj = datetime(year, month, day).date()
    except ValueError:
        return JsonResponse({"error": "Invalid date"}, status=400)

    try:
        # Get all prayer schedules
        prayers = PrayerSchedule.objects.all().order_by("start_time")

        # Get completions for this date
        completions = PrayerCompletion.objects.filter(date=date_obj).values_list("prayer_name", "is_completed")
        completion_dict = dict(completions)

        # Build response
        prayer_list = []
        for prayer in prayers:
            is_completed = completion_dict.get(prayer.prayer_name, False)

            # Get the completion record to fetch the status
            completion = PrayerCompletion.objects.filter(
                prayer_name=prayer.prayer_name,
                date=date_obj
            ).first()

            status = "not_yet"  # default
            if completion:
                status = completion.status

            prayer_list.append({
                "prayer_name": prayer.prayer_name,
                "prayer_display": prayer.get_prayer_name_display(),
                "start_time": prayer.start_time.isoformat(),
                "end_time": prayer.end_time.isoformat(),
                "is_completed": is_completed,
                "status": status,
            })

        # Calculate completion percentage
        total_prayers = len(prayer_list)
        completed_prayers = sum(1 for p in prayer_list if p["is_completed"])
        completion_percentage = (completed_prayers / total_prayers * 100) if total_prayers > 0 else 0

        return JsonResponse({
            "success": True,
            "date": date_obj.isoformat(),
            "prayers": prayer_list,
            "total_prayers": total_prayers,
            "completed_prayers": completed_prayers,
            "completion_percentage": completion_percentage,
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["GET"])
def get_prayer_stats(request, start_date=None, end_date=None):
    """Get prayer completion statistics for a date range"""
    try:
        # Use query params if provided
        start_date_str = request.GET.get("start_date", start_date)
        end_date_str = request.GET.get("end_date", end_date)

        if start_date_str and end_date_str:
            start_date_obj = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date_obj = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        else:
            return JsonResponse({"error": "start_date and end_date are required"}, status=400)

        # Get prayer completion statistics
        completions = PrayerCompletion.objects.filter(
            date__range=[start_date_obj, end_date_obj]
        ).values("prayer_name").annotate(
            total=models.Count("id"),
            completed=models.Count("id", filter=models.Q(is_completed=True))
        ).order_by("prayer_name")

        stats = []
        for completion in completions:
            percentage = (completion["completed"] / completion["total"] * 100) if completion["total"] > 0 else 0
            stats.append({
                "prayer_name": completion["prayer_name"],
                "prayer_display": dict(PrayerName.choices).get(completion["prayer_name"], completion["prayer_name"]),
                "total": completion["total"],
                "completed": completion["completed"],
                "percentage": percentage,
            })

        return JsonResponse({
            "success": True,
            "start_date": start_date_obj.isoformat(),
            "end_date": end_date_obj.isoformat(),
            "stats": stats,
        })
    except ValueError:
        return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD"}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

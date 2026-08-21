from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from scheduler.models import PrayerSchedule, PrayerName


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

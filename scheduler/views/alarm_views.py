from datetime import datetime

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from scheduler.alarms import events_for_day
from scheduler.models import AlarmSetting

_BOOL_FIELDS = ("enabled", "break_alarm", "prayer_alarm", "task_alarm")
_INT_FIELDS = {
    "break_lead_minutes": (0, 30),
    "prayer_lead_minutes": (0, 60),
    "snooze_minutes": (1, 60),
    "ring_seconds": (5, 600),
    "volume": (0, 100),
}


def _settings_dict(cfg: AlarmSetting) -> dict:
    return {f: getattr(cfg, f) for f in (*_BOOL_FIELDS, *_INT_FIELDS)}


@require_GET
def alarms_today_api(request):
    """Today's alarm events + settings. Used by the in-browser fallback alarm."""
    cfg = AlarmSetting.get()
    now = datetime.now()
    return JsonResponse(
        {
            "now": now.isoformat(),
            "settings": _settings_dict(cfg),
            "events": [e.as_dict() for e in events_for_day(now.date(), cfg)],
        }
    )


@require_http_methods(["GET", "POST"])
def alarm_settings(request):
    cfg = AlarmSetting.get()
    if request.method == "POST":
        for f in _BOOL_FIELDS:
            setattr(cfg, f, f in request.POST)
        for f, (lo, hi) in _INT_FIELDS.items():
            try:
                value = int(request.POST.get(f, getattr(cfg, f)))
            except ValueError:
                continue
            setattr(cfg, f, max(lo, min(hi, value)))
        cfg.save()
        messages.success(request, "Alarm settings saved.")
        return redirect("alarm_settings")
    return render(request, "admin/scheduler/alarm_settings.html", {"cfg": cfg})

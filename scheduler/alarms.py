"""Alarm event calculation shared by the browser fallback and the desktop (.exe) engine.

Pure schedule logic lives here so it can be tested without any UI: given a moment in
time, which break / prayer / task alarms should be ringing?
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta

from scheduler.models import (
    POMODORO_BREAK_MINUTES,
    POMODORO_WORK_MINUTES,
    AlarmSetting,
    PersonalTask,
    PrayerSchedule,
    TaskMode,
)


@dataclass(frozen=True)
class AlarmEvent:
    key: str  # unique per occurrence, used to ring only once
    kind: str  # "break" | "prayer" | "task"
    phase: str  # "start" | "heads_up"
    title: str
    message: str
    at: datetime

    def as_dict(self) -> dict[str, str]:
        d = asdict(self)
        d["at"] = self.at.isoformat()
        return d


def _events(kind: str, ident: str, day: date, name: str, start, lead: int, label: str) -> list[AlarmEvent]:
    at = datetime.combine(day, start)
    out = [
        AlarmEvent(f"{kind}:{ident}:{day}:start", kind, "start", f"{label} time", f"{name} is starting now", at),
    ]
    if lead > 0:
        out.append(
            AlarmEvent(
                f"{kind}:{ident}:{day}:lead",
                kind,
                "heads_up",
                f"{label} in {lead} min",
                f"{name} starts at {start.strftime('%H:%M')}",
                at - timedelta(minutes=lead),
            )
        )
    return out


def pomodoro_events(task: PersonalTask, day: date, lead: int) -> list[AlarmEvent]:
    """Break alarms inside a focus task: 50 min of work, then a 10 min break, repeating until the task ends."""
    start = datetime.combine(day, task.start_time)
    end = datetime.combine(day, task.end_time)
    out: list[AlarmEvent] = []
    k = 0
    while True:
        break_start = start + timedelta(minutes=POMODORO_WORK_MINUTES + k * (POMODORO_WORK_MINUTES + POMODORO_BREAK_MINUTES))
        if break_start >= end:
            break
        k += 1
        out += _events(
            "break", f"{task.pk}-{k}", day, f"{POMODORO_BREAK_MINUTES}-minute break ({task.title})",
            break_start.time(), lead, "Break",
        )
    return out


def events_for_day(day: date, cfg: AlarmSetting | None = None) -> list[AlarmEvent]:
    """All alarm events for ``day``, sorted by time. Prayers recur daily."""
    cfg = cfg or AlarmSetting.get()
    if not cfg.enabled:
        return []
    events: list[AlarmEvent] = []

    if cfg.prayer_alarm:
        for prayer in PrayerSchedule.objects.all():
            events += _events(
                "prayer", prayer.prayer_name, day, prayer.get_prayer_name_display(), prayer.start_time,
                cfg.prayer_lead_minutes, "Prayer",
            )

    if cfg.break_alarm or cfg.task_alarm:
        for task in PersonalTask.objects.filter(date=day, is_completed=False):
            if task.is_break and cfg.break_alarm:
                events += _events(
                    "break", str(task.pk), day, task.title.replace("🔔", "").strip() or "Break", task.start_time,
                    cfg.break_lead_minutes, "Break",
                )
            elif not task.is_break and task.task_type == TaskMode.FOCUS and cfg.break_alarm:
                events += pomodoro_events(task, day, cfg.break_lead_minutes)
                if cfg.task_alarm:
                    events += _events("task", str(task.pk), day, task.title, task.start_time, 0, "Task")
            elif not task.is_break and cfg.task_alarm:
                events += _events("task", str(task.pk), day, task.title, task.start_time, 0, "Task")

    return sorted(events, key=lambda e: e.at)


def due_events(now: datetime, cfg: AlarmSetting | None = None, grace_seconds: int = 90) -> list[AlarmEvent]:
    """Events whose time has arrived within the last ``grace_seconds`` (so a just-started app still rings)."""
    window_start = now - timedelta(seconds=grace_seconds)
    return [e for e in events_for_day(now.date(), cfg) if window_start <= e.at <= now]

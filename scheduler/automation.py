"""Things the app does for you so you don't have to click: recurring tasks, quick-add,
free-slot finding, carry-over of unfinished work and auto-"missed" prayers.

Every function here is idempotent (safe to call repeatedly), because the desktop engine calls
``run_daily_automation`` on a timer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from django.utils import timezone

from scheduler.forms import PersonalTaskForm
from scheduler.models import (
    PersonalTask,
    PrayerCompletion,
    PrayerCompletionStatus,
    PrayerSchedule,
    RecurringTask,
    SubTask,
    TaskCategory,
    TaskMode,
)
from scheduler.planning import auto_insert_breaks, focus_slots_left, overlaps, prayer_conflict

DAY_START = time(6, 0)
DAY_END = time(22, 0)
STEP_MINUTES = 5


# --- free slots -------------------------------------------------------------------------------
def _busy_intervals(day: date) -> list[tuple[time, time]]:
    busy = [(t.start_time, t.end_time) for t in PersonalTask.objects.filter(date=day)]
    busy += [(p.start_time, p.end_time) for p in PrayerSchedule.objects.all()]
    return busy


def find_free_slot(
    day: date, minutes: int, earliest: time = DAY_START, latest: time = DAY_END
) -> tuple[time, time] | None:
    """First [start, end) of ``minutes`` that avoids every task and every prayer window."""
    busy = _busy_intervals(day)
    cursor = datetime.combine(day, earliest)
    limit = datetime.combine(day, latest)
    while cursor + timedelta(minutes=minutes) <= limit:
        start, end = cursor.time(), (cursor + timedelta(minutes=minutes)).time()
        if not any(overlaps(start, end, b0, b1) for b0, b1 in busy):
            return start, end
        cursor += timedelta(minutes=STEP_MINUTES)
    return None


# --- quick add --------------------------------------------------------------------------------
_TIME_RE = re.compile(r"\b(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b|\b(?:at\s+)?(\d{1,2}):(\d{2})\b", re.I)
_DUR_RE = re.compile(r"\b(?:for\s+)?(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|minutes?|mins?|m)\b", re.I)


@dataclass
class ParsedTask:
    title: str
    start: time | None
    minutes: int
    task_type: str | None = None
    category: str | None = None


def parse_quick_add(text: str) -> ParsedTask:
    """'Study maths 4pm 1h #focus' -> title='Study maths', start=16:00, minutes=60, task_type='focus'."""
    rest = text.strip()
    task_type = category = None
    for tag, mode in (("#focus", TaskMode.FOCUS), ("#multi", TaskMode.MULTI)):
        if tag in rest.lower():
            task_type = mode
            rest = re.sub(tag, "", rest, flags=re.I)
    if "!" in rest:
        category = TaskCategory.NON_NEGOTIABLE
        rest = rest.replace("!", "")

    start = None
    m = _TIME_RE.search(rest)
    if m:
        if m.group(1):
            hour, minute, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3).lower()
            hour = hour % 12 + (12 if ap == "pm" else 0)
        else:
            hour, minute = int(m.group(4)), int(m.group(5))
        if 0 <= hour < 24 and 0 <= minute < 60:
            start = time(hour, minute)
            rest = rest[: m.start()] + " " + rest[m.end():]

    minutes = 60
    d = _DUR_RE.search(rest)
    if d:
        value = float(d.group(1))
        minutes = int(round(value * 60)) if d.group(2).lower().startswith("h") else int(round(value))
        rest = rest[: d.start()] + " " + rest[d.end():]

    title = re.sub(r"\s+", " ", rest).strip(" -,")
    return ParsedTask(title=title, start=start, minutes=max(5, minutes), task_type=task_type, category=category)


def quick_add(text: str, day: date, default_type: str = TaskMode.MULTI):
    """Create a task from one line of text. Returns (task | None, error | None). Uses the real form rules."""
    parsed = parse_quick_add(text)
    if not parsed.title:
        return None, "Please include a task name."
    if parsed.start:
        start = parsed.start
        end = (datetime.combine(day, start) + timedelta(minutes=parsed.minutes)).time()
        if end <= start:
            return None, "That would run past midnight."
    else:
        now = timezone.now()
        earliest = DAY_START
        if day == now.date():
            earliest = max(DAY_START, (now + timedelta(minutes=5)).time().replace(second=0, microsecond=0))
        slot = find_free_slot(day, parsed.minutes, earliest)
        if not slot:
            return None, "No free slot left that day (prayer times and tasks fill it)."
        start, end = slot

    form = PersonalTaskForm(
        {
            "title": parsed.title,
            "date": day.isoformat(),
            "start_time": start.strftime("%H:%M"),
            "end_time": end.strftime("%H:%M"),
            "category": parsed.category or TaskCategory.SECONDARY,
            "task_type": parsed.task_type or default_type,
        }
    )
    if not form.is_valid():
        return None, " ".join(e for errs in form.errors.values() for e in errs)
    task = form.save()
    auto_insert_breaks(task)
    return task, None


# --- recurring --------------------------------------------------------------------------------
@dataclass
class GenerationReport:
    created: list[PersonalTask] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def generate_recurring(day: date) -> GenerationReport:
    """Create today's tasks from active recurring templates (once each)."""
    report = GenerationReport()
    for rt in RecurringTask.objects.filter(is_active=True):
        if not rt.runs_on(day):
            continue
        if PersonalTask.objects.filter(date=day, recurring_source=rt).exists():
            continue
        conflict = prayer_conflict(rt.start_time, rt.end_time)
        if conflict:
            report.skipped.append(f"{rt.title}: overlaps {conflict.get_prayer_name_display()}")
            continue
        if rt.task_type == TaskMode.FOCUS and focus_slots_left(day) == 0:
            report.skipped.append(f"{rt.title}: focus limit reached")
            continue
        task = PersonalTask.objects.create(
            title=rt.title,
            description=rt.description,
            date=day,
            start_time=rt.start_time,
            end_time=rt.end_time,
            category=rt.category,
            task_type=rt.task_type,
            recurring_source=rt,
        )
        auto_insert_breaks(task)
        report.created.append(task)
    return report


# --- carry-over -------------------------------------------------------------------------------
def carry_over_incomplete(from_day: date, to_day: date) -> GenerationReport:
    """Re-schedule unfinished tasks from ``from_day`` into the first free slots of ``to_day``."""
    report = GenerationReport()
    now = timezone.now()
    earliest = DAY_START
    if to_day == now.date():
        earliest = max(DAY_START, (now + timedelta(minutes=5)).time().replace(second=0, microsecond=0))

    for old in PersonalTask.objects.filter(date=from_day, is_completed=False, is_break=False):
        if PersonalTask.objects.filter(date=to_day, title=old.title, is_break=False).exists():
            continue  # already carried over / already planned
        minutes = int((datetime.combine(from_day, old.end_time) - datetime.combine(from_day, old.start_time)).total_seconds() // 60)
        task_type = old.task_type
        if task_type == TaskMode.FOCUS and focus_slots_left(to_day) == 0:
            task_type = TaskMode.MULTI  # keep the work, but don't break the two-focus-task rule
        slot = find_free_slot(to_day, minutes, earliest)
        if not slot:
            report.skipped.append(f"{old.title}: no free slot")
            continue
        new = PersonalTask.objects.create(
            title=old.title, description=old.description, date=to_day, start_time=slot[0], end_time=slot[1],
            category=old.category, task_type=task_type,
        )
        for st in old.subtasks.filter(is_completed=False):
            SubTask.objects.create(personal_task=new, title=st.title, order=st.order)
        auto_insert_breaks(new)
        report.created.append(new)
    return report


# --- prayers ----------------------------------------------------------------------------------
def mark_missed_prayers(now: datetime) -> int:
    """Prayers whose window has ended and weren't marked prayed become 'missed'. Returns how many changed."""
    changed = 0
    today = now.date()
    for day in (today - timedelta(days=1), today):
        for prayer in PrayerSchedule.objects.all():
            window_over = day < today or prayer.end_time <= now.time()
            if not window_over:
                continue
            rec, _created = PrayerCompletion.objects.get_or_create(
                prayer_name=prayer.prayer_name, date=day, defaults={"status": PrayerCompletionStatus.MISSED}
            )
            if not rec.is_completed and rec.status == PrayerCompletionStatus.NOT_YET:
                rec.status = PrayerCompletionStatus.MISSED
                rec.save(update_fields=["status", "updated_at"])
                changed += 1
            elif _created:
                changed += 1
    return changed


def run_daily_automation(now: datetime | None = None) -> dict[str, int]:
    """Everything that should happen on its own. Safe to call every minute."""
    now = now or datetime.now()
    report = generate_recurring(now.date())
    return {"recurring_created": len(report.created), "prayers_missed": mark_missed_prayers(now)}

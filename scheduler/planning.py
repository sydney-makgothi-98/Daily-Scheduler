"""Scheduling rules shared by forms, views and (later) the auto-planner.

Prayer windows are fixed in both Multi and Focus mode: nothing may be placed over them.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from scheduler.models import FOCUS_MAX_PER_DAY, PersonalTask, PrayerSchedule, TaskCategory, TaskMode


def overlaps(a_start: time, a_end: time, b_start: time, b_end: time) -> bool:
    return a_start < b_end and a_end > b_start


def prayer_conflict(start: time, end: time) -> PrayerSchedule | None:
    """The first prayer window that overlaps [start, end), or None."""
    for prayer in PrayerSchedule.objects.all():
        if overlaps(start, end, prayer.start_time, prayer.end_time):
            return prayer
    return None


def focus_task_count(day: date, exclude_pk: int | None = None) -> int:
    qs = PersonalTask.objects.filter(date=day, task_type=TaskMode.FOCUS, is_break=False)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs.count()


def focus_slots_left(day: date) -> int:
    return max(0, FOCUS_MAX_PER_DAY - focus_task_count(day))


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

        # Prayer time is fixed: if the break would run into a prayer, start it after the prayer instead.
        prayer = prayer_conflict(break_start, break_end_time)
        if prayer:
            break_start = prayer.end_time
            break_end_time = (datetime.combine(task.date, break_start) + timedelta(minutes=10)).time()
            if break_end_time <= break_start:  # crossed midnight
                return

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

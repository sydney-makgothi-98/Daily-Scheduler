from datetime import date, datetime, time

from django.test import TestCase
from django.urls import reverse

from scheduler.alarms import due_events, events_for_day
from scheduler.models import AlarmSetting, PersonalTask, PrayerSchedule, TaskCategory

DAY = date(2026, 11, 9)


def make_break(start: time, end: time, **kw) -> PersonalTask:
    return PersonalTask.objects.create(
        title="🔔 Break", date=DAY, start_time=start, end_time=end, category=TaskCategory.FUN, is_break=True, **kw
    )


class AlarmEventsTest(TestCase):
    def test_break_start_and_heads_up(self):
        make_break(time(10, 0), time(10, 10))
        keys = {e.phase: e for e in events_for_day(DAY)}
        self.assertEqual(keys["start"].at, datetime(2026, 11, 9, 10, 0))
        self.assertEqual(keys["heads_up"].at, datetime(2026, 11, 9, 9, 58))  # default lead = 2 min

    def test_prayer_events_use_prayer_lead(self):
        PrayerSchedule.objects.create(prayer_name="fajr", start_time=time(5, 0), end_time=time(6, 0))
        evs = {e.phase: e for e in events_for_day(DAY)}
        self.assertEqual(evs["heads_up"].at, datetime(2026, 11, 9, 4, 55))
        self.assertEqual(evs["start"].kind, "prayer")

    def test_disabled_and_toggles(self):
        make_break(time(10, 0), time(10, 10))
        cfg = AlarmSetting.get()
        cfg.break_alarm = False
        cfg.save()
        self.assertEqual(events_for_day(DAY), [])
        cfg.break_alarm, cfg.enabled = True, False
        cfg.save()
        self.assertEqual(events_for_day(DAY), [])

    def test_completed_break_and_regular_tasks_do_not_ring(self):
        make_break(time(10, 0), time(10, 10), is_completed=True)
        PersonalTask.objects.create(title="Work", date=DAY, start_time=time(9), end_time=time(10))
        self.assertEqual(events_for_day(DAY), [])

    def test_task_alarm_opt_in(self):
        PersonalTask.objects.create(title="Work", date=DAY, start_time=time(9), end_time=time(10))
        cfg = AlarmSetting.get()
        cfg.task_alarm = True
        cfg.save()
        self.assertEqual([e.kind for e in events_for_day(DAY)], ["task"])

    def test_due_window(self):
        make_break(time(10, 0), time(10, 10))
        self.assertEqual([e.phase for e in due_events(datetime(2026, 11, 9, 10, 0, 30))], ["start"])
        self.assertEqual(due_events(datetime(2026, 11, 9, 10, 5)), [])  # too late (past grace)
        self.assertEqual([e.phase for e in due_events(datetime(2026, 11, 9, 9, 58, 10))], ["heads_up"])


class AlarmApiTest(TestCase):
    def test_today_api_and_settings_form(self):
        res = self.client.get(reverse("alarms_today_api"))
        self.assertEqual(res.status_code, 200)
        self.assertIn("events", res.json())

        res = self.client.post(reverse("alarm_settings"), {"break_alarm": "on", "snooze_minutes": "999", "volume": "50"})
        self.assertEqual(res.status_code, 302)
        cfg = AlarmSetting.get()
        self.assertEqual(cfg.snooze_minutes, 60)  # clamped
        self.assertEqual(cfg.volume, 50)
        self.assertFalse(cfg.prayer_alarm)  # unchecked boxes are off

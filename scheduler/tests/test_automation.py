from datetime import datetime, time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from scheduler.automation import (
    carry_over_incomplete,
    find_free_slot,
    generate_recurring,
    mark_missed_prayers,
    parse_quick_add,
    quick_add,
)
from scheduler.models import (
    PersonalTask,
    PrayerCompletion,
    PrayerCompletionStatus,
    PrayerSchedule,
    RecurringTask,
    TaskMode,
)

TODAY = timezone.now().date()
TOMORROW = TODAY + timedelta(days=1)


class ParseTest(TestCase):
    def test_full_line(self):
        p = parse_quick_add("Study maths 4pm 1h #focus")
        self.assertEqual((p.title, p.start, p.minutes, p.task_type), ("Study maths", time(16), 60, TaskMode.FOCUS))

    def test_24h_time_and_minutes(self):
        p = parse_quick_add("Call mum at 18:30 for 45 min")
        self.assertEqual((p.title, p.start, p.minutes), ("Call mum", time(18, 30), 45))

    def test_no_time_means_free_slot_and_numbers_in_title_survive(self):
        p = parse_quick_add("Read chapter 3")
        self.assertEqual((p.title, p.start, p.minutes), ("Read chapter 3", None, 60))

    def test_12am_12pm(self):
        self.assertEqual(parse_quick_add("x 12pm").start, time(12))
        self.assertEqual(parse_quick_add("x 12am").start, time(0))

    def test_exclamation_is_non_negotiable(self):
        self.assertEqual(parse_quick_add("Gym! 6pm").category, "non_negotiable")


class FreeSlotTest(TestCase):
    def test_skips_tasks_and_prayers(self):
        PrayerSchedule.objects.create(prayer_name="fajr", start_time=time(6), end_time=time(6, 30))
        PersonalTask.objects.create(title="a", date=TOMORROW, start_time=time(6, 30), end_time=time(8))
        self.assertEqual(find_free_slot(TOMORROW, 60), (time(8), time(9)))

    def test_none_when_full(self):
        PersonalTask.objects.create(title="a", date=TOMORROW, start_time=time(6), end_time=time(22))
        self.assertIsNone(find_free_slot(TOMORROW, 30))


class QuickAddTest(TestCase):
    def test_creates_with_form_rules(self):
        task, err = quick_add("Write 10am 2h", TOMORROW)
        self.assertIsNone(err)
        self.assertEqual((task.start_time, task.end_time), (time(10), time(12)))
        self.assertTrue(PersonalTask.objects.filter(is_break=True, parent_task=task).exists())  # auto break

    def test_rejects_prayer_overlap(self):
        PrayerSchedule.objects.create(prayer_name="zhor", start_time=time(13), end_time=time(13, 30))
        task, err = quick_add("Lunch 1pm 1h", TOMORROW)
        self.assertIsNone(task)
        self.assertIn("Zhor", err)

    def test_api(self):
        url = reverse("quick_add_api", args=[TOMORROW.year, TOMORROW.month, TOMORROW.day])
        ok = self.client.post(url, '{"text": "Plan 9am 30m"}', content_type="application/json")
        self.assertEqual(ok.status_code, 200)
        bad = self.client.post(url, '{"text": ""}', content_type="application/json")
        self.assertEqual(bad.status_code, 400)


class RecurringTest(TestCase):
    def make(self, **kw):
        defaults = dict(title="Gym", weekdays=str(TOMORROW.weekday()), start_time=time(17), end_time=time(18))
        defaults.update(kw)
        return RecurringTask.objects.create(**defaults)

    def test_generates_once(self):
        self.make()
        self.assertEqual(len(generate_recurring(TOMORROW).created), 1)
        self.assertEqual(len(generate_recurring(TOMORROW).created), 0)  # idempotent
        self.assertEqual(PersonalTask.objects.filter(date=TOMORROW, is_break=False).count(), 1)

    def test_wrong_weekday_and_paused(self):
        self.make(weekdays=str((TOMORROW.weekday() + 1) % 7))
        self.make(title="Paused", is_active=False)
        self.assertEqual(generate_recurring(TOMORROW).created, [])

    def test_prayer_clash_is_skipped_not_overwritten(self):
        PrayerSchedule.objects.create(prayer_name="asr", start_time=time(17, 30), end_time=time(18))
        self.make()
        report = generate_recurring(TOMORROW)
        self.assertEqual(report.created, [])
        self.assertIn("Asr", report.skipped[0])

    def test_focus_limit_respected(self):
        for i in range(2):
            PersonalTask.objects.create(
                title=f"f{i}", date=TOMORROW, start_time=time(8 + i), end_time=time(9 + i), task_type=TaskMode.FOCUS
            )
        self.make(task_type=TaskMode.FOCUS)
        self.assertIn("focus limit", generate_recurring(TOMORROW).skipped[0])


class CarryOverTest(TestCase):
    def test_moves_only_unfinished_and_does_not_duplicate(self):
        y = TODAY
        PersonalTask.objects.create(title="done", date=y, start_time=time(9), end_time=time(10), is_completed=True)
        PersonalTask.objects.create(title="todo", date=y, start_time=time(9), end_time=time(10))
        r = carry_over_incomplete(y, TOMORROW)
        self.assertEqual([t.title for t in r.created], ["todo"])
        self.assertEqual(carry_over_incomplete(y, TOMORROW).created, [])


class MissedPrayerTest(TestCase):
    def test_marks_ended_unprayed_only(self):
        PrayerSchedule.objects.create(prayer_name="fajr", start_time=time(5), end_time=time(6))
        PrayerSchedule.objects.create(prayer_name="zhor", start_time=time(13), end_time=time(15))
        PrayerCompletion.objects.create(
            prayer_name="fajr", date=TODAY, is_completed=True, status=PrayerCompletionStatus.PRAYED
        )
        mark_missed_prayers(datetime.combine(TODAY, time(14)))
        self.assertEqual(PrayerCompletion.objects.get(prayer_name="fajr", date=TODAY).status, "prayed")
        self.assertFalse(PrayerCompletion.objects.filter(prayer_name="zhor", date=TODAY).exists())  # still open
        # yesterday's unprayed fajr is missed
        self.assertEqual(
            PrayerCompletion.objects.get(prayer_name="fajr", date=TODAY - timedelta(days=1)).status, "missed"
        )


class PagesRenderTest(TestCase):
    def test_new_and_changed_pages(self):
        RecurringTask.objects.create(title="Gym", weekdays="0,2", start_time=time(17), end_time=time(18))
        for name, args in (
            ("recurring_list", []),
            ("home", []),
            ("calendar_view", []),
            ("alarm_settings", []),
        ):
            res = self.client.get(reverse(name, args=args))
            self.assertEqual(res.status_code, 200, name)
        home = self.client.get(reverse("home")).content.decode()
        self.assertIn("app/vendor/three.min.js", home)

    def test_recurring_create_and_delete(self):
        res = self.client.post(
            reverse("recurring_list"),
            {"title": "Read", "weekdays": ["0", "1"], "start_time": "07:00", "end_time": "07:30"},
        )
        self.assertEqual(res.status_code, 302)
        rt = RecurringTask.objects.get()
        self.assertEqual(rt.weekdays, "0,1")
        self.client.post(reverse("recurring_toggle", args=[rt.pk]))
        rt.refresh_from_db()
        self.assertFalse(rt.is_active)
        self.client.post(reverse("recurring_delete", args=[rt.pk]))
        self.assertEqual(RecurringTask.objects.count(), 0)

    def test_recurring_requires_valid_input(self):
        self.client.post(reverse("recurring_list"), {"title": "x", "start_time": "09:00", "end_time": "08:00"})
        self.assertEqual(RecurringTask.objects.count(), 0)

from datetime import datetime, time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from scheduler.alarms import events_for_day
from scheduler.forms import PersonalTaskForm
from scheduler.models import DayPlan, PersonalTask, PrayerSchedule, TaskCategory, TaskMode

TOMORROW = timezone.now().date() + timedelta(days=1)


def form_data(**over):
    data = {
        "title": "Write",
        "date": TOMORROW.isoformat(),
        "start_time": "09:00",
        "end_time": "10:00",
        "category": TaskCategory.SECONDARY,
        "task_type": TaskMode.FOCUS,
    }
    data.update(over)
    return data


def make(title, start, end, task_type=TaskMode.FOCUS, **kw):
    return PersonalTask.objects.create(
        title=title, date=TOMORROW, start_time=start, end_time=end, task_type=task_type, **kw
    )


class FocusLimitTest(TestCase):
    def test_third_focus_task_rejected_but_multi_allowed(self):
        make("a", time(8), time(9))
        make("b", time(10), time(11))
        bad = PersonalTaskForm(form_data(start_time="12:00", end_time="13:00"))
        self.assertFalse(bad.is_valid())
        self.assertIn("at most 2 focus", str(bad.errors))
        ok = PersonalTaskForm(form_data(start_time="12:00", end_time="13:00", task_type=TaskMode.MULTI))
        self.assertTrue(ok.is_valid(), ok.errors)

    def test_editing_an_existing_focus_task_is_not_blocked(self):
        make("a", time(8), time(9))
        t = make("b", time(10), time(11))
        form = PersonalTaskForm(form_data(start_time="10:00", end_time="11:30"), instance=t)
        self.assertTrue(form.is_valid(), form.errors)

    def test_breaks_do_not_count(self):
        make("a", time(8), time(9))
        make("brk", time(9), time(9, 10), is_break=True)
        self.assertTrue(PersonalTaskForm(form_data(start_time="12:00", end_time="13:00")).is_valid())


class PrayerProtectionTest(TestCase):
    def setUp(self):
        PrayerSchedule.objects.create(prayer_name="zhor", start_time=time(13), end_time=time(13, 30))

    def test_overlap_rejected_in_both_modes(self):
        for mode in (TaskMode.MULTI, TaskMode.FOCUS):
            form = PersonalTaskForm(form_data(start_time="12:30", end_time="14:00", task_type=mode))
            self.assertFalse(form.is_valid())
            self.assertIn("Zhor", str(form.errors))

    def test_touching_a_prayer_is_fine(self):
        self.assertTrue(PersonalTaskForm(form_data(start_time="12:00", end_time="13:00")).is_valid())


class PomodoroAlarmTest(TestCase):
    def test_focus_task_gets_a_break_alarm_every_60_minutes(self):
        make("deep", time(9), time(12))  # 3h: work 9:00-9:50, break 9:50; 10:50; 11:50
        starts = [e.at.time() for e in events_for_day(TOMORROW) if e.phase == "start" and e.kind == "break"]
        self.assertEqual(starts, [time(9, 50), time(10, 50), time(11, 50)])

    def test_no_break_alarm_if_task_ends_before_first_break(self):
        make("short", time(9), time(9, 40))
        self.assertEqual([e for e in events_for_day(TOMORROW) if e.kind == "break"], [])


class DayTypeTest(TestCase):
    def test_default_and_set(self):
        self.assertEqual(DayPlan.type_for(TOMORROW), TaskMode.MULTI)
        url = reverse("set_day_type", args=[TOMORROW.year, TOMORROW.month, TOMORROW.day])
        res = self.client.post(url, '{"day_type": "focus"}', content_type="application/json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(DayPlan.type_for(TOMORROW), TaskMode.FOCUS)
        bad = self.client.post(url, '{"day_type": "nope"}', content_type="application/json")
        self.assertEqual(bad.status_code, 400)

    def test_pages_render(self):
        make("a", time(8), time(9))
        for name in ("home", "focus_today"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        d = TOMORROW
        self.assertEqual(self.client.get(reverse("focus_day", args=[d.year, d.month, d.day])).status_code, 200)
        self.assertEqual(self.client.get(reverse("task_data_view", args=[d.year, d.month, d.day])).status_code, 200)
        self.assertEqual(self.client.get(reverse("create_personal_task", args=[d.year, d.month, d.day])).status_code, 200)

    def test_new_task_defaults_to_the_days_type(self):
        DayPlan.objects.create(date=TOMORROW, day_type=TaskMode.FOCUS)
        res = self.client.get(reverse("create_personal_task", args=[TOMORROW.year, TOMORROW.month, TOMORROW.day]))
        self.assertEqual(res.context["form"].initial["task_type"], TaskMode.FOCUS)


class ProjectGenerationPrayerTest(TestCase):
    def test_generate_schedule_skips_prayer_windows(self):
        import json

        from scheduler.models import Project, ProjectSchedule, ProjectTask

        PrayerSchedule.objects.create(prayer_name="zhor", start_time=time(13), end_time=time(13, 30))
        start = TOMORROW
        project = Project.objects.create(title="P", start_date=start, end_date=start + timedelta(days=6))
        task = ProjectTask.objects.create(project=project, title="T", duration_hours=1)
        ProjectSchedule.objects.create(project_task=task, day_of_week=start.weekday(), start_time=time(13), duration_hours=1)
        res = self.client.post(
            reverse("generate_schedule", args=[project.id]),
            json.dumps({"task_ids": [task.id]}),
            content_type="application/json",
        )
        body = res.json()
        self.assertEqual(body["created"], 0)
        self.assertIn("Zhor", body["conflicts"][0]["reason"])

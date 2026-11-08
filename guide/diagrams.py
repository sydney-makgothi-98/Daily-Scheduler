"""Diagrams for the guide, drawn with reportlab graphics (no image files). get(name, width) -> Drawing."""

from __future__ import annotations

import math

from reportlab.graphics.shapes import Drawing, Group, Line, Polygon, Rect, String
from reportlab.lib import colors

W = 520  # design width; get() scales to the page
PALETTE = {
    "violet": ("#ede9fe", "#6d28d9"),
    "blue": ("#dbeafe", "#2563eb"),
    "green": ("#dcfce7", "#16a34a"),
    "amber": ("#fef3c7", "#d97706"),
    "red": ("#fee2e2", "#dc2626"),
    "grey": ("#f1f5f9", "#64748b"),
}


class Canvas:
    def __init__(self, height: int, title: str | None = None):
        self.d = Drawing(W, height)
        self.h = height
        if title:
            self.d.add(String(W / 2, height - 14, title, fontName="Body-Bold", fontSize=11, textAnchor="middle",
                              fillColor=colors.HexColor("#1e293b")))

    def box(self, x, y, w, h, text, color="violet", size=8.5, sub=None):
        fill, edge = PALETTE[color]
        self.d.add(Rect(x, y, w, h, rx=6, ry=6, fillColor=colors.HexColor(fill), strokeColor=colors.HexColor(edge), strokeWidth=1.2))
        lines = text.split("\n")
        total = len(lines) * (size + 2) + (size if sub else 0)
        ty = y + h / 2 + total / 2 - size
        for ln in lines:
            self.d.add(String(x + w / 2, ty, ln, fontName="Body-Bold", fontSize=size, textAnchor="middle", fillColor=colors.HexColor("#1e293b")))
            ty -= size + 2
        if sub:
            self.d.add(String(x + w / 2, ty - 1, sub, fontName="Body", fontSize=size - 1.5, textAnchor="middle", fillColor=colors.HexColor("#475569")))

    def label(self, x, y, text, size=7.5, anchor="middle", color="#475569", bold=False):
        self.d.add(String(x, y, text, fontName="Body-Bold" if bold else "Body", fontSize=size, textAnchor=anchor, fillColor=colors.HexColor(color)))

    def arrow(self, x1, y1, x2, y2, text=None, color="#475569", dashed=False):
        ln = Line(x1, y1, x2, y2, strokeColor=colors.HexColor(color), strokeWidth=1.3)
        if dashed:
            ln.strokeDashArray = [3, 2]
        self.d.add(ln)
        ang = math.atan2(y2 - y1, x2 - x1)
        a = 6
        p = [x2, y2, x2 - a * math.cos(ang - 0.4), y2 - a * math.sin(ang - 0.4), x2 - a * math.cos(ang + 0.4), y2 - a * math.sin(ang + 0.4)]
        self.d.add(Polygon(p, fillColor=colors.HexColor(color), strokeColor=colors.HexColor(color)))
        if text:
            self.label((x1 + x2) / 2, (y1 + y2) / 2 + 3, text)

    def done(self, width):
        scale = width / W
        g = Group(*self.d.contents)
        g.scale(scale, scale)
        out = Drawing(width, self.h * scale)
        out.add(g)
        return out


# --- individual diagrams -----------------------------------------------------------------------
def http_exchange():
    c = Canvas(190, "One HTTP request and its response")
    c.box(20, 70, 110, 70, "Browser\n(the client)", "blue")
    c.box(390, 70, 110, 70, "Django app\n(the server)", "violet")
    c.arrow(130, 125, 390, 125, "1. Request:  GET /calendar/2026/11/9/ HTTP/1.1")
    c.arrow(390, 85, 130, 85, "2. Response:  200 OK  +  HTML text")
    c.label(260, 50, "The browser asks for a URL. The server runs Python code and answers with text.", 8)
    c.label(260, 36, "Nothing is remembered between requests unless you store it (database, session, cookie).", 8)
    return c


def request_cycle():
    c = Canvas(255, "What Django does with every request")
    xs = [10, 112, 214, 316, 418]
    labels = [("Browser", "blue", "sends URL"), ("urls.py", "amber", "matches path"), ("views.py", "violet", "your logic"),
              ("models.py\n+ database", "green", "reads/writes data"), ("template\n(.html)", "red", "draws page")]
    for x, (t, col, sub) in zip(xs, labels):
        c.box(x, 140, 92, 56, t, col, sub=sub)
    for a, b in zip(xs, xs[1:]):
        c.arrow(a + 92, 168, b, 168)
    c.arrow(464, 140, 464, 110, color="#dc2626")
    c.arrow(464, 110, 56, 110, "HTML travels back to the browser as the response", color="#dc2626")
    c.arrow(56, 110, 56, 138, color="#dc2626")
    c.label(260, 85, "Middleware wraps the whole trip: sessions, CSRF protection, security headers.", 8)
    c.label(260, 70, "Example: /calendar/2026/11/9/  ->  urls.py picks task_data_view  ->  view loads tasks  ->  template.", 8)
    c.label(260, 55, "A view returns an HttpResponse. render(...) and JsonResponse(...) are shortcuts that build one.", 8)
    return c


def mtv():
    c = Canvas(210, "Django's MTV pattern (called MVC elsewhere)")
    c.box(30, 110, 140, 55, "Model", "green", sub="data + rules  (models.py)")
    c.box(190, 110, 140, 55, "View", "violet", sub="decides what to do  (views.py)")
    c.box(350, 110, 140, 55, "Template", "red", sub="how it looks  (.html)")
    c.arrow(190, 137, 170, 137)
    c.arrow(170, 150, 190, 150)
    c.arrow(330, 137, 350, 137)
    c.label(260, 85, "Other frameworks call these:   Model = Model,   View = Controller,   Template = View.", 8)
    c.label(260, 70, "Django's *View* is the traffic cop. It is not the HTML. That naming trips up almost every beginner.", 8)
    c.label(260, 45, "urls.py sits in front: it only chooses WHICH view runs.", 8)
    return c


def project_vs_app():
    c = Canvas(250, "Project vs app")
    c.box(10, 20, 500, 205, "", "grey")
    c.label(260, 210, "PROJECT  =  one website/program  (settings, root urls, wsgi)", 8.5, bold=True)
    c.box(30, 130, 200, 65, "App: scheduler", "violet", sub="models, views, forms, templates")
    c.box(290, 130, 200, 65, "App: django.contrib.admin", "blue", sub="ready-made app that ships with Django")
    c.box(30, 40, 200, 65, "App: django.contrib.auth", "blue", sub="users, groups, permissions")
    c.box(290, 40, 200, 65, "App: (your next app)", "grey", sub="e.g. notes, finance, ...")
    c.label(260, 112, "An app is a reusable folder of code that does ONE job. Apps are listed in INSTALLED_APPS.", 7.5)
    return c


def orm():
    c = Canvas(200, "The ORM: Python objects in, SQL out")
    c.box(15, 90, 200, 70, "PersonalTask.objects\n.filter(date=day, is_completed=False)", "violet", size=8)
    c.box(305, 90, 200, 70, "SELECT * FROM scheduler_personaltask\nWHERE date = '2026-11-09' AND NOT is_completed", "green", size=7)
    c.arrow(215, 125, 305, 125, "Django writes the SQL")
    c.arrow(305, 100, 215, 100, "rows -> PersonalTask objects")
    c.label(260, 55, "You never write SQL by hand for normal work. You also never have to worry about SQL injection,", 8)
    c.label(260, 41, "because values are passed as parameters, not pasted into the query text.", 8)
    return c


def migration_flow():
    c = Canvas(185, "Models -> migrations -> database")
    c.box(10, 80, 105, 60, "models.py", "violet", sub="you edit this")
    c.box(150, 80, 105, 60, "makemigrations", "amber", sub="compares to history")
    c.box(290, 80, 105, 60, "0028_....py", "blue", sub="a recipe file, in git")
    c.box(425, 80, 85, 60, "migrate", "green", sub="runs the recipe")
    c.arrow(115, 110, 150, 110); c.arrow(255, 110, 290, 110); c.arrow(395, 110, 425, 110)
    c.label(260, 50, "Migrations make database changes repeatable: your PC, a test database and the .exe's", 8)
    c.label(260, 36, "database all end up with exactly the same tables, in the same order.", 8)
    return c


def form_flow():
    c = Canvas(250, "How a Django form is processed (create_personal_task)")
    c.box(190, 195, 140, 36, "GET: show empty form", "blue")
    c.box(190, 140, 140, 36, "POST: form = Form(request.POST)", "violet", size=8)
    c.box(190, 85, 140, 36, "form.is_valid() ?", "amber")
    c.box(30, 25, 170, 40, "No: redisplay with errors\n(user keeps what they typed)", "red", size=7.5)
    c.box(320, 25, 170, 40, "Yes: form.save() then redirect\n(auto breaks, messages)", "green", size=7.5)
    c.arrow(260, 195, 260, 176); c.arrow(260, 140, 260, 121)
    c.arrow(230, 85, 120, 65); c.arrow(290, 85, 400, 65)
    c.label(110, 72, "no", 8); c.label(410, 72, "yes", 8)
    return c


def middleware():
    c = Canvas(210, "Middleware: layers around your view")
    sizes = [(20, 20, 480, 175, "Security / Common", "grey"), (60, 45, 400, 125, "Session + CSRF", "blue"),
             (100, 70, 320, 75, "Auth + Messages", "violet")]
    for x, y, w, h, t, col in sizes:
        c.box(x, y, w, h, "", col)
        c.label(x + 8, y + h - 12, t, 8, "start", bold=True)
    c.box(190, 82, 140, 38, "your view", "green")
    c.arrow(5, 100, 100, 100); c.arrow(420, 90, 505, 90)
    c.label(260, 8, "Requests pass inward through each layer; responses pass outward in reverse order.", 8)
    return c


def desktop_arch():
    c = Canvas(310, "DailySchedule.exe - one process, several jobs")
    c.box(10, 20, 500, 265, "", "grey")
    c.label(260, 270, "DailySchedule.exe  (desktop/main.py)", 9, bold=True)
    c.box(25, 190, 140, 60, "Window\n(pywebview / Edge)", "blue", sub="shows the website")
    c.box(190, 190, 140, 60, "Web server\n(waitress thread)", "violet", sub="runs Django")
    c.box(355, 190, 140, 60, "Tray icon\n(pystray)", "amber", sub="keeps app alive")
    c.box(190, 100, 140, 60, "Alarm engine\n(thread, 5 s tick)", "red", sub="rings with window closed")
    c.box(25, 100, 140, 60, "SQLite file", "green", sub="%APPDATA%\\DailySchedule")
    c.box(355, 100, 140, 60, "Windows\nsound + toast + pop-up", "blue", sub="winsound, winotify, tkinter")
    c.arrow(165, 220, 190, 220, "HTTP"); c.arrow(330, 140, 355, 130); c.arrow(260, 190, 260, 160, "events")
    c.arrow(190, 130, 165, 130, "reads")
    c.arrow(260, 190, 120, 160, color="#16a34a")
    c.label(260, 50, "Closing the window only hides it. The tray keeps the process, and so the alarm engine, running.", 8)
    c.label(260, 36, "Quit from the tray menu stops everything (and the alarms).", 8)
    return c


def alarm_flow():
    c = Canvas(245, "How an alarm happens")
    c.box(10, 150, 120, 55, "Database", "green", sub="breaks, prayers, settings")
    c.box(150, 150, 120, 55, "events_for_day()", "violet", sub="builds today's events")
    c.box(290, 150, 110, 55, "due_events(now)", "amber", sub="which are due?")
    c.box(420, 150, 90, 55, "engine.tick()", "red", sub="every 5 s")
    c.arrow(130, 177, 150, 177); c.arrow(270, 177, 290, 177); c.arrow(400, 177, 420, 177)
    c.box(40, 40, 130, 55, "sound loop", "blue"); c.box(195, 40, 130, 55, "Windows toast", "blue"); c.box(350, 40, 130, 55, "pop-up: Snooze/Dismiss", "blue", size=7.5)
    c.arrow(465, 150, 415, 95); c.arrow(465, 150, 260, 95); c.arrow(465, 150, 105, 95)
    c.label(260, 215, "Each event has a unique key, so it rings once. Snooze stores it to ring again later.", 8)
    return c


def er_diagram():
    c = Canvas(430, "Database tables of the planner (arrows = foreign keys)")
    c.box(190, 330, 140, 75, "PersonalTask", "violet", sub="title, date, start/end\ncategory, task_type, is_break")
    c.box(10, 330, 140, 60, "SubTask", "green", sub="title, is_completed, order")
    c.box(370, 330, 140, 60, "TaskCompletion", "green", sub="history of ticks")
    c.box(190, 220, 140, 55, "RecurringTask", "amber", sub="title, weekdays, times")
    c.box(10, 215, 140, 55, "DayPlan", "blue", sub="date -> multi | focus")
    c.box(370, 215, 140, 55, "AlarmSetting", "blue", sub="one row of preferences")
    c.box(10, 110, 140, 55, "PrayerSchedule", "red", sub="5 daily windows")
    c.box(190, 110, 140, 55, "PrayerCompletion", "red", sub="per prayer per day")
    c.box(370, 110, 140, 55, "Project", "violet", sub="title, start/end, status")
    c.box(370, 20, 140, 55, "ProjectTask", "violet", sub="duration, order")
    c.box(190, 20, 140, 55, "ProjectSchedule", "violet", sub="weekday, start, weeks")
    c.arrow(190, 350, 150, 350); c.arrow(370, 350, 330, 350)
    c.arrow(260, 275, 260, 330, dashed=True)
    c.arrow(430, 110, 430, 75); c.arrow(370, 47, 330, 47)
    c.arrow(190, 137, 150, 137, dashed=True)
    c.label(298, 300, "recurring_source", 7); c.label(170, 366, "personal_task", 7, "middle"); c.label(350, 366, "task", 7)
    c.label(262, 188, "PrayerSchedule/PrayerCompletion share prayer_name (no FK) and DayPlan shares date.", 7.5)
    return c


def upstream_arch():
    c = Canvas(260, "The upstream library (django-tasks-scheduler) underneath")
    c.box(10, 180, 130, 55, "Django database", "green", sub="Task rows (cron/once/repeat)")
    c.box(195, 180, 130, 55, "WorkerScheduler", "violet", sub="enqueues due tasks")
    c.box(380, 180, 130, 55, "Redis / Valkey", "red", sub="queues + job state")
    c.box(195, 60, 130, 55, "Worker(s)", "blue", sub="dequeue and run jobs")
    c.box(10, 60, 130, 55, "Admin / views", "amber", sub="monitor queues, workers")
    c.arrow(140, 207, 195, 207); c.arrow(325, 207, 380, 207); c.arrow(445, 180, 325, 100)
    c.arrow(195, 87, 140, 87); c.arrow(260, 180, 260, 115, "locks")
    c.label(260, 20, "Your planner app piggybacks on this project: it adds PersonalTask etc. next to the Task model.", 8)
    return c


def repo_map():
    c = Canvas(300, "Where things live in the repository")
    rows = [
        ("scheduler/", "the Django app: models, views, forms, templates, static, tests, migrations", "violet"),
        ("scheduler/worker, redis_models, helpers/", "upstream job engine (queues, workers, Redis)", "red"),
        ("testproject/", "minimal Django project used for development and tests", "amber"),
        ("desktop/", "the Windows program: settings, alarm engine, tray, build + installer", "green"),
        ("guide/", "this guide: chapters, diagrams, build script", "blue"),
        ("docs/, .github/", "upstream documentation and CI workflows", "grey"),
        ("pyproject.toml, uv.lock", "dependencies and tool settings", "grey"),
        ("manage_desktop.py", "manage.py for the desktop settings", "grey"),
    ]
    y = 255
    for name, desc, col in rows:
        c.box(10, y - 8, 190, 28, name, col, size=8)
        c.label(210, y + 2, desc, 8, "start")
        y -= 33
    return c


def mvt_example():
    c = Canvas(210, "Worked example: opening the Focus page")
    steps = [("1  URL", "/focus/", "amber"), ("2  urls.py", "path('focus/', views.focus_day)", "amber"),
             ("3  view", "focus_day(request)", "violet"), ("4  ORM", "PersonalTask.objects.filter(...)", "green"),
             ("5  template", "focus_day.html", "red")]
    x = 10
    for t, sub, col in steps:
        c.box(x, 105, 94, 60, t, col, size=8.5, sub=sub)
        x += 102
    for i in range(4):
        c.arrow(10 + 94 + i * 102, 135, 10 + (i + 1) * 102, 135)
    c.label(260, 70, "The template receives a context dict (tasks, prayers, slots_left ...) and fills in the HTML.", 8)
    c.label(260, 55, "The browser then runs the page's JavaScript, which draws the live 50/10 countdown.", 8)
    return c


def languages():
    c = Canvas(230, "Languages in this project and where each runs")
    c.box(10, 150, 150, 55, "Python", "violet", sub="server logic, desktop app")
    c.box(185, 150, 150, 55, "HTML + Django templates", "red", sub="structure of pages")
    c.box(360, 150, 150, 55, "CSS", "blue", sub="looks, 3D tilt, dark theme")
    c.box(10, 70, 150, 55, "JavaScript", "amber", sub="timers, fetch(), Three.js")
    c.box(185, 70, 150, 55, "SQL (via the ORM)", "green", sub="queries Django writes for you")
    c.box(360, 70, 150, 55, "PowerShell / TOML / Markdown", "grey", sub="installer, config, docs", size=7.5)
    c.label(260, 30, "Python runs on the server (inside the .exe). HTML/CSS/JS run in the browser window.", 8)
    return c


BUILDERS = {f.__name__: f for f in (
    http_exchange, request_cycle, mtv, project_vs_app, orm, migration_flow, form_flow, middleware, desktop_arch,
    alarm_flow, er_diagram, upstream_arch, repo_map, mvt_example, languages,
)}


def get(name: str, width: float) -> Drawing:
    return BUILDERS[name]().done(width)

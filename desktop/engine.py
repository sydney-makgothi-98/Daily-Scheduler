"""Background alarm engine for the desktop app.

Runs in the .exe process (not in the web page), so alarms ring with the window closed:
looping sound + Windows toast + an always-on-top alarm window with Snooze / Dismiss.
"""

from __future__ import annotations

import io
import logging
import math
import struct
import threading
import wave
from datetime import datetime, timedelta

from scheduler.alarms import AlarmEvent, due_events
from scheduler.models import AlarmSetting

log = logging.getLogger("desktop.alarm")
APP_ID = "Daily Schedule"
POLL_SECONDS = 5

try:  # Windows only
    import winsound
except ImportError:  # pragma: no cover
    winsound = None

try:
    from winotify import Notification, audio
except ImportError:  # pragma: no cover
    Notification = None


def build_alarm_wav(volume_pct: int) -> bytes:
    """A short 'beep-beep-beep-beep ... pause' pattern as WAV bytes, scaled by ``volume_pct``."""
    rate = 22050
    amp = int(32767 * 0.6 * max(0, min(100, volume_pct)) / 100)
    frames = bytearray()
    for freq in (880, 1100, 880, 1100):
        for n in range(int(rate * 0.16)):
            frames += struct.pack("<h", int(amp * math.sin(2 * math.pi * freq * n / rate)))
        frames += b"\x00\x00" * int(rate * 0.06)
    frames += b"\x00\x00" * int(rate * 0.6)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
    return buf.getvalue()


def start_sound(volume_pct: int, loop: bool) -> None:
    if winsound is None:
        return
    flags = winsound.SND_MEMORY | winsound.SND_ASYNC | (winsound.SND_LOOP if loop else 0)
    winsound.PlaySound(build_alarm_wav(volume_pct), flags)


def stop_sound() -> None:
    if winsound is not None:
        winsound.PlaySound(None, winsound.SND_PURGE)


def toast(event: AlarmEvent) -> None:
    if Notification is None:
        return
    try:
        n = Notification(app_id=APP_ID, title=event.title, msg=event.message, duration="long")
        n.set_audio(audio.Default, loop=False)
        n.show()
    except Exception:
        log.exception("toast failed")


def mark_prayed(event: AlarmEvent) -> None:
    from django.utils import timezone

    from scheduler.models import PrayerCompletion, PrayerCompletionStatus

    name = event.key.split(":")[1]
    PrayerCompletion.objects.update_or_create(
        prayer_name=name,
        date=event.at.date(),
        defaults={
            "is_completed": True,
            "status": PrayerCompletionStatus.PRAYED,
            "completed_at": timezone.now(),
        },
    )


class AlarmEngine(threading.Thread):
    def __init__(self) -> None:
        super().__init__(daemon=True, name="alarm-engine")
        self._stop_evt = threading.Event()
        self._fired: set[str] = set()
        self._snoozed: list[tuple[datetime, AlarmEvent]] = []
        self._ringing: AlarmEvent | None = None
        self._last_auto: datetime | None = None
        self._lock = threading.Lock()
        self.muted = False

    # --- control ---------------------------------------------------------------------------
    def stop(self) -> None:
        self._stop_evt.set()
        stop_sound()

    def snooze(self, event: AlarmEvent, minutes: int) -> None:
        with self._lock:
            self._snoozed.append((datetime.now() + timedelta(minutes=minutes), event))

    # --- loop ------------------------------------------------------------------------------
    def run(self) -> None:
        while not self._stop_evt.wait(POLL_SECONDS):
            try:
                self.tick(datetime.now())
            except Exception:
                log.exception("alarm tick failed")

    def tick(self, now: datetime) -> list[AlarmEvent]:
        """Fire everything due at ``now``. Returns the events fired (handy for tests)."""
        fired_now: list[AlarmEvent] = []
        self._automate(now)
        cfg = AlarmSetting.get()
        if self.muted or not cfg.enabled:
            return fired_now

        candidates = [e for e in due_events(now, cfg) if e.key not in self._fired]
        with self._lock:
            ready = [e for t, e in self._snoozed if t <= now]
            self._snoozed = [(t, e) for t, e in self._snoozed if t > now]
        for e in candidates:
            self._fired.add(e.key)
        for e in candidates + ready:
            fired_now.append(e)
            self.ring(e, cfg)
        return fired_now

    def _automate(self, now: datetime) -> None:
        """Recurring tasks + auto-missed prayers, at most once a minute."""
        if self._last_auto and (now - self._last_auto).total_seconds() < 60:
            return
        self._last_auto = now
        try:
            from scheduler.automation import run_daily_automation

            run_daily_automation(now)
        except Exception:
            log.exception("daily automation failed")

    def ring(self, event: AlarmEvent, cfg: AlarmSetting) -> None:
        toast(event)
        if event.phase == "heads_up":
            start_sound(cfg.volume, loop=False)  # a short nudge, no blocking window
            return
        # A prayer that is already ringing is not interrupted by a break/task alarm.
        if self._ringing and self._ringing.kind == "prayer" and event.kind != "prayer":
            return
        threading.Thread(target=self._show_window, args=(event, cfg), daemon=True).start()

    # --- alarm window ----------------------------------------------------------------------
    def _show_window(self, event: AlarmEvent, cfg: AlarmSetting) -> None:
        import tkinter as tk

        self._ringing = event
        start_sound(cfg.volume, loop=True)
        root = tk.Tk()
        root.title(event.title)
        root.attributes("-topmost", True)
        root.configure(bg="#0f172a")
        w, h = 520, 340
        root.geometry(f"{w}x{h}+{(root.winfo_screenwidth() - w) // 2}+{(root.winfo_screenheight() - h) // 3}")
        root.resizable(False, False)

        def close(action: str | None = None) -> None:
            stop_sound()
            if self._ringing is event:
                self._ringing = None
            try:
                root.destroy()
            except tk.TclError:
                pass
            if action == "snooze":
                self.snooze(event, cfg.snooze_minutes)
            elif action == "prayed":
                mark_prayed(event)

        icon = "\U0001F54C" if event.kind == "prayer" else "⏰"
        tk.Label(root, text=icon, font=("Segoe UI Emoji", 44), bg="#0f172a", fg="#f8fafc").pack(pady=(18, 0))
        tk.Label(root, text=event.title, font=("Segoe UI", 22, "bold"), bg="#0f172a", fg="#f8fafc").pack()
        tk.Label(root, text=event.message, font=("Segoe UI", 12), bg="#0f172a", fg="#cbd5e1").pack(pady=(4, 18))
        row = tk.Frame(root, bg="#0f172a")
        row.pack()

        def button(text: str, color: str, action: str | None) -> None:
            tk.Button(
                row, text=text, command=lambda: close(action), bg=color, fg="white", relief="flat",
                font=("Segoe UI", 11, "bold"), padx=16, pady=8, cursor="hand2",
            ).pack(side="left", padx=6)

        if event.kind == "prayer":
            button("Prayed", "#16a34a", "prayed")
        button(f"Snooze {cfg.snooze_minutes} min", "#7c3aed", "snooze")
        button("Dismiss", "#334155", None)

        root.protocol("WM_DELETE_WINDOW", lambda: close(None))
        root.after(max(5, cfg.ring_seconds) * 1000, lambda: close(None))
        root.lift()
        root.focus_force()
        root.mainloop()

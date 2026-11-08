"""Entry point of DailySchedule.exe: web server + native window + tray icon + alarm engine."""

from __future__ import annotations

import argparse
import ctypes
import os
import socket
import sys
import threading
import urllib.request

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "desktop.settings")

from .paths import APP_NAME, FROZEN  # noqa: E402

USER_AGENT = "DailyScheduleDesktop/1.0"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def already_running() -> bool:
    """Named mutex so a second launch (e.g. autostart + manual) doesn't ring alarms twice."""
    if sys.platform != "win32":
        return False
    handle = ctypes.windll.kernel32.CreateMutexW(None, False, f"Local\\{APP_NAME}.SingleInstance")
    return ctypes.windll.kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS


def launch_command() -> str:
    exe = sys.executable if FROZEN else f'"{sys.executable}" -m desktop.main'
    return f'"{exe}" --background' if FROZEN else f"{exe} --background"


def autostart_enabled() -> bool:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, APP_NAME)
            return True
    except OSError:
        return False


def set_autostart(on: bool) -> None:
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, launch_command())
        else:
            try:
                winreg.DeleteValue(k, APP_NAME)
            except OSError:
                pass


def start_server(port: int) -> None:
    from waitress import serve

    from .wsgi import application

    threading.Thread(
        target=lambda: serve(application, host="127.0.0.1", port=port, threads=4, _quiet=True),
        daemon=True,
        name="web",
    ).start()


def wait_for_server(port: int, timeout: float = 20.0) -> bool:
    import time

    end = time.time() + timeout
    while time.time() < end:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/alarms/today/", timeout=2).read()
            return True
        except Exception:
            time.sleep(0.25)
    return False


def tray_image():
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4, 4, 60, 60), fill=(124, 58, 237, 255))
    d.ellipse((14, 14, 50, 50), fill=(15, 23, 42, 255))
    d.line((32, 32, 32, 20), fill=(248, 250, 252, 255), width=4)
    d.line((32, 32, 42, 36), fill=(248, 250, 252, 255), width=4)
    return img


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--background", action="store_true", help="start hidden in the tray")
    parser.add_argument("--selftest", action="store_true", help="boot the server, check it responds, exit")
    args = parser.parse_args()

    if not args.selftest and already_running():
        return 0

    import django
    from django.core.management import call_command

    django.setup()
    call_command("migrate", interactive=False, verbosity=0)

    port = free_port()
    start_server(port)
    if not wait_for_server(port):
        print("server failed to start", file=sys.stderr)
        return 1
    if args.selftest:
        print(f"selftest ok on port {port}")
        return 0

    from .engine import AlarmEngine

    engine = AlarmEngine()
    engine.start()

    url = f"http://127.0.0.1:{port}/calendar/"
    try:
        import webview
    except ImportError:
        import webbrowser

        webbrowser.open(url)
        threading.Event().wait()  # keep alarms alive; no tray without the window libs
        return 0

    import pystray

    state = {"quitting": False}
    window = webview.create_window(
        "Daily Schedule", url, width=1280, height=820, min_size=(900, 600), hidden=args.background
    )

    def on_closing():
        if state["quitting"]:
            return True
        window.hide()  # keep running in the tray so alarms still ring
        return False

    window.events.closing += on_closing

    def quit_app(icon=None, item=None):
        state["quitting"] = True
        engine.stop()
        if icon:
            icon.stop()
        window.destroy()

    def toggle_mute(icon, item):
        engine.muted = not engine.muted

    def toggle_autostart(icon, item):
        set_autostart(not autostart_enabled())

    menu = pystray.Menu(
        pystray.MenuItem("Open Daily Schedule", lambda icon, item: window.show(), default=True),
        pystray.MenuItem("Mute alarms", toggle_mute, checked=lambda item: engine.muted),
        pystray.MenuItem("Start with Windows", toggle_autostart, checked=lambda item: autostart_enabled()),
        pystray.MenuItem("Quit (stops alarms)", quit_app),
    )
    pystray.Icon(APP_NAME, tray_image(), "Daily Schedule", menu).run_detached()

    webview.start(user_agent=USER_AGENT)
    engine.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())

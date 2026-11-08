"""Build dist/DailySchedule/DailySchedule.exe  (run: uv run python -m desktop.build)."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ["DJANGO_SETTINGS_MODULE"] = "desktop.settings"


def run(*cmd: str) -> None:
    print(">", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> None:
    run(sys.executable, "manage_desktop.py", "collectstatic", "--noinput", "--clear")
    run(
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--name", "DailySchedule",
        "--paths", str(ROOT),
        "--collect-all", "scheduler",
        "--collect-submodules", "django.contrib.admin",
        "--hidden-import", "desktop.settings", "--hidden-import", "desktop.urls", "--hidden-import", "desktop.wsgi",
        "--hidden-import", "pystray._win32", "--hidden-import", "winotify",
        "--add-data", f"{ROOT / 'staticfiles'}{os.pathsep}staticfiles",
        "desktop/launcher.py",
    )
    print("Installer package:", package())


def package() -> Path:
    """dist/DailySchedule-Setup.zip = the app folder + Install.ps1 / Uninstall.ps1."""
    stage = ROOT / "dist" / "setup"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    shutil.copytree(ROOT / "dist" / "DailySchedule", stage / "DailySchedule")
    for name in ("Install.ps1", "Uninstall.ps1"):
        shutil.copy(ROOT / "desktop" / "installer" / name, stage / name)
    archive = shutil.make_archive(str(ROOT / "dist" / "DailySchedule-Setup"), "zip", stage)
    shutil.rmtree(stage)
    return Path(archive)


if __name__ == "__main__":
    main()

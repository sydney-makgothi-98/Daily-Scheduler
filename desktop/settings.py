"""Django settings for the standalone Windows app: SQLite in %APPDATA%, no external Redis."""

import json
import secrets

from scheduler.types import Broker, SchedulerConfiguration

from .paths import DATA_DIR, RESOURCE_DIR

DESKTOP_MODE = True
DEBUG = False
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# Per-install secret, generated once and kept in the user's data folder.
_secret_file = DATA_DIR / "secret.json"
if not _secret_file.exists():
    _secret_file.write_text(json.dumps({"key": secrets.token_urlsafe(50)}))
SECRET_KEY = json.loads(_secret_file.read_text())["key"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "scheduler.apps.SchedulerConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "desktop.urls"
WSGI_APPLICATION = "desktop.wsgi.application"

# The job queue is not used by the planner; an in-memory fake broker keeps the admin pages importable.
SCHEDULER_CONFIG = SchedulerConfiguration(BROKER=Broker.FAKEREDIS)
SCHEDULER_QUEUES = {}

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": DATA_DIR / "db.sqlite3"}}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"  # tasks are stored as naive local times (USE_TZ = False), as in the web version
USE_I18N = True
USE_TZ = False

STATIC_URL = "/static/"
STATIC_ROOT = RESOURCE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

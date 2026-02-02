from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.core.apps.CoreConfig",
    "apps.reference",
    "apps.analysis.apps.AnalysisConfig",
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

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "app_db"),
        "USER": os.environ.get("POSTGRES_USER", "app_user"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "app_password"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    },
    "portal": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("PORTAL_DB", "portal_db"),
        "USER": os.environ.get("PORTAL_USER", "portal_user"),
        "PASSWORD": os.environ.get("PORTAL_PASSWORD", "portal_password"),
        "HOST": os.environ.get("PORTAL_HOST", "localhost"),
        "PORT": os.environ.get("PORTAL_PORT", "5432"),
    },
}

DATABASE_ROUTERS = ["apps.analysis.db_router.PortalRouter"]

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "core.AppUser"

LOGIN_URL = "/login"
LOGIN_REDIRECT_URL = "/upload"

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
RESULT_TTL_SECONDS = int(os.environ.get("RESULT_TTL_SECONDS", "1800"))

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL)
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 60 * 15

DOCS_DIR = BASE_DIR / "docs"

SEMANTIC_MODEL_NAME = os.environ.get(
    "SEMANTIC_MODEL_NAME", "intfloat/multilingual-e5-large"
)

APP_ADMIN_LOGIN = os.environ.get("APP_ADMIN_LOGIN", "admin")
APP_ADMIN_PASSWORD = os.environ.get("APP_ADMIN_PASSWORD", "admin")

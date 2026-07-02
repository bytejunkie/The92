import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-ys(6kc9$@*96&(tiu(9w2z2tgb-r_4(8#dvv8382^o#^13p!oc",
)

DEBUG = False

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "accounts",
    "grounds",
    "django.contrib.sites",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/London"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "theme" / "static"]

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

AUTH_USER_MODEL = "accounts.User"
LOGIN_REDIRECT_URL = "grounds:home"
LOGOUT_REDIRECT_URL = "grounds:home"

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "none"

SOCIALACCOUNT_AUTO_SIGNUP = False
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_FORMS = {"signup": "accounts.forms.SocialSignupForm"}

# Third-party API keys
FOOTBALL_DATA_API_KEY = os.environ.get("FOOTBALL_DATA_API_KEY", "")

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "OAUTH_PKCE_ENABLED": True,
    }
}

# Logging — console always; ship to Better Stack (Logtail) when configured.
# Set LOGTAIL_SOURCE_TOKEN and LOGTAIL_INGESTING_HOST (both required by
# Better Stack) via .env locally or as Railway service variables in prod.
LOGTAIL_SOURCE_TOKEN = os.environ.get("LOGTAIL_SOURCE_TOKEN", "")
LOGTAIL_INGESTING_HOST = os.environ.get("LOGTAIL_INGESTING_HOST", "")
DJANGO_LOG_LEVEL = os.environ.get("DJANGO_LOG_LEVEL", "INFO")

# Render all log timestamps in UTC/GMT (not the machine's local time, which
# is BST in summer) so console and Better Stack line up regardless of host TZ.
logging.Formatter.converter = time.gmtime

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} UTC {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": DJANGO_LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": DJANGO_LOG_LEVEL,
            "propagate": False,
        },
    },
}

if LOGTAIL_SOURCE_TOKEN and LOGTAIL_INGESTING_HOST:
    _logtail_host = LOGTAIL_INGESTING_HOST
    if not _logtail_host.startswith("http"):
        _logtail_host = f"https://{_logtail_host}"
    # The Logtail handler does network I/O on emit(). Run it behind a
    # QueueHandler so logging never blocks the request/startup threads — this
    # keeps logging off the request path in production and avoids a deadlock
    # with the runserver autoreloader. Python 3.12+ dictConfig creates and
    # starts the listener thread automatically.
    LOGGING["handlers"]["betterstack"] = {
        "class": "logtail.LogtailHandler",
        "source_token": LOGTAIL_SOURCE_TOKEN,
        "host": _logtail_host,
        "formatter": "verbose",
    }
    LOGGING["handlers"]["betterstack_queue"] = {
        "class": "logging.handlers.QueueHandler",
        "handlers": ["betterstack"],
    }
    LOGGING["root"]["handlers"].append("betterstack_queue")
    LOGGING["loggers"]["django"]["handlers"].append("betterstack_queue")

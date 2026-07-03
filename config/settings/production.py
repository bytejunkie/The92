import os

import dj_database_url

from .base import *  # noqa: F401, F403
from .base import BASE_DIR, DATABASES

DEBUG = False
ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h]

# Trust the scheme forwarded by Railway's edge proxy (and Cloudflare in front of
# it). Without this Django sees plain HTTP behind the TLS-terminating proxy and
# SECURE_SSL_REDIRECT below would loop forever.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CSRF_TRUSTED_ORIGINS = [
    o
    for o in os.environ.get(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "https://the92.uk,https://www.the92.uk",
    ).split(",")
    if o
]

# Postgres in production via Railway's injected DATABASE_URL. Falls back to the
# base SQLite config if the var is absent (e.g. running prod settings locally).
if os.environ.get("DATABASE_URL"):
    DATABASES["default"] = dj_database_url.config(
        conn_max_age=600,
        conn_health_checks=True,
    )

STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise compresses and fingerprints static files. Requires collectstatic to
# have run (handled by the pre-deploy command).
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "config.storage.WhiteNoiseStaticFilesStorage",
    },
}

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

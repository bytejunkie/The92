# The92 production image. Pinned to Python 3.14 to match local/dev and the
# project's requires-python; Railway's Nixpacks images don't ship 3.14 yet.
FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    # Install the resolved deps straight into the system env so gunicorn /
    # manage.py are on PATH without activating a venv.
    UV_PROJECT_ENVIRONMENT=/usr/local

# uv, copied from its official distroless image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first so the layer caches across code changes. The
# project itself is package = false, so this installs deps only.
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project

# Application code.
COPY . .

# Collect static at build time so the fingerprinted assets + manifest are baked
# into the image. It can't run as a pre-deploy step: that runs in a throwaway
# container whose filesystem is discarded before the app boots. Uses the
# insecure fallback SECRET_KEY — fine, collectstatic touches no secrets or DB.
ENV DJANGO_SETTINGS_MODULE=config.settings.production
RUN python manage.py collectstatic --noinput

# migrate runs as Railway's pre-deploy step (railway.json) against Postgres.
CMD gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8080} --workers 3

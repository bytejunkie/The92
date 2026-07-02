"""Domain-event telemetry.

One call — log_event(...) — persists an Event row (for day-by-day monitoring in
the admin) AND emits a structured log line (for Better Stack / live tailing).
Telemetry must never break the user action it records, so persistence failures
are swallowed and logged, not raised.
"""

import logging

from .models import Event

logger = logging.getLogger("the92.events")


def log_event(event_type, *, user=None, ground=None, **context):
    """Record a domain event.

    event_type: an Event.Type value (or its string).
    user:       the acting user (AnonymousUser is stored as null).
    ground:     the ground involved, if any.
    context:    extra key/values (e.g. followed="bob"), stored on the row and
                attached to the log line.
    """
    etype = getattr(event_type, "value", event_type)
    actor = user if (user is not None and getattr(user, "is_authenticated", False)) else None

    try:
        Event.objects.create(event_type=etype, user=actor, ground=ground, context=context)
    except Exception:  # noqa: BLE001 — telemetry must not break the request
        logger.exception("event_persist_failed", extra={"event": etype})

    logger.info(
        "event",
        extra={
            "event": etype,
            "username": getattr(actor, "username", None),
            "ground": getattr(ground, "slug", None),
            **context,
        },
    )

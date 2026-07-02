"""Template helpers for grounds/teams."""

from functools import lru_cache

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()

_CREST_DIR = "theme/img/crests"


@lru_cache(maxsize=512)
def _crest_rel(slug: str) -> str:
    """Return the static-relative crest path for a team slug if the file
    exists, else "". Cached per process — crests are committed static assets
    keyed on slug (like the league logos), so there is no DB/media coupling."""
    rel = f"{_CREST_DIR}/{slug}.png"
    return rel if finders.find(rel) else ""


@register.simple_tag
def crest_url(team) -> str:
    """Static URL of a team's crest, or "" when no crest asset is present.

    Usage:
        {% load ground_extras %}
        {% crest_url ground.team as crest %}
        {% if crest %}<img src="{{ crest }}" alt="{{ ground.team.name }}">{% endif %}
    """
    if not team or not getattr(team, "slug", ""):
        return ""
    rel = _crest_rel(team.slug)
    return static(rel) if rel else ""

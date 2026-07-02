"""
Import Premier League fixtures from football-data.org into the Match model.

Upserts on external_id — safe to re-run to refresh scores and status.

Usage:
    uv run python manage.py import_fixtures
    uv run python manage.py import_fixtures --season 2024  # e.g. 2023/24
"""

import json
import urllib.request

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from grounds.models import Ground, Match, Team

API_BASE = "https://api.football-data.org/v4"
COMPETITION = "PL"

# Overrides where stripping " FC"/" AFC" still doesn't give an exact match
NAME_OVERRIDES: dict[str, str] = {}


def _fetch(path: str) -> dict:
    key = getattr(settings, "FOOTBALL_DATA_API_KEY", "")
    if not key:
        raise CommandError("FOOTBALL_DATA_API_KEY is not set. Add it to .env.")
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        headers={"X-Auth-Token": key},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _canonical_name(api_name: str) -> str:
    if api_name in NAME_OVERRIDES:
        return NAME_OVERRIDES[api_name]
    for suffix in (" FC", " AFC", " F.C.", " A.F.C."):
        if api_name.endswith(suffix):
            return api_name[: -len(suffix)]
    return api_name


def _build_team_map() -> dict[int, Team]:
    """Return {football-data team id → Team} by resolving API team list against DB."""
    data = _fetch(f"/competitions/{COMPETITION}/teams")
    team_map: dict[int, Team] = {}
    unmatched: list[str] = []

    # Index our DB teams by canonical name (case-insensitive)
    db_by_name = {t.name.lower(): t for t in Team.objects.all()}

    for api_team in data["teams"]:
        canonical = _canonical_name(api_team["name"]).lower()
        team = db_by_name.get(canonical)
        if not team:
            # Try shortName
            short = api_team.get("shortName", "").lower()
            team = db_by_name.get(short)
        if team:
            team_map[api_team["id"]] = team
        else:
            unmatched.append(f"{api_team['name']!r} (id={api_team['id']})")

    return team_map, unmatched


class Command(BaseCommand):
    help = "Import Premier League fixtures from football-data.org."

    def add_arguments(self, parser):
        parser.add_argument(
            "--season",
            type=int,
            help="Season start year (e.g. 2025 for 2025/26). Defaults to current season.",
        )

    def handle(self, *args, **options):
        season_param = f"?season={options['season']}" if options.get("season") else ""

        self.stdout.write("Resolving team names …")
        team_map, unmatched = _build_team_map()
        if unmatched:
            self.stdout.write(self.style.WARNING(f"  Unmatched teams: {', '.join(unmatched)}"))
        self.stdout.write(f"  {len(team_map)} teams mapped.")

        # Preload ground lookup (home_team_id → Ground)
        ground_by_team = {
            g.team_id: g
            for g in Ground.objects.filter(team__isnull=False).select_related("team")
        }

        self.stdout.write("Fetching matches …")
        data = _fetch(f"/competitions/{COMPETITION}/matches{season_param}")
        matches = data["matches"]
        self.stdout.write(f"  {len(matches)} matches received.")

        created = updated = skipped = 0

        for m in matches:
            ext_id = m["id"]
            home_api_id = m["homeTeam"]["id"]
            away_api_id = m["awayTeam"]["id"]

            home_team = team_map.get(home_api_id)
            away_team = team_map.get(away_api_id)
            ground = ground_by_team.get(home_team.pk) if home_team else None

            score = m.get("score", {})
            ft = score.get("fullTime", {})
            home_score = ft.get("home")
            away_score = ft.get("away")

            kickoff = timezone.datetime.fromisoformat(
                m["utcDate"].replace("Z", "+00:00")
            )

            defaults = {
                "home_team": home_team,
                "away_team": away_team,
                "ground": ground,
                "kickoff": kickoff,
                "competition": COMPETITION,
                "matchday": m.get("matchday"),
                "status": m.get("status", "SCHEDULED"),
                "home_score": home_score,
                "away_score": away_score,
            }

            obj, was_created = Match.objects.update_or_create(
                external_id=ext_id,
                defaults=defaults,
            )

            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. {created} created, {updated} updated, {skipped} skipped."
            )
        )

"""
Import team crests and league logos from TheSportsDB.

- Team crests -> Team.logo (media/team-logos/<slug>.png). Sourced per league via
  lookup_all_teams.php (bounded roster, so no fuzzy-search / U21 mismatch).
- League logos -> theme/static/theme/img/leagues/<slug>.png, replacing the
  placeholder text-pill SVGs that the ground card/detail templates render.

Idempotent: skips teams that already have a logo unless --force.

NOTE: club crests and league badges are trademarked. TheSportsDB hosts them, but
serving them publicly is a licensing question — verify before going live.

Usage:
    uv run python manage.py import_sportsdb_logos
    uv run python manage.py import_sportsdb_logos --force
    uv run python manage.py import_sportsdb_logos --leagues-only
"""

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from grounds.models import Team

API = "https://www.thesportsdb.com/api/v1/json/123"

# our league_level slug -> TheSportsDB league id
LEAGUES = {
    "premier-league": 4328,
    "championship": 4329,
    "league-one": 4396,
    "league-two": 4397,
}

# TheSportsDB strTeam -> our Team.name where they differ
NAME_OVERRIDES = {
    "Milton Keynes Dons": "MK Dons",
    "Brighton and Hove Albion": "Brighton & Hove Albion",
}

# our Team.name -> the query to search TheSportsDB with (where ours finds nothing)
SEARCH_ALIASES = {
    "AFC Bournemouth": "Bournemouth",
    "King's Lynn Town": "King's Lynn Town FC",
    "Republic of Ireland": "Ireland",
}

HEADERS = {"User-Agent": "The92-LogoImport/1.0"}


def _get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def _download(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()


class Command(BaseCommand):
    help = "Import team crests and league logos from TheSportsDB."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true",
                            help="Overwrite logos that already exist")
        parser.add_argument("--teams-only", action="store_true")
        parser.add_argument("--leagues-only", action="store_true")
        parser.add_argument("--pause", type=float, default=2.0)

    def handle(self, *args, **opts):
        if not opts["leagues_only"]:
            self._import_team_crests(opts)
        if not opts["teams_only"]:
            self._import_league_logos(opts)

    def _import_team_crests(self, opts):
        # NOTE: the free key's lookup_all_teams.php ignores the league id (returns
        # a fixed 24-team sample), so we search per team by full name instead —
        # which disambiguates cleanly (the short name is what pulls in U21 sides).
        self.stdout.write(self.style.MIGRATE_HEADING("Team crests:"))
        teams = Team.objects.all() if opts["force"] else Team.objects.filter(logo="")
        done = nobadge = notfound = 0

        for team in teams:
            q = urllib.parse.quote(SEARCH_ALIASES.get(team.name, team.name))
            try:
                data = _get(f"{API}/searchteams.php?t={q}")
            except Exception as e:  # noqa: BLE001
                self.stderr.write(f"  {team.name}: search failed ({e})")
                time.sleep(opts["pause"])
                continue

            badge = self._pick_badge(team.name, data.get("teams") or [])
            time.sleep(opts["pause"])
            if badge is None:
                notfound += 1
                self.stderr.write(f"  ? {team.name}: no match")
                continue
            try:
                content = _download(badge)
            except Exception as e:  # noqa: BLE001
                nobadge += 1
                self.stderr.write(f"  {team.name}: download failed ({e})")
                continue
            team.logo.save(f"{team.slug}.png", ContentFile(content), save=True)
            self.stdout.write(f"  + {team.name}")
            done += 1

        self.stdout.write(self.style.SUCCESS(
            f"  crests: {done} saved, {notfound} no match, {nobadge} download failed"
        ))

    @staticmethod
    def _pick_badge(name, results):
        """Choose the badge for the senior England club matching `name`."""
        skip = ("U21", "U23", "U19", "U18", "Women", "Ladies", "Reserve")
        # 1) exact name match (allowing the TheSportsDB->our-name override)
        for r in results:
            st = r.get("strTeam") or ""
            if st == name or NAME_OVERRIDES.get(st) == name or st.lower() == name.lower():
                if r.get("strBadge"):
                    return r["strBadge"]
        # 2) first senior team with a badge (skip youth/women/reserve sides)
        for r in results:
            st = r.get("strTeam") or ""
            if any(x in st for x in skip):
                continue
            if r.get("strBadge"):
                return r["strBadge"]
        return None

    def _import_league_logos(self, opts):
        self.stdout.write(self.style.MIGRATE_HEADING("League logos:"))
        dest = Path(settings.BASE_DIR) / "theme" / "static" / "theme" / "img" / "leagues"
        dest.mkdir(parents=True, exist_ok=True)
        done = 0
        for slug, lid in LEAGUES.items():
            png = dest / f"{slug}.png"
            if png.exists() and not opts["force"]:
                self.stdout.write(f"  = {slug} (exists)")
                continue
            data = _get(f"{API}/lookupleague.php?id={lid}")
            badge = (data.get("leagues") or [{}])[0].get("strBadge")
            if not badge:
                self.stderr.write(f"  {slug}: no badge")
                continue
            png.write_bytes(_download(badge))
            self.stdout.write(f"  + {slug}.png")
            done += 1
            time.sleep(opts["pause"])
        self.stdout.write(self.style.SUCCESS(f"  league logos: {done} saved"))

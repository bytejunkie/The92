"""
Fetch a full season's fixtures for the top four English tiers from TheSportsDB
and write a CSV in the schema expected by import_csv_fixtures.

Why TheSportsDB: it is the only free source that carries League One/Two fixtures
(football-data.org's free tier and fixturedownload.com cover only PL +
Championship). The free key's season endpoint caps at 15 events, but the
per-ROUND endpoint (eventsround.php) is uncapped, so we assemble the season
round by round. Free key is rate-limited (~30 req/min) -> default 2.5s pause.

Produces upcoming fixtures: no scores, status SCHEDULED, matchday = round.

Usage:
    uv run python manage.py fetch_sportsdb_fixtures              # 2026-2027
    uv run python manage.py fetch_sportsdb_fixtures --season 2027-2028
    uv run python manage.py import_csv_fixtures data/sportsdb/fixtures_2026.csv --dry-run
"""

import csv
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

API = "https://www.thesportsdb.com/api/v1/json/{key}/eventsround.php?id={lid}&r={r}&s={season}"

# our competition code -> TheSportsDB league id
LEAGUES = {
    "PL": 4328,    # Premier League        (38 rounds)
    "ELC": 4329,   # Championship          (46 rounds)
    "EL1": 4396,   # League One            (46 rounds)
    "EL2": 4397,   # League Two            (46 rounds)
}

DEFAULT_KICKOFF_TIME = "15:00:00"


class Command(BaseCommand):
    help = "Fetch a season's fixtures (all four tiers) from TheSportsDB into a CSV."

    def add_arguments(self, parser):
        parser.add_argument("--season", default="2026-2027",
                            help="TheSportsDB season string, e.g. 2026-2027")
        parser.add_argument("--key", default="123",
                            help="TheSportsDB API key (default: free test key 123)")
        parser.add_argument("--max-rounds", type=int, default=50,
                            help="Highest round to try before giving up")
        parser.add_argument("--pause", type=float, default=2.5,
                            help="Seconds between requests (free key ~30/min)")

    def handle(self, *args, **opts):
        season = opts["season"]
        key = opts["key"]
        start_year = season[:4]

        rows: list[dict] = []
        for comp, lid in LEAGUES.items():
            empty_streak = 0
            comp_count = 0
            for r in range(1, opts["max_rounds"] + 1):
                url = API.format(key=key, lid=lid, r=r, season=season)
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "The92/1.0"})
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        data = json.load(resp)
                except (urllib.error.URLError, json.JSONDecodeError) as e:
                    self.stderr.write(f"  {comp} round {r}: {e}")
                    time.sleep(opts["pause"])
                    continue

                events = data.get("events") or []
                time.sleep(opts["pause"])
                if not events:
                    empty_streak += 1
                    if empty_streak >= 2:
                        break
                    continue
                empty_streak = 0

                for e in events:
                    home = (e.get("strHomeTeam") or "").strip()
                    away = (e.get("strAwayTeam") or "").strip()
                    if not home or not away:
                        continue
                    rows.append({
                        "competition": comp,
                        "season": start_year,
                        "home_team": home,
                        "away_team": away,
                        "kickoff": self._kickoff(e),
                        "home_score": "",
                        "away_score": "",
                        "status": "SCHEDULED",
                        "matchday": e.get("intRound") or r,
                    })
                    comp_count += 1
            self.stdout.write(f"  {comp}: {comp_count} fixtures")

        out_dir = Path(settings.BASE_DIR) / "data" / "sportsdb"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"fixtures_{start_year}.csv"
        fieldnames = ["competition", "season", "home_team", "away_team",
                      "kickoff", "home_score", "away_score", "status", "matchday"]
        with open(out_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)

        self.stdout.write(self.style.SUCCESS(
            f"\nWrote {len(rows):,} fixtures to {out_path.relative_to(settings.BASE_DIR)}"
        ))

    def _kickoff(self, e) -> str:
        ts = (e.get("strTimestamp") or "").strip()
        if ts:
            return ts if ts.endswith("Z") else ts + "Z"
        date = (e.get("dateEvent") or "").strip()
        t = (e.get("strTime") or "").strip() or DEFAULT_KICKOFF_TIME
        return f"{date}T{t}Z"

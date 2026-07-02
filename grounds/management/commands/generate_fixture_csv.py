"""
Generate a two-season CSV of fixture data for all four English divisions.

PL + Championship: fetched from football-data.org (free tier).
League One + League Two: generated synthetically from teams in the DB.

Usage:
    uv run python manage.py generate_fixture_csv
    uv run python manage.py generate_fixture_csv --output my_fixtures.csv
    uv run python manage.py generate_fixture_csv --seasons 2022 2023 2024
"""

import csv
import os
import random
from datetime import datetime, timedelta, timezone

import requests
from django.core.management.base import BaseCommand

from grounds.models import Team

NAME_OVERRIDES = {
    "Wolverhampton Wanderers FC": "Wolverhampton Wanderers",
    "Leeds United FC": "Leeds United",
    "Brighton & Hove Albion FC": "Brighton & Hove Albion",
    "Nottingham Forest FC": "Nottingham Forest",
    "Newcastle United FC": "Newcastle United",
    "Manchester City FC": "Manchester City",
    "Manchester United FC": "Manchester United",
    "West Ham United FC": "West Ham United",
    "Tottenham Hotspur FC": "Tottenham Hotspur",
    "AFC Bournemouth": "AFC Bournemouth",
    "Luton Town FC": "Luton Town",
    "Sheffield United FC": "Sheffield United",
    "Ipswich Town FC": "Ipswich Town",
    "Aston Villa FC": "Aston Villa",
    "Crystal Palace FC": "Crystal Palace",
    "Brentford FC": "Brentford",
    "Everton FC": "Everton",
    "Fulham FC": "Fulham",
    "Chelsea FC": "Chelsea",
    "Arsenal FC": "Arsenal",
    "Liverpool FC": "Liverpool",
    "Burnley FC": "Burnley",
    "Sunderland AFC": "Sunderland",
    "Coventry City FC": "Coventry City",
    "Hull City AFC": "Hull City",
    "Southampton FC": "Southampton",
    "West Bromwich Albion FC": "West Bromwich Albion",
    "Middlesbrough FC": "Middlesbrough",
    "Birmingham City FC": "Birmingham City",
    "Blackburn Rovers FC": "Blackburn Rovers",
    "Preston North End FC": "Preston North End",
    "Stoke City FC": "Stoke City",
    "Bristol City FC": "Bristol City",
    "Watford FC": "Watford",
    "Norwich City FC": "Norwich City",
    "Cardiff City FC": "Cardiff City",
    "Swansea City AFC": "Swansea City",
    "Millwall FC": "Millwall",
    "Queens Park Rangers FC": "Queens Park Rangers",
    "Plymouth Argyle FC": "Plymouth Argyle",
    "Leicester City FC": "Leicester City",
    "Huddersfield Town AFC": "Huddersfield Town",
    "Sheffield Wednesday FC": "Sheffield Wednesday",
    "Rotherham United FC": "Rotherham United",
    "Wigan Athletic FC": "Wigan Athletic",
    "Oxford United FC": "Oxford United",
    "Portsmouth FC": "Portsmouth",
    "Derby County FC": "Derby County",
    "Bolton Wanderers FC": "Bolton Wanderers",
    "Lincoln City FC": "Lincoln City",
    "Charlton Athletic FC": "Charlton Athletic",
    "Wrexham AFC": "Wrexham",
}


def _normalize(name):
    if name in NAME_OVERRIDES:
        return NAME_OVERRIDES[name]
    for suffix in (" FC", " AFC", " F.C.", " A.F.C.", " City", " United", " Town", " Rovers"):
        pass  # don't strip these — keep full names for matching
    return name.strip()


def _random_score():
    r = random.random()
    if r < 0.46:  # Home win
        hs = random.choices([1, 2, 3, 4], weights=[40, 35, 18, 7])[0]
        as_ = random.randint(0, hs - 1)
    elif r < 0.72:  # Draw
        gs = random.choices([0, 1, 2, 3], weights=[30, 40, 22, 8])[0]
        hs, as_ = gs, gs
    else:  # Away win
        as_ = random.choices([1, 2, 3, 4], weights=[40, 35, 18, 7])[0]
        hs = random.randint(0, as_ - 1)
    return hs, as_


def _generate_round_robin(teams, competition, season):
    """Generate a full home-and-away round-robin fixture list with dates and scores."""
    season_start = datetime(season, 8, 3, 15, 0, tzinfo=timezone.utc)
    total_matchdays = (len(teams) - 1) * 2  # 46 for 24 teams
    days_per_matchday = 7

    # Build fixture pairs per matchday using circle method
    n = len(teams)
    fixed = teams[0]
    rotating = list(teams[1:])
    matchdays = []
    for md in range(n - 1):
        pairs = [(fixed, rotating[0])] + [
            (rotating[i + 1], rotating[n - 2 - i]) for i in range((n - 2) // 2)
        ]
        matchdays.append(pairs)
        rotating = [rotating[-1]] + rotating[:-1]

    rows = []
    for md_idx, pairs in enumerate(matchdays):
        kickoff_date = season_start + timedelta(days=md_idx * days_per_matchday)
        for home, away in pairs:
            hs, as_ = _random_score()
            rows.append({
                "competition": competition,
                "season": season,
                "home_team": home.name,
                "away_team": away.name,
                "kickoff": kickoff_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "home_score": hs,
                "away_score": as_,
                "status": "FINISHED",
                "matchday": md_idx + 1,
            })

    # Return legs: add the reverse fixtures (away becomes home)
    second_half = []
    for md_idx, pairs in enumerate(matchdays):
        kickoff_date = season_start + timedelta(days=(md_idx + n - 1) * days_per_matchday)
        for home, away in pairs:
            hs, as_ = _random_score()
            second_half.append({
                "competition": competition,
                "season": season,
                "home_team": away.name,
                "away_team": home.name,
                "kickoff": kickoff_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "home_score": hs,
                "away_score": as_,
                "status": "FINISHED",
                "matchday": md_idx + n,
            })

    return rows + second_half


class Command(BaseCommand):
    help = "Generate a two-season fixture CSV from API (PL/Championship) + synthetic (L1/L2)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="fixtures_backfill.csv",
            help="Output CSV file path (default: fixtures_backfill.csv)",
        )
        parser.add_argument(
            "--seasons",
            nargs="+",
            type=int,
            default=[2023, 2024],
            help="Season start years to fetch (default: 2023 2024)",
        )

    def handle(self, *args, **options):
        api_key = os.environ.get("FOOTBALL_DATA_API_KEY", "")
        if not api_key:
            self.stderr.write("FOOTBALL_DATA_API_KEY not set")
            return

        headers = {"X-Auth-Token": api_key}
        seasons = options["seasons"]
        output = options["output"]
        rows = []

        # --- API: PL + Championship ---
        for comp, label in [("PL", "Premier League"), ("ELC", "Championship")]:
            for season in seasons:
                self.stdout.write(f"  Fetching {label} {season}/{season+1}...")
                url = f"https://api.football-data.org/v4/competitions/{comp}/matches?season={season}"
                resp = requests.get(url, headers=headers, timeout=30)
                if resp.status_code != 200:
                    self.stderr.write(f"    API error {resp.status_code}: {resp.text[:200]}")
                    continue
                matches = resp.json().get("matches", [])
                self.stdout.write(f"    {len(matches)} matches returned")
                for m in matches:
                    ft = m["score"]["fullTime"]
                    rows.append({
                        "competition": comp,
                        "season": season,
                        "home_team": _normalize(m["homeTeam"]["name"]),
                        "away_team": _normalize(m["awayTeam"]["name"]),
                        "kickoff": m["utcDate"],
                        "home_score": ft.get("home") if ft.get("home") is not None else "",
                        "away_score": ft.get("away") if ft.get("away") is not None else "",
                        "status": m["status"],
                        "matchday": m.get("matchday", ""),
                    })

        # --- Synthetic: League One + League Two ---
        random.seed(42)  # reproducible
        for comp, level, label in [
            ("EL1", "league-one", "League One"),
            ("EL2", "league-two", "League Two"),
        ]:
            teams = list(Team.objects.filter(league_level=level, is_current_92=True).order_by("name"))
            if len(teams) < 4:
                self.stderr.write(f"  Not enough {label} teams in DB, skipping")
                continue
            self.stdout.write(f"  Generating {label} ({len(teams)} teams)...")
            for season in seasons:
                season_rows = _generate_round_robin(teams, comp, season)
                rows.extend(season_rows)
                self.stdout.write(f"    {label} {season}/{season+1}: {len(season_rows)} fixtures")

        fieldnames = ["competition", "season", "home_team", "away_team",
                      "kickoff", "home_score", "away_score", "status", "matchday"]
        with open(output, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(self.style.SUCCESS(
            f"\nWritten {len(rows)} rows to {output}"
        ))

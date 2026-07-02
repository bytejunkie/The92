"""
Fetch historical English league results from football-data.co.uk and build a
consolidated CSV in the schema expected by ``import_csv_fixtures``.

football-data.co.uk publishes free, static, per-division/per-season CSVs:

    https://www.football-data.co.uk/mmz4281/{seasoncode}/{div}.csv

Divisions used (English league pyramid, tiers 1-4):
    E0 -> Premier League   (PL)
    E1 -> Championship     (ELC)
    E2 -> League One       (EL1)
    E3 -> League Two       (EL2)

Coverage on the source: all four divisions from season 1993-94 onward, with
full seasons (~552 matches per lower division). The data is free to download
with no key. We cache the raw files (gitignored) and emit a single normalised
dataset (committed) that can be imported locally and on the live site via:

    uv run python manage.py import_csv_fixtures data/football-data/historical_results.csv

Usage:
    uv run python manage.py fetch_footballdata
    uv run python manage.py fetch_footballdata --from 1993 --to 2025
    uv run python manage.py fetch_footballdata --refresh   # re-download cached files
"""

import csv
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

BASE_URL = "https://www.football-data.co.uk/mmz4281/{code}/{div}.csv"

# football-data division code -> (competition code used in our Match model, label)
DIVISIONS = {
    "E0": ("PL", "Premier League"),
    "E1": ("ELC", "Championship"),
    "E2": ("EL1", "League One"),
    "E3": ("EL2", "League Two"),
}

DEFAULT_KICKOFF_TIME = "15:00"  # used when the source row has no Time column


def _season_code(start_year: int) -> str:
    """1993 -> '9394', 2000 -> '0001', 2025 -> '2526'."""
    return f"{start_year % 100:02d}{(start_year + 1) % 100:02d}"


def _parse_date(raw: str) -> datetime | None:
    """football-data uses DD/MM/YY (older) or DD/MM/YYYY (newer)."""
    raw = (raw or "").strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _kickoff_iso(date_str: str, time_str: str | None) -> str | None:
    d = _parse_date(date_str)
    if d is None:
        return None
    t = (time_str or "").strip() or DEFAULT_KICKOFF_TIME
    # Normalise odd time values to a safe default
    try:
        datetime.strptime(t, "%H:%M")
    except ValueError:
        t = DEFAULT_KICKOFF_TIME
    return f"{d:%Y-%m-%d}T{t}:00Z"


class Command(BaseCommand):
    help = "Download football-data.co.uk results and build a consolidated import CSV"

    def add_arguments(self, parser):
        parser.add_argument("--from", dest="from_year", type=int, default=1993,
                            help="First season start year (default 1993)")
        parser.add_argument("--to", dest="to_year", type=int, default=None,
                            help="Last season start year (default: current season)")
        parser.add_argument("--refresh", action="store_true",
                            help="Re-download files even if cached")
        parser.add_argument("--pause", type=float, default=1.0,
                            help="Seconds to pause between downloads (politeness)")

    def handle(self, *args, **opts):
        from_year = opts["from_year"]
        # Current English season starts in the year of (month >= 7 ? this year : last year)
        now = datetime.utcnow()
        current_start = now.year if now.month >= 7 else now.year - 1
        to_year = opts["to_year"] or current_start

        data_dir = Path(settings.BASE_DIR) / "data" / "football-data"
        raw_dir = data_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        out_path = data_dir / "historical_results.csv"

        rows: list[dict] = []
        downloaded = cached = failed = 0

        for start_year in range(from_year, to_year + 1):
            code = _season_code(start_year)
            for div, (comp, label) in DIVISIONS.items():
                cache_file = raw_dir / f"{code}_{div}.csv"
                if cache_file.exists() and not opts["refresh"]:
                    text = cache_file.read_text(encoding="latin-1", errors="replace")
                    cached += 1
                else:
                    url = BASE_URL.format(code=code, div=div)
                    try:
                        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(req, timeout=30) as resp:
                            text = resp.read().decode("latin-1", "replace")
                        cache_file.write_text(text, encoding="latin-1")
                        downloaded += 1
                        time.sleep(opts["pause"])
                    except urllib.error.HTTPError as e:
                        self.stderr.write(f"  {start_year}-{start_year+1} {div}: HTTP {e.code} (skipped)")
                        failed += 1
                        continue
                    except Exception as e:  # noqa: BLE001
                        self.stderr.write(f"  {start_year}-{start_year+1} {div}: {e} (skipped)")
                        failed += 1
                        continue

                added = self._parse_rows(text, comp, start_year, rows)
                self.stdout.write(f"  {start_year}-{start_year+1} {label:14s} ({div}): {added} matches")

        rows.sort(key=lambda r: (r["kickoff"], r["competition"]))

        fieldnames = ["competition", "season", "home_team", "away_team",
                      "kickoff", "home_score", "away_score", "status", "matchday"]
        with open(out_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(self.style.SUCCESS(
            f"\nDownloaded {downloaded}, cached {cached}, failed {failed}.\n"
            f"Wrote {len(rows):,} matches to {out_path.relative_to(settings.BASE_DIR)}"
        ))

    def _parse_rows(self, text: str, comp: str, start_year: int, rows: list[dict]) -> int:
        reader = csv.DictReader(text.splitlines())
        added = 0
        for r in reader:
            home = (r.get("HomeTeam") or "").strip()
            away = (r.get("AwayTeam") or "").strip()
            hg = (r.get("FTHG") or "").strip()
            ag = (r.get("FTAG") or "").strip()
            if not home or not away or hg == "" or ag == "":
                continue  # future/abandoned/blank row
            kickoff = _kickoff_iso(r.get("Date"), r.get("Time"))
            if kickoff is None:
                continue
            try:
                home_score = int(float(hg))
                away_score = int(float(ag))
            except ValueError:
                continue
            rows.append({
                "competition": comp,
                "season": str(start_year),
                "home_team": home,
                "away_team": away,
                "kickoff": kickoff,
                "home_score": home_score,
                "away_score": away_score,
                "status": "FINISHED",
                "matchday": "",
            })
            added += 1
        return added

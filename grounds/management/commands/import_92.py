import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from grounds.models import Ground, Team

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "the92.csv"


class Command(BaseCommand):
    help = "Import all 92 clubs and grounds from grounds/data/the92.csv"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing teams and grounds before importing.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            Ground.objects.all().delete()
            Team.objects.all().delete()
            self.stdout.write("Cleared existing teams and grounds.")

        teams_created = teams_updated = grounds_created = grounds_updated = 0

        with DATA_FILE.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                team, created = Team.objects.update_or_create(
                    name=row["team_name"],
                    defaults={
                        "league_level": row["league_level"],
                        "is_current_92": True,
                        "primary_colour": row["primary_colour"],
                    },
                )
                if created:
                    teams_created += 1
                else:
                    teams_updated += 1

                capacity = int(row["capacity"]) if row["capacity"] else None
                opened_year = int(row["opened_year"]) if row["opened_year"] else None
                slug = row.get("ground_slug") or slugify(row["ground_name"])

                _, created = Ground.objects.update_or_create(
                    name=row["ground_name"],
                    defaults={
                        "slug": slug,
                        "team": team,
                        "town_or_city": row["town_or_city"],
                        "postcode": row["postcode"],
                        "capacity": capacity,
                        "opened_year": opened_year,
                    },
                )
                if created:
                    grounds_created += 1
                else:
                    grounds_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Teams: {teams_created} created, {teams_updated} updated. "
                f"Grounds: {grounds_created} created, {grounds_updated} updated."
            )
        )

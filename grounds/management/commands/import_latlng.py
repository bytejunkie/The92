"""
Populate latitude/longitude on all Ground records using postcodes.io.

Uses the bulk endpoint to resolve all postcodes in a single HTTP request.
Safe to re-run — skips grounds that already have coordinates unless
--force is passed.

Usage:
    uv run python manage.py import_latlng
    uv run python manage.py import_latlng --force
"""

import json
import urllib.request

from django.core.management.base import BaseCommand

from grounds.models import Ground

BULK_URL = "https://api.postcodes.io/postcodes"


class Command(BaseCommand):
    help = "Resolve postcodes to lat/lng via postcodes.io and save to Ground."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-fetch even for grounds that already have coordinates.",
        )

    def handle(self, *args, **options):
        qs = Ground.objects.exclude(postcode="")
        if not options["force"]:
            qs = qs.filter(latitude__isnull=True)

        grounds = list(qs)
        if not grounds:
            self.stdout.write("All grounds already have coordinates. Use --force to refresh.")
            return

        self.stdout.write(f"Resolving {len(grounds)} postcodes via postcodes.io …")

        # postcodes.io bulk endpoint accepts up to 100 postcodes per request
        CHUNK = 100
        updated = 0
        failed = []

        for i in range(0, len(grounds), CHUNK):
            chunk = grounds[i : i + CHUNK]
            payload = json.dumps({"postcodes": [g.postcode for g in chunk]}).encode()
            req = urllib.request.Request(
                BULK_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())

            results_by_postcode = {}
            for item in data.get("result", []):
                if item.get("result"):
                    pc = item["query"].replace(" ", "").upper()
                    results_by_postcode[pc] = item["result"]

            for ground in chunk:
                normalised = ground.postcode.replace(" ", "").upper()
                result = results_by_postcode.get(normalised)
                if result:
                    ground.latitude = result["latitude"]
                    ground.longitude = result["longitude"]
                    ground.save(update_fields=["latitude", "longitude"])
                    updated += 1
                    self.stdout.write(f"  ✓ {ground.name} ({ground.postcode}) → {result['latitude']}, {result['longitude']}")
                else:
                    failed.append(ground)
                    self.stdout.write(
                        self.style.WARNING(f"  ✗ {ground.name} — postcode not found: {ground.postcode!r}")
                    )

        self.stdout.write(self.style.SUCCESS(f"\nDone. {updated} updated, {len(failed)} failed."))
        if failed:
            self.stdout.write("Failed grounds (check postcodes):")
            for g in failed:
                self.stdout.write(f"  {g.name}: {g.postcode!r}")

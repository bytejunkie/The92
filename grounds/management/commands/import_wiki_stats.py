"""
Populate capacity, opened_year, and address for Ground records via
the Wikipedia REST API → Wikidata entity API pipeline.

Flow per ground:
  1. GET https://en.wikipedia.org/api/rest_v1/page/summary/<name>
     → extract wikibase_item (Wikidata QID)
  2. GET https://www.wikidata.org/w/api.php?action=wbgetentities&ids=<QID>
     → claims P1083 (max capacity), P571 (inception date), P669 (street address)

Skips grounds that already have the field set unless --force.
Skips grounds where the Wikipedia lookup finds no matching article.

Usage:
    uv run python manage.py import_wiki_stats
    uv run python manage.py import_wiki_stats --force
    uv run python manage.py import_wiki_stats --slug vitality-stadium
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

from django.core.management.base import BaseCommand

from grounds.models import Ground

WIKI_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
HEADERS = {"User-Agent": "The92-GroundScraper/1.0 (contact@the92.co.uk)"}

# Wikidata property IDs
P_CAPACITY = "P1083"
P_INCEPTION = "P571"
P_STREET_ADDRESS = "P6375"
P_COORDINATES = "P625"

# Override map: ground slug → exact Wikipedia article title (when auto-match fails)
OVERRIDES = {
    "gtech-community-stadium": "Gtech Community Stadium",
    "dean-court": "Vitality Stadium",
    "selhurst-park": "Selhurst Park",
    # Ambiguous ground names that need an explicit disambiguated article title
    "recreation-ground": "Recreation Ground (Aldershot)",
    "victoria-park": "Victoria Park (Hartlepool)",
    "victoria-road": "Victoria Road (stadium)",
    "selhurst-park-groundshare": "Selhurst Park",
}


def _fetch(url, params=None):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def _get_wikidata_qid(ground_name, slug):
    title = OVERRIDES.get(slug) or ground_name
    title_encoded = urllib.parse.quote(title.replace(" ", "_"))
    try:
        data = _fetch(WIKI_SUMMARY.format(title_encoded))
        return data.get("wikibase_item"), data.get("title")
    except (urllib.error.HTTPError, urllib.error.URLError):
        return None, None


def _get_wikidata_claims(qid):
    data = _fetch(
        WIKIDATA_API,
        {
            "action": "wbgetentities",
            "ids": qid,
            "props": "claims",
            "format": "json",
        },
    )
    entity = data.get("entities", {}).get(qid, {})
    return entity.get("claims", {})


def _extract_capacity(claims):
    for snak in claims.get(P_CAPACITY, []):
        val = snak.get("mainsnak", {}).get("datavalue", {}).get("value")
        if val and "amount" in val:
            try:
                return int(float(val["amount"].lstrip("+")))
            except (ValueError, TypeError):
                pass
    return None


def _extract_year(claims):
    for snak in claims.get(P_INCEPTION, []):
        val = snak.get("mainsnak", {}).get("datavalue", {}).get("value")
        if val and "time" in val:
            # format: "+1910-00-00T00:00:00Z"
            try:
                return int(val["time"][1:5])
            except (ValueError, IndexError):
                pass
    return None


def _extract_address(claims):
    for snak in claims.get(P_STREET_ADDRESS, []):
        val = snak.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(val, dict):
            text = val.get("text") or val.get("value")
            if text:
                return text
        if isinstance(val, str) and val:
            return val
    return None


def _extract_coords(claims):
    """Return (latitude, longitude) from the Wikidata globe-coordinate claim."""
    for snak in claims.get(P_COORDINATES, []):
        val = snak.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(val, dict) and "latitude" in val and "longitude" in val:
            try:
                return round(float(val["latitude"]), 6), round(float(val["longitude"]), 6)
            except (ValueError, TypeError):
                pass
    return None, None


class Command(BaseCommand):
    help = "Populate capacity, opened_year, and address via Wikipedia → Wikidata."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Overwrite existing values.")
        parser.add_argument("--slug", help="Only update a single ground by slug.")

    def handle(self, *args, **options):
        force = options["force"]
        slug = options.get("slug")

        qs = Ground.objects.select_related("team").all()
        if slug:
            qs = qs.filter(slug=slug)

        updated = skipped = failed = 0

        for ground in qs:
            needs_update = force or not ground.capacity or not ground.opened_year
            if not needs_update:
                skipped += 1
                continue

            self.stdout.write(f"  → {ground.name} …", ending=" ")

            qid, wiki_title = _get_wikidata_qid(ground.name, ground.slug)
            if not qid:
                self.stdout.write(self.style.WARNING("no Wikipedia article found"))
                failed += 1
                time.sleep(0.3)
                continue

            try:
                claims = _get_wikidata_claims(qid)
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f"Wikidata error: {exc}"))
                failed += 1
                time.sleep(0.3)
                continue

            changes = []
            update_fields = []

            capacity = _extract_capacity(claims)
            if capacity and (force or not ground.capacity):
                ground.capacity = capacity
                changes.append(f"capacity={capacity:,}")
                update_fields.append("capacity")

            year = _extract_year(claims)
            if year and (force or not ground.opened_year):
                ground.opened_year = year
                changes.append(f"opened={year}")
                update_fields.append("opened_year")

            address = _extract_address(claims)
            if address and (force or not ground.address):
                ground.address = address
                changes.append("address set")
                update_fields.append("address")

            lat, lng = _extract_coords(claims)
            if lat is not None and (force or ground.latitude is None):
                ground.latitude = lat
                ground.longitude = lng
                changes.append(f"coords={lat},{lng}")
                update_fields += ["latitude", "longitude"]

            if update_fields:
                ground.save(update_fields=update_fields)
                self.stdout.write(self.style.SUCCESS(f"✓ {', '.join(changes)}"))
                updated += 1
            else:
                self.stdout.write("no new data")
                skipped += 1

            time.sleep(0.25)  # be polite to Wikipedia

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. {updated} updated, {skipped} skipped, {failed} failed."
            )
        )

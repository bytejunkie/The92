"""
Populate Ground.image from Wikipedia's lead/infobox photo.

Flow per ground:
  1. GET https://en.wikipedia.org/api/rest_v1/page/summary/<name>
     → originalimage.source (full-res lead photo)
  2. Download, resize to a sane max width, save to Ground.image

Skips grounds that already have an image unless --force.
Skips grounds where Wikipedia has no article or no lead image.

Usage:
    uv run python manage.py import_ground_images
    uv run python manage.py import_ground_images --force
    uv run python manage.py import_ground_images --slug vitality-stadium
"""

import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image

from grounds.models import Ground

WIKI_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
HEADERS = {"User-Agent": "The92-GroundScraper/1.0 (contact@the92.co.uk)"}
MAX_WIDTH = 1600

# Override map: ground slug → exact Wikipedia article title (when auto-match fails)
OVERRIDES = {
    "gtech-community-stadium": "Gtech Community Stadium",
    "dean-court": "Vitality Stadium",
    "selhurst-park": "Selhurst Park",
    "ashton-gate": "Ashton Gate (stadium)",
    "cherry-red-records-stadium": "Plough Lane",
    "county-ground": "County Ground (Swindon)",
    "faze-arena": "Hayes Lane",
    "hillsborough": "Hillsborough Stadium",
    "london-road": "Weston Homes Stadium",
    "memorial-stadium": "Memorial Stadium (Bristol)",
    "molineux": "Molineux Stadium",
    "st-andrews": "St Andrew's (stadium)",
    "st-james-park-exeter": "St James Park (Exeter)",
    "stamford-bridge": "Stamford Bridge (stadium)",
    "the-valley": "The Valley (stadium)",
}


def _fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def _get_summary(ground_name, slug):
    title = OVERRIDES.get(slug) or ground_name
    title_encoded = urllib.parse.quote(title.replace(" ", "_"))
    try:
        return _fetch_json(WIKI_SUMMARY.format(title_encoded))
    except (urllib.error.HTTPError, urllib.error.URLError):
        return None


def _download_and_resize(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read()

    img = Image.open(io.BytesIO(raw))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    if img.width > MAX_WIDTH:
        ratio = MAX_WIDTH / img.width
        img = img.resize((MAX_WIDTH, int(img.height * ratio)), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


class Command(BaseCommand):
    help = "Populate Ground.image from Wikipedia's lead photo."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Overwrite existing images.")
        parser.add_argument("--slug", help="Only update a single ground by slug.")

    def handle(self, *args, **options):
        force = options["force"]
        slug = options.get("slug")

        qs = Ground.objects.select_related("team").all()
        if slug:
            qs = qs.filter(slug=slug)

        updated = skipped = failed = 0

        for ground in qs:
            if ground.image and not force:
                skipped += 1
                continue

            self.stdout.write(f"  → {ground.name} …", ending=" ")

            summary = _get_summary(ground.name, ground.slug)
            if not summary:
                self.stdout.write(self.style.WARNING("no Wikipedia article found"))
                failed += 1
                time.sleep(0.3)
                continue

            image_info = summary.get("originalimage") or summary.get("thumbnail")
            if not image_info or not image_info.get("source"):
                self.stdout.write(self.style.WARNING("no lead image on article"))
                failed += 1
                time.sleep(0.3)
                continue

            try:
                content = _download_and_resize(image_info["source"])
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f"download error: {exc}"))
                failed += 1
                time.sleep(0.3)
                continue

            filename = f"{ground.slug}.jpg"
            ground.image.save(filename, ContentFile(content), save=True)
            self.stdout.write(self.style.SUCCESS(f"✓ saved ({len(content) // 1024} KB)"))
            updated += 1

            time.sleep(0.3)  # be polite to Wikipedia

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. {updated} updated, {skipped} skipped, {failed} failed."
            )
        )

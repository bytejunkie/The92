"""
Seed the non-92 clubs that appear in historical results (1993-94 onward) but
have no Team/Ground record yet. These clubs are NOT part of the current 92
(is_current_92=False), but they appear as opponents in real results, so they
must exist for the historical Match import to link both sides.

Creates a Team and its home Ground for each. Safe to re-run (get_or_create).

This seeds only the identity + home ground name + town (all high-confidence).
Ground stats (capacity, opened year, coordinates, address) are deliberately
left blank here and populated authoritatively from Wikidata afterwards.

Run order:
    uv run python manage.py seed_result_clubs
    uv run python manage.py import_wiki_stats      # fills capacity/opened/coords
    uv run python manage.py import_csv_fixtures data/football-data/historical_results.csv

The ground names below are chosen to match Wikipedia article titles; ambiguous
ones (Victoria Park, Recreation Ground, Victoria Road, Selhurst Park) have slug
overrides in import_wiki_stats.OVERRIDES.
"""

from django.core.management.base import BaseCommand

from grounds.models import Ground, Team

L = Team.LeagueLevel

# name, league_level, colour, ground, town, note
CLUBS = [
    ("Scunthorpe United", L.NON_LEAGUE, "#8A1538", "Glanford Park", "Scunthorpe", ""),
    ("Southend United", L.NON_LEAGUE, "#1D3FBE", "Roots Hall", "Southend-on-Sea", ""),
    ("Hartlepool United", L.NON_LEAGUE, "#004B9B", "Victoria Park", "Hartlepool", ""),
    ("Bury", L.OTHER, "#1D3FBE", "Gigg Lane", "Bury",
     "Expelled from EFL 2019; Gigg Lane now Bury FC (reformed)"),
    ("Torquay United", L.NON_LEAGUE, "#FFD200", "Plainmoor", "Torquay", ""),
    ("Darlington", L.NON_LEAGUE, "#000000", "Blackwell Meadows", "Darlington",
     "Played at Feethams during 1990s results era"),
    ("Macclesfield Town", L.OTHER, "#1D4E9B", "Moss Rose", "Macclesfield",
     "Wound up 2020; Moss Rose now Macclesfield FC"),
    ("Yeovil Town", L.NON_LEAGUE, "#006A4E", "Huish Park", "Yeovil", ""),
    ("Wimbledon FC", L.OTHER, "#002F87", "Selhurst Park (groundshare)", "London",
     "ORIGINAL Wimbledon FC (Plough Lane to 1991, Selhurst share to 2003) -> MK Dons 2004. NOT AFC Wimbledon."),
    ("Dagenham & Redbridge", L.NON_LEAGUE, "#C8102E", "Victoria Road", "Dagenham",
     "football-data name: 'Dag and Red'"),
    ("Scarborough", L.OTHER, "#C8102E", "McCain Stadium", "Scarborough",
     "Defunct 2007; successor Scarborough Athletic"),
    ("Kidderminster Harriers", L.NON_LEAGUE, "#C8102E", "Aggborough", "Kidderminster", ""),
    ("Rushden & Diamonds", L.OTHER, "#002F87", "Nene Park", "Irthlingborough",
     "Defunct 2011; football-data name: 'Rushden & D'"),
    ("Aldershot Town", L.NON_LEAGUE, "#C8102E", "Recreation Ground", "Aldershot",
     "Reformed 1992 after Aldershot FC folded"),
    ("Halifax Town", L.OTHER, "#1D3FBE", "The Shay", "Halifax",
     "Wound up 2008; The Shay now FC Halifax Town"),
    ("Sutton United", L.NON_LEAGUE, "#FFB81C", "Gander Green Lane", "Sutton", ""),
]


class Command(BaseCommand):
    help = "Seed non-92 clubs (Team + Ground) that appear in historical results."

    def handle(self, *args, **options):
        teams_created = grounds_created = 0
        for name, league, colour, ground_name, town, note in CLUBS:
            team, t_made = Team.objects.get_or_create(
                name=name,
                defaults={
                    "league_level": league,
                    "primary_colour": colour,
                    "is_current_92": False,
                },
            )
            if t_made:
                teams_created += 1

            _, g_made = Ground.objects.get_or_create(
                team=team,
                defaults={"name": ground_name, "town_or_city": town},
            )
            if g_made:
                grounds_created += 1

            flag = "+" if (t_made or g_made) else "="
            suffix = f"  ({note})" if note else ""
            self.stdout.write(f"  {flag} {name} — {ground_name}, {town}{suffix}")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. {teams_created} teams and {grounds_created} grounds created. "
            f"Run import_wiki_stats next to populate ground stats."
        ))

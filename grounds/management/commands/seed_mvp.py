from django.core.management.base import BaseCommand

from grounds.models import Ground, Team


class Command(BaseCommand):
    help = "Seed a small set of teams and grounds for local MVP design work."

    def handle(self, *args, **options):
        rows = [
            {
                "team": "Leeds United",
                "league": Team.LeagueLevel.CHAMPIONSHIP,
                "ground": "Elland Road",
                "city": "Leeds",
                "address": "Elland Road, Beeston, Leeds",
                "postcode": "LS11 0ES",
                "capacity": 37792,
                "opened_year": 1897,
                "away_allocation": 3000,
                "colour": "#182740",
                "parking": (
                    "Use official matchday car parks where available, or pre-book "
                    "nearby private parking. Expect heavy traffic after full time."
                ),
                "drinking": (
                    "Away-friendly pubs vary by fixture. Check recent supporter "
                    "notes and official club guidance before travelling."
                ),
                "transport": (
                    "Leeds station is the main rail option, then bus or taxi. "
                    "Allow 20-30 minutes on matchday."
                ),
                "entrance": (
                    "Away supporters are usually directed to the West Stand area."
                ),
                "tip": (
                    "Arrive early for the walk-up and photos outside the East Stand."
                ),
            },
            {
                "team": "Newcastle United",
                "league": Team.LeagueLevel.PREMIER_LEAGUE,
                "ground": "St James' Park",
                "city": "Newcastle upon Tyne",
                "address": "Barrack Road, Newcastle upon Tyne",
                "postcode": "NE1 4ST",
                "capacity": 52305,
                "opened_year": 1892,
                "away_allocation": 3200,
                "colour": "#101820",
                "parking": (
                    "City-centre parking is limited. Public transport is usually "
                    "the better option."
                ),
                "drinking": (
                    "Central Newcastle has plenty of options, but away-fan "
                    "policies can vary by fixture."
                ),
                "transport": "The ground is walkable from Newcastle station.",
                "entrance": "Away seating is high in the Leazes End.",
                "tip": "The city-centre approach makes this a strong first away day.",
            },
            {
                "team": "Plymouth Argyle",
                "league": Team.LeagueLevel.CHAMPIONSHIP,
                "ground": "Home Park",
                "city": "Plymouth",
                "address": "Home Park, Plymouth",
                "postcode": "PL2 3DQ",
                "capacity": 17900,
                "opened_year": 1893,
                "away_allocation": 1700,
                "colour": "#19704B",
                "parking": (
                    "Park-and-ride and city parking are often easier than driving "
                    "right up to the ground."
                ),
                "drinking": (
                    "Use recent supporter notes for away-friendly pubs near the "
                    "station and Barbican."
                ),
                "transport": "Plymouth station is roughly a 25-minute walk.",
                "entrance": "Away fans are commonly housed in the Barn Park End.",
                "tip": "A long-distance tick for many users, so travel notes matter.",
            },
            {
                "team": "Luton Town",
                "league": Team.LeagueLevel.CHAMPIONSHIP,
                "ground": "Kenilworth Road",
                "city": "Luton",
                "address": "1 Maple Road, Luton",
                "postcode": "LU4 8AW",
                "capacity": 12056,
                "opened_year": 1905,
                "away_allocation": 1000,
                "colour": "#D6363E",
                "parking": (
                    "Residential streets are busy and restricted. Use town-centre "
                    "parking and walk."
                ),
                "drinking": (
                    "Town-centre options are the practical starting point; check "
                    "fixture-specific notes."
                ),
                "transport": "Luton station is around a 20-minute walk.",
                "entrance": (
                    "The away entrance is part of the ground's distinctive "
                    "residential approach."
                ),
                "tip": "A classic compact ground with a memorable away entrance.",
            },
        ]

        created = 0
        for row in rows:
            team, _ = Team.objects.update_or_create(
                name=row["team"],
                defaults={
                    "league_level": row["league"],
                    "is_current_92": True,
                    "primary_colour": row["colour"],
                },
            )
            _, was_created = Ground.objects.update_or_create(
                name=row["ground"],
                defaults={
                    "team": team,
                    "town_or_city": row["city"],
                    "address": row["address"],
                    "postcode": row["postcode"],
                    "capacity": row["capacity"],
                    "opened_year": row["opened_year"],
                    "away_allocation": row["away_allocation"],
                    "parking_notes": row["parking"],
                    "drinking_notes": row["drinking"],
                    "transport_notes": row["transport"],
                    "away_entrance": row["entrance"],
                    "first_visit_tip": row["tip"],
                },
            )
            created += int(was_created)

        self.stdout.write(self.style.SUCCESS(f"Seeded MVP grounds ({created} new)."))

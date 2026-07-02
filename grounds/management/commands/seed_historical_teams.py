"""
Add notable non-92 teams so the favourite_team dropdown on signup
has meaningful options beyond the current 92.

Covers: national sides, Scottish Premiership, relegated/historical
English clubs with a large supporter base.

Safe to re-run — uses get_or_create throughout.
"""

from django.core.management.base import BaseCommand

from grounds.models import Team


class Command(BaseCommand):
    help = "Seed historical and non-92 teams for the favourite_team dropdown."

    TEAMS = [
        # National sides
        {"name": "England", "league": Team.LeagueLevel.INTERNATIONAL, "colour": "#FFFFFF"},
        {"name": "Scotland", "league": Team.LeagueLevel.INTERNATIONAL, "colour": "#003580"},
        {"name": "Wales", "league": Team.LeagueLevel.INTERNATIONAL, "colour": "#C8102E"},
        {"name": "Northern Ireland", "league": Team.LeagueLevel.INTERNATIONAL, "colour": "#003580"},
        {"name": "Republic of Ireland", "league": Team.LeagueLevel.INTERNATIONAL, "colour": "#169B62"},

        # Scottish Premiership (top 6 by support)
        {"name": "Celtic", "league": Team.LeagueLevel.SCOTLAND, "colour": "#16A34A"},
        {"name": "Rangers", "league": Team.LeagueLevel.SCOTLAND, "colour": "#003580"},
        {"name": "Aberdeen", "league": Team.LeagueLevel.SCOTLAND, "colour": "#C8102E"},
        {"name": "Heart of Midlothian", "league": Team.LeagueLevel.SCOTLAND, "colour": "#800020"},
        {"name": "Hibernian", "league": Team.LeagueLevel.SCOTLAND, "colour": "#005B21"},
        {"name": "Dundee United", "league": Team.LeagueLevel.SCOTLAND, "colour": "#F5821F"},
        {"name": "Motherwell", "league": Team.LeagueLevel.SCOTLAND, "colour": "#C8102E"},
        {"name": "St Mirren", "league": Team.LeagueLevel.SCOTLAND, "colour": "#000000"},

        # Welsh Premier League
        {"name": "Cardiff City", "league": Team.LeagueLevel.WALES, "colour": "#0070B8"},
        {"name": "Swansea City", "league": Team.LeagueLevel.WALES, "colour": "#FFFFFF"},
        {"name": "Newport County", "league": Team.LeagueLevel.WALES, "colour": "#F5821F"},

        # Well-supported English clubs currently outside the 92
        {"name": "AFC Fylde", "league": Team.LeagueLevel.NON_LEAGUE, "colour": "#FFFFFF"},
        {"name": "Altrincham", "league": Team.LeagueLevel.NON_LEAGUE, "colour": "#C8102E"},
        {"name": "Boston United", "league": Team.LeagueLevel.NON_LEAGUE, "colour": "#FFCD00"},
        {"name": "Chester FC", "league": Team.LeagueLevel.NON_LEAGUE, "colour": "#000000"},
        {"name": "FC United of Manchester", "league": Team.LeagueLevel.NON_LEAGUE, "colour": "#C8102E"},
        {"name": "Gateshead", "league": Team.LeagueLevel.NON_LEAGUE, "colour": "#000000"},
        {"name": "Hereford FC", "league": Team.LeagueLevel.NON_LEAGUE, "colour": "#FFFFFF"},
        {"name": "King's Lynn Town", "league": Team.LeagueLevel.NON_LEAGUE, "colour": "#FFCD00"},
        {"name": "Maidstone United", "league": Team.LeagueLevel.NON_LEAGUE, "colour": "#FFCD00"},
        {"name": "Solihull Moors", "league": Team.LeagueLevel.NON_LEAGUE, "colour": "#FFCD00"},
        {"name": "Southport", "league": Team.LeagueLevel.NON_LEAGUE, "colour": "#F5821F"},
        {"name": "Spennymoor Town", "league": Team.LeagueLevel.NON_LEAGUE, "colour": "#000000"},
        {"name": "Tamworth", "league": Team.LeagueLevel.NON_LEAGUE, "colour": "#C8102E"},
        {"name": "Woking", "league": Team.LeagueLevel.NON_LEAGUE, "colour": "#C8102E"},
        {"name": "Wrexham", "league": Team.LeagueLevel.WALES, "colour": "#C8102E"},
    ]

    def handle(self, *args, **options):
        created_count = 0
        for t in self.TEAMS:
            _, created = Team.objects.get_or_create(
                name=t["name"],
                defaults={
                    "league_level": t["league"],
                    "primary_colour": t["colour"],
                    "is_current_92": False,
                },
            )
            if created:
                created_count += 1
                self.stdout.write(f"  + {t['name']} ({t['league']})")
            else:
                self.stdout.write(f"  = {t['name']} (already exists)")

        self.stdout.write(self.style.SUCCESS(f"\nDone. {created_count} new teams created."))

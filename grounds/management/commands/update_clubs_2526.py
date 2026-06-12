"""
Apply two rounds of promotion/relegation (end of 24/25 and end of 25/26)
to bring the club database up to the 2026-27 pre-season state.

Changes applied are NET movements — teams that went up then back down
(e.g. Cambridge United, Port Vale, Burnley, Cardiff City, Ipswich Town)
end up unchanged and are not touched.
"""

from django.core.management.base import BaseCommand

from grounds.models import Ground, Team


class Command(BaseCommand):
    help = "Update league levels to reflect 2026-27 pre-season state."

    def handle(self, *args, **options):
        self._update_levels()
        self._deactivate_relegated()
        self._create_promoted()
        self.stdout.write(self.style.SUCCESS("Done — clubs updated to 2026-27."))

    # ------------------------------------------------------------------
    def _update_levels(self):
        moves = [
            # PL → Championship
            ("Southampton",              "championship"),
            ("West Ham United",          "championship"),
            ("Wolverhampton Wanderers",  "championship"),
            # PL → League One
            ("Leicester City",           "league-one"),
            # Championship → PL
            ("Coventry City",            "premier-league"),
            ("Hull City",                "premier-league"),
            ("Leeds United",             "premier-league"),
            ("Sunderland",               "premier-league"),
            # Championship → League One
            ("Luton Town",               "league-one"),
            ("Oxford United",            "league-one"),
            ("Plymouth Argyle",          "league-one"),
            ("Sheffield Wednesday",      "league-one"),
            # League One → Championship
            ("Birmingham City",          "championship"),
            ("Bolton Wanderers",         "championship"),
            ("Charlton Athletic",        "championship"),
            ("Lincoln City",             "championship"),
            ("Wrexham",                  "championship"),
            # League One → League Two
            ("Bristol Rovers",           "league-two"),
            ("Crawley Town",             "league-two"),
            ("Exeter City",              "league-two"),
            ("Northampton Town",         "league-two"),
            ("Rotherham United",         "league-two"),
            ("Shrewsbury Town",          "league-two"),
            # League Two → League One
            ("AFC Wimbledon",            "league-one"),
            ("Bradford City",            "league-one"),
            ("Doncaster Rovers",         "league-one"),
            ("MK Dons",                  "league-one"),
            ("Notts County",             "league-one"),
        ]

        for name, new_level in moves:
            updated = Team.objects.filter(name=name).update(league_level=new_level)
            if updated:
                self.stdout.write(f"  {name} → {new_level}")
            else:
                self.stdout.write(
                    self.style.WARNING(f"  NOT FOUND: {name}")
                )

    def _deactivate_relegated(self):
        relegated = [
            "Carlisle United",
            "Forest Green Rovers",
            "Morecambe",
            "Harrogate Town",
            "Barrow",
        ]
        for name in relegated:
            updated = Team.objects.filter(name=name).update(
                is_current_92=False,
                league_level=Team.LeagueLevel.NON_LEAGUE,
            )
            if updated:
                self.stdout.write(f"  {name} → non-league (deactivated)")
            else:
                self.stdout.write(self.style.WARNING(f"  NOT FOUND: {name}"))

    def _create_promoted(self):
        """
        Five clubs newly in the 92 for 26-27.
        Barnet + Oldham → League Two.
        Bromley, York City, Rochdale → League Two.
        (Bromley promoted NL→L2 in 25/26 then L2→L1 in 25/26; net state = L1.)
        """
        new_clubs = [
            {
                "name": "Barnet",
                "league": Team.LeagueLevel.LEAGUE_TWO,
                "colour": "#F5A623",
                "ground": "The Hive London",
                "city": "Harrow",
                "postcode": "HA3 5BN",
                "capacity": 6023,
                "opened": 2013,
            },
            {
                "name": "Bromley",
                "league": Team.LeagueLevel.LEAGUE_ONE,
                "colour": "#1C4B8A",
                "ground": "FAZE Arena",
                "city": "Bromley",
                "postcode": "BR2 9EF",
                "capacity": 5000,
                "opened": 1892,
            },
            {
                "name": "Oldham Athletic",
                "league": Team.LeagueLevel.LEAGUE_TWO,
                "colour": "#0057A8",
                "ground": "Boundary Park",
                "city": "Oldham",
                "postcode": "OL1 2PA",
                "capacity": 10638,
                "opened": 1906,
            },
            {
                "name": "York City",
                "league": Team.LeagueLevel.LEAGUE_TWO,
                "colour": "#C41E3A",
                "ground": "LNER Community Stadium",
                "city": "York",
                "postcode": "YO32 9AF",
                "capacity": 8168,
                "opened": 2020,
            },
            {
                "name": "Rochdale",
                "league": Team.LeagueLevel.LEAGUE_TWO,
                "colour": "#003594",
                "ground": "Crown Oil Arena",
                "city": "Rochdale",
                "postcode": "OL11 5DR",
                "capacity": 10249,
                "opened": 1920,
            },
        ]

        for c in new_clubs:
            team, created = Team.objects.get_or_create(
                name=c["name"],
                defaults={
                    "league_level": c["league"],
                    "primary_colour": c["colour"],
                    "is_current_92": True,
                },
            )
            if not created:
                team.league_level = c["league"]
                team.primary_colour = c["colour"]
                team.is_current_92 = True
                team.save()

            Ground.objects.get_or_create(
                name=c["ground"],
                defaults={
                    "team": team,
                    "town_or_city": c["city"],
                    "postcode": c["postcode"],
                    "capacity": c["capacity"],
                    "opened_year": c["opened"],
                },
            )
            self.stdout.write(
                f"  {'Created' if created else 'Updated'} {c['name']} "
                f"({c['league']}) — {c['ground']}"
            )

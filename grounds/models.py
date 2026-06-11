from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Team(models.Model):
    class LeagueLevel(models.TextChoices):
        PREMIER_LEAGUE = "premier-league", "Premier League"
        CHAMPIONSHIP = "championship", "Championship"
        LEAGUE_ONE = "league-one", "League One"
        LEAGUE_TWO = "league-two", "League Two"
        NON_LEAGUE = "non-league", "Non-League"
        SCOTLAND = "scotland", "Scotland"
        WALES = "wales", "Wales"
        INTERNATIONAL = "international", "International"
        OTHER = "other", "Other"

    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    league_level = models.CharField(
        max_length=40,
        choices=LeagueLevel.choices,
        default=LeagueLevel.OTHER,
    )
    is_current_92 = models.BooleanField(default=False)
    logo = models.ImageField(upload_to="team-logos/", blank=True)
    primary_colour = models.CharField(max_length=7, default="#19704B")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Ground(models.Model):
    name = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    team = models.OneToOneField(
        Team,
        on_delete=models.PROTECT,
        related_name="ground",
        null=True,
        blank=True,
    )
    town_or_city = models.CharField(max_length=120)
    address = models.TextField(blank=True)
    postcode = models.CharField(max_length=12, blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    opened_year = models.PositiveIntegerField(null=True, blank=True)
    image = models.ImageField(upload_to="grounds/", blank=True)
    away_allocation = models.PositiveIntegerField(null=True, blank=True)
    away_entrance = models.CharField(max_length=160, blank=True)
    parking_notes = models.TextField(blank=True)
    drinking_notes = models.TextField(blank=True)
    transport_notes = models.TextField(blank=True)
    first_visit_tip = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("grounds:detail", kwargs={"slug": self.slug})

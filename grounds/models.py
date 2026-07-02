from django.conf import settings
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
    # Crests are committed static assets by slug (theme/img/crests/<slug>.png),
    # resolved via the {% crest_url %} tag — not a DB/media field.
    shirt = models.ImageField(upload_to="team-shirts/", blank=True)
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
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    away_allocation = models.PositiveIntegerField(null=True, blank=True)
    away_end = models.CharField(max_length=200, blank=True)
    away_entrance = models.CharField(max_length=160, blank=True)
    parking_notes = models.TextField(blank=True)
    drinking_notes = models.TextField(blank=True)
    transport_notes = models.TextField(blank=True)
    first_visit_tip = models.TextField(blank=True)
    info_updated_at = models.DateField(null=True, blank=True)
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


class Match(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Scheduled"
        TIMED = "TIMED", "Timed"
        IN_PLAY = "IN_PLAY", "In Play"
        PAUSED = "PAUSED", "Paused"
        FINISHED = "FINISHED", "Finished"
        POSTPONED = "POSTPONED", "Postponed"
        CANCELLED = "CANCELLED", "Cancelled"
        SUSPENDED = "SUSPENDED", "Suspended"

    external_id = models.IntegerField(unique=True)
    home_team = models.ForeignKey(
        Team, on_delete=models.PROTECT, related_name="home_matches", null=True, blank=True
    )
    away_team = models.ForeignKey(
        Team, on_delete=models.PROTECT, related_name="away_matches", null=True, blank=True
    )
    ground = models.ForeignKey(
        Ground, on_delete=models.SET_NULL, null=True, blank=True, related_name="matches"
    )
    kickoff = models.DateTimeField()
    competition = models.CharField(max_length=10, default="PL")
    matchday = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    home_score = models.PositiveIntegerField(null=True, blank=True)
    away_score = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["kickoff"]

    def __str__(self):
        return f"{self.home_team} v {self.away_team} ({self.kickoff:%Y-%m-%d})"

    COMPETITION_NAMES = {
        "PL": "Premier League",
        "ELC": "Championship",
        "EL1": "League One",
        "EL2": "League Two",
    }

    @property
    def is_today(self):
        from django.utils import timezone
        return self.kickoff.date() == timezone.localdate()

    @property
    def competition_name(self):
        return self.COMPETITION_NAMES.get(self.competition, self.competition)

    @property
    def score_display(self):
        if self.home_score is not None and self.away_score is not None:
            return f"{self.home_score}–{self.away_score}"
        return "v"


class GroundSuggestion(models.Model):
    """User-submitted suggestion to update or add a specific field on a Ground record."""

    class FieldName(models.TextChoices):
        IMAGE = "image", "Ground photo"
        PARKING = "parking_notes", "Where to park"
        DRINKING = "drinking_notes", "Where to drink"
        TRANSPORT = "transport_notes", "Getting there"
        AWAY_END = "away_end", "Away end"
        AWAY_ENTRANCE = "away_entrance", "Away entrance"
        AWAY_ALLOCATION = "away_allocation", "Away allocation"
        FIRST_VISIT_TIP = "first_visit_tip", "First visit tip"
        CAPACITY = "capacity", "Capacity"
        OPENED_YEAR = "opened_year", "Opened year"
        ADDRESS = "address", "Address"

    IMAGE_FIELDS = {"image"}
    INTEGER_FIELDS = {"capacity", "opened_year", "away_allocation"}

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    ground = models.ForeignKey(Ground, on_delete=models.CASCADE, related_name="suggestions")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="suggestions"
    )
    field_name = models.CharField(max_length=30, choices=FieldName.choices)
    proposed_value = models.TextField(max_length=500, blank=True)
    proposed_image = models.ImageField(upload_to="suggestions/", blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_suggestions",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} → {self.ground} [{self.field_name}] ({self.status})"

    def apply(self, reviewer):
        """Write the proposed value (or image) to the ground field and mark approved."""
        from django.utils import timezone
        field = self.field_name

        if field in self.IMAGE_FIELDS:
            if not self.proposed_image:
                return False
            self.ground.image.save(
                self.proposed_image.name, self.proposed_image.file, save=False
            )
        else:
            value = self.proposed_value
            if field in self.INTEGER_FIELDS:
                try:
                    value = int(value)
                except ValueError:
                    return False
            setattr(self.ground, field, value)

        self.ground.info_updated_at = timezone.now().date()
        self.ground.save()
        self.status = self.Status.APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_by", "reviewed_at"])
        return True


class GroundTip(models.Model):
    """Short community tip shown in the away fan guide (max 280 chars)."""

    class Category(models.TextChoices):
        PARKING = "parking", "Where to park"
        PUBS = "pubs", "Where to drink"
        TRANSPORT = "transport", "Getting there"
        GENERAL = "general", "General tip"

    ground = models.ForeignKey(Ground, on_delete=models.CASCADE, related_name="tips")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tips"
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    body = models.CharField(max_length=280)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} tip on {self.ground} ({self.category})"


class Visit(models.Model):
    class VisitType(models.TextChoices):
        VISITED = "visited", "Visited"
        WANT_TO_GO = "want-to-go", "Want to go"
        HISTORIC = "historic", "Historic"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="visits",
    )
    ground = models.ForeignKey(
        Ground,
        on_delete=models.CASCADE,
        related_name="visits",
    )
    visit_type = models.CharField(
        max_length=20,
        choices=VisitType.choices,
        default=VisitType.VISITED,
    )
    match = models.ForeignKey(
        "Match", on_delete=models.SET_NULL, null=True, blank=True, related_name="visits"
    )
    visited_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "ground"],
                condition=models.Q(visit_type="want-to-go"),
                name="unique_want_to_go_per_user_ground",
            )
        ]

    def __str__(self):
        return f"{self.user} → {self.ground} ({self.visit_type})"


class Event(models.Model):
    """Lightweight domain-event telemetry (sign-ups, claims, follows, …) for
    day-by-day monitoring. Written — alongside a structured log line — by
    grounds.telemetry.log_event. Never blocks the user action it records."""

    class Type(models.TextChoices):
        REGISTER = "register", "Sign-up"
        CLAIM = "claim", "Ground claimed"
        WANT_TO_GO = "want_to_go", "Added to want-to-go"
        HISTORIC = "historic", "Historic visit logged"
        FOLLOW = "follow", "Followed a user"
        CHECKIN = "checkin", "Matchday check-in"

    event_type = models.CharField(max_length=20, choices=Type.choices)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="events",
    )
    ground = models.ForeignKey(
        "Ground", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="events",
    )
    context = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["event_type", "created_at"])]

    def __str__(self):
        return f"{self.get_event_type_display()} · {self.created_at:%Y-%m-%d %H:%M}"

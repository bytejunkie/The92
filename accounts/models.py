from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

BLOCKED_USERNAME_TERMS = {
    "arse",
    "bastard",
    "bellend",
    "bitch",
    "bollock",
    "bollocks",
    "bugger",
    "cunt",
    "dick",
    "fuck",
    "knob",
    "piss",
    "prick",
    "shit",
    "slut",
    "twat",
    "wank",
}


def validate_username_comedy(value):
    normalized = "".join(ch.lower() for ch in value if ch.isalnum())
    for blocked in BLOCKED_USERNAME_TERMS:
        if blocked in normalized:
            raise ValidationError(
                _("Comedy is allowed, but keep usernames swear-free."),
                code="profane_username",
            )


class User(AbstractUser):
    username = models.CharField(
        max_length=30,
        unique=True,
        help_text=_("Comedy is allowed, but no swears."),
        validators=[validate_username_comedy],
        error_messages={"unique": _("That username is already taken.")},
    )
    email = models.EmailField(unique=True)
    birthday = models.DateField(
        help_text=_("Some future features may be age restricted.")
    )
    favourite_team = models.ForeignKey(
        "grounds.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supporters",
    )

    REQUIRED_FIELDS = ["email", "birthday"]

    def clean(self):
        super().clean()
        if self.username:
            validate_username_comedy(self.username)


class Follow(models.Model):
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="following",
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="followers",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("follower", "following")]

    def __str__(self):
        return f"{self.follower} → {self.following}"

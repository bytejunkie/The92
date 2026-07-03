"""Post-migrate hooks that pin environment-specific database state.

The Site domain and the SocialApp→Site links live in the database, so a data
dump/`loaddata` (e.g. reseeding prod from a local export) silently reverts them
and breaks Google sign-in with ``SocialApp.DoesNotExist``. Re-asserting them on
every ``migrate`` — which runs on every deploy — keeps them correct no matter
what's in the database, without hardcoding the domain (it comes from settings).
"""
from django.conf import settings
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def sync_site_and_social_apps(sender, **kwargs):
    # post_migrate fires once per app; act only when our own app's fires so this
    # runs exactly once per `migrate`.
    if sender is None or sender.name != "accounts":
        return

    domain = getattr(settings, "SITE_DOMAIN", "")
    if not domain:
        # Unconfigured (local/dev/test/CI) — leave the database untouched.
        return

    from django.contrib.sites.models import Site

    site, _ = Site.objects.update_or_create(
        pk=settings.SITE_ID,
        defaults={"domain": domain, "name": getattr(settings, "SITE_NAME", domain)},
    )

    try:
        from allauth.socialaccount.models import SocialApp
    except ImportError:
        return

    # Ensure every configured social app is usable on this site.
    for app in SocialApp.objects.exclude(sites=site):
        app.sites.add(site)

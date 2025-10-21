from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.sites.models import Site

try:
    from allauth.socialaccount.models import SocialApp
except Exception:  # pragma: no cover
    SocialApp = None

try:
    from auth_payments.settings_config import OAUTH_PROVIDERS
except Exception:  # pragma: no cover
    OAUTH_PROVIDERS = {}


class Command(BaseCommand):
    help = (
        "Fix Google OAuth configuration in the database: update the Django Site "
        "domain to match local development, ensure the Google SocialApp exists "
        "and is associated with the current Site, and print the exact redirect URIs "
        "to add in Google Cloud Console."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--domain",
            type=str,
            default="localhost:8000",
            help="Domain to set for the current Site (e.g., localhost:8000)",
        )
        parser.add_argument(
            "--print127",
            action="store_true",
            help="Also print 127.0.0.1 redirect URIs",
        )

    def handle(self, *args, **options):
        domain = options.get("domain") or "localhost:8000"
        print127 = bool(options.get("print127"))

        # Verify required apps
        installed = set(getattr(settings, "INSTALLED_APPS", []))
        if "django.contrib.sites" not in installed:
            self.stderr.write(self.style.ERROR("django.contrib.sites is not installed."))
            return
        if "allauth" not in installed or "allauth.socialaccount" not in installed:
            self.stderr.write(self.style.ERROR("django-allauth is not installed."))
            return
        if SocialApp is None:
            self.stderr.write(self.style.ERROR("Could not import allauth SocialApp model."))
            return

        # Resolve protocol
        protocol = getattr(settings, "ACCOUNT_DEFAULT_HTTP_PROTOCOL", "http")
        if protocol not in ("http", "https"):
            protocol = "http"

        # Update current Site
        site_id = getattr(settings, "SITE_ID", 1)
        site = Site.objects.filter(pk=site_id).first() or Site.objects.first()
        if not site:
            site = Site.objects.create(domain=domain, name=domain)
            self.stdout.write(self.style.WARNING(f"Created default Site with domain {domain}"))
        else:
            site.domain = domain
            site.name = domain
            site.save()
            self.stdout.write(self.style.SUCCESS(f"Updated Site (id={site.id}) domain to {domain}"))

        # Ensure Google SocialApp exists with credentials from env/config
        google_cfg = OAUTH_PROVIDERS.get("google", {})
        client_id = google_cfg.get("client_id") or (
            settings.environ.get("GOOGLE_OAUTH_CLIENT_ID") if hasattr(settings, "environ") else None
        )
        client_secret = google_cfg.get("client_secret") or (
            settings.environ.get("GOOGLE_OAUTH_CLIENT_SECRET") if hasattr(settings, "environ") else None
        )

        # Create or fetch the SocialApp for Google
        social_app, created = SocialApp.objects.get_or_create(
            provider="google",
            defaults={
                "name": "Google OAuth",
                "client_id": client_id or "",
                "secret": client_secret or "",
            },
        )

        # Update credentials if provided and different
        updated = False
        if client_id and social_app.client_id != client_id:
            social_app.client_id = client_id
            updated = True
        if client_secret and social_app.secret != client_secret:
            social_app.secret = client_secret
            updated = True
        if updated:
            social_app.save()
            self.stdout.write(self.style.SUCCESS("Updated Google SocialApp credentials."))

        # Associate Site
        if not social_app.sites.filter(id=site.id).exists():
            social_app.sites.add(site)
            self.stdout.write(self.style.SUCCESS(f"Associated Google SocialApp with site {site.domain}"))

        # Print redirect URIs and origins for Google Cloud
        redirect_uri = f"{protocol}://{domain}/accounts/google/login/callback/"
        origins = [f"{protocol}://{domain}"]
        self.stdout.write(self.style.NOTICE("\nAdd the following in Google Cloud → OAuth client:"))
        self.stdout.write(self.style.SUCCESS(f"Authorized redirect URI: {redirect_uri}"))
        self.stdout.write(self.style.SUCCESS(f"Authorized JavaScript origin: {origins[0]}"))

        if print127:
            alt_redirect = f"{protocol}://127.0.0.1:8000/accounts/google/login/callback/"
            alt_origin = f"{protocol}://127.0.0.1:8000"
            self.stdout.write(self.style.WARNING("\nOptional local alternatives:"))
            self.stdout.write(self.style.WARNING(f"Authorized redirect URI: {alt_redirect}"))
            self.stdout.write(self.style.WARNING(f"Authorized JavaScript origin: {alt_origin}"))
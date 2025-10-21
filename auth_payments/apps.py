from django.apps import AppConfig


class AuthPaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'auth_payments'
    
    def ready(self):
        """Initialize auth_payments app and auto-create SocialApp entries"""
        # Import inside to avoid AppRegistryNotReady during startup
        try:
            self._create_social_apps()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"AuthPayments ready() error: {e}")
    
    def _create_social_apps(self):
        """Auto-create SocialApp entries from OAuth provider configuration"""
        from django.conf import settings
        try:
            from allauth.socialaccount.models import SocialApp
            from django.contrib.sites.models import Site
            from .settings_config import OAUTH_PROVIDERS
            import logging
            
            logger = logging.getLogger(__name__)
            
            # Only run if allauth and sites app enabled
            installed = set(getattr(settings, 'INSTALLED_APPS', []))
            if 'allauth' not in installed or 'allauth.socialaccount' not in installed or 'django.contrib.sites' not in installed:
                return
            
            # Get the current site (SITE_ID must be set)
            try:
                site = Site.objects.get_current()
            except Exception:
                site = Site.objects.filter(pk=getattr(settings, 'SITE_ID', 1)).first() or Site.objects.first()
                if not site:
                    # Create default site if none exists
                    site = Site.objects.create(domain='example.com', name='example.com')
            
            for provider_id, config in OAUTH_PROVIDERS.items():
                if not config.get('enabled', False):
                    continue
                client_id = config.get('client_id', '')
                client_secret = config.get('client_secret', '')
                if not client_id or not client_secret:
                    # Skip providers without credentials
                    continue
                
                social_app, created = SocialApp.objects.get_or_create(
                    provider=provider_id,
                    defaults={
                        'name': f'{provider_id.title()} OAuth',
                        'client_id': client_id,
                        'secret': client_secret,
                    }
                )
                
                # Update credentials if changed
                updated = False
                if social_app.client_id != client_id:
                    social_app.client_id = client_id
                    updated = True
                if social_app.secret != client_secret:
                    social_app.secret = client_secret
                    updated = True
                if updated:
                    social_app.save()
                    logger.info(f"Updated SocialApp credentials for {provider_id}")
                
                # Ensure site association
                if not social_app.sites.filter(id=site.id).exists():
                    social_app.sites.add(site)
                    logger.info(f"Associated {provider_id} SocialApp with site {site.domain}")
                
                if created:
                    logger.info(f"Created SocialApp for provider {provider_id}")
        except ImportError:
            # allauth not installed; silently skip
            return

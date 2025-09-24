from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from allauth.socialaccount import app_settings
from django.conf import settings
import json


def social_login_view(request):
    """
    Display available social login options
    """
    context = {
        'google_enabled': 'google' in settings.SOCIALACCOUNT_PROVIDERS,
        'facebook_enabled': 'facebook' in settings.SOCIALACCOUNT_PROVIDERS,
        'github_enabled': 'github' in settings.SOCIALACCOUNT_PROVIDERS,
    }
    return render(request, 'auth_payments/social_login.html', context)


@login_required
def social_connections_view(request):
    """
    Display user's connected social accounts
    """
    social_accounts = SocialAccount.objects.filter(user=request.user)
    
    context = {
        'social_accounts': social_accounts,
        'available_providers': {
            'google': 'google' in settings.SOCIALACCOUNT_PROVIDERS,
            'facebook': 'facebook' in settings.SOCIALACCOUNT_PROVIDERS,
            'github': 'github' in settings.SOCIALACCOUNT_PROVIDERS,
        }
    }
    return render(request, 'auth_payments/social_connections.html', context)


@login_required
@require_http_methods(["POST"])
def disconnect_social_account(request, provider):
    """
    Disconnect a social account from user's profile
    """
    try:
        social_account = SocialAccount.objects.get(
            user=request.user,
            provider=provider
        )
        social_account.delete()
        messages.success(request, f'Successfully disconnected {provider.title()} account.')
    except SocialAccount.DoesNotExist:
        messages.error(request, f'No {provider.title()} account found to disconnect.')
    
    return redirect('auth_payments:social_connections')


def oauth_callback_success(request):
    """
    Handle successful OAuth callback
    """
    messages.success(request, 'Successfully connected your social account!')
    return redirect('auth_payments:social_connections')


def oauth_callback_error(request):
    """
    Handle OAuth callback errors
    """
    error = request.GET.get('error', 'Unknown error')
    error_description = request.GET.get('error_description', 'An error occurred during authentication')
    
    messages.error(request, f'Authentication failed: {error_description}')
    return redirect('auth_payments:social_login')


@csrf_exempt
@require_http_methods(["GET"])
def social_account_info(request):
    """
    API endpoint to get user's social account information
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    social_accounts = SocialAccount.objects.filter(user=request.user)
    accounts_data = []
    
    for account in social_accounts:
        accounts_data.append({
            'provider': account.provider,
            'uid': account.uid,
            'extra_data': {
                'name': account.extra_data.get('name', ''),
                'email': account.extra_data.get('email', ''),
                'picture': account.extra_data.get('picture', ''),
                'avatar_url': account.extra_data.get('avatar_url', ''),
            },
            'date_joined': account.date_joined.isoformat() if account.date_joined else None,
        })
    
    return JsonResponse({
        'social_accounts': accounts_data,
        'total_accounts': len(accounts_data)
    })


class CustomGoogleOAuth2Adapter(GoogleOAuth2Adapter):
    """
    Custom Google OAuth2 adapter with additional logging
    """
    def complete_login(self, request, app, token, **kwargs):
        # Add custom logging here if needed
        return super().complete_login(request, app, token, **kwargs)


class CustomFacebookOAuth2Adapter(FacebookOAuth2Adapter):
    """
    Custom Facebook OAuth2 adapter with additional logging
    """
    def complete_login(self, request, app, token, **kwargs):
        # Add custom logging here if needed
        return super().complete_login(request, app, token, **kwargs)


class CustomGitHubOAuth2Adapter(GitHubOAuth2Adapter):
    """
    Custom GitHub OAuth2 adapter with additional logging
    """
    def complete_login(self, request, app, token, **kwargs):
        # Add custom logging here if needed
        return super().complete_login(request, app, token, **kwargs)
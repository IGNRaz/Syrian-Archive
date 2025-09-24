from django.urls import path, include
from allauth.socialaccount import urls as socialaccount_urls
from allauth.account.views import (
    LoginView, LogoutView, SignupView, 
    PasswordChangeView, PasswordSetView, PasswordResetView, 
    PasswordResetDoneView, PasswordResetFromKeyView, PasswordResetFromKeyDoneView
)

# Custom allauth URLs excluding email confirmation endpoints
urlpatterns = [
    # Basic account URLs we want to keep (excluding email confirmation)
    path('login/', LoginView.as_view(), name='account_login'),
    path('logout/', LogoutView.as_view(), name='account_logout'),
    path('signup/', SignupView.as_view(), name='account_signup'),
    
    # Password management URLs
    path('password/change/', PasswordChangeView.as_view(), name='account_change_password'),
    path('password/set/', PasswordSetView.as_view(), name='account_set_password'),
    path('password/reset/', PasswordResetView.as_view(), name='account_reset_password'),
    path('password/reset/done/', PasswordResetDoneView.as_view(), name='account_reset_password_done'),
    path('password/reset/key/<uidb36>-<key>/', PasswordResetFromKeyView.as_view(), name='account_reset_password_from_key'),
    path('password/reset/key/done/', PasswordResetFromKeyDoneView.as_view(), name='account_reset_password_from_key_done'),
    
    # Social account URLs (GitHub, Google, etc.) - these are needed for provider_login_url
    # Include them after our custom URLs to avoid conflicts
    path('', include(socialaccount_urls)),
    
    # Note: Email confirmation URLs are intentionally excluded
    # - confirm-email/<key>/
    # - email/
    # - email/confirm/
]
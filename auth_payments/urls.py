from django.urls import path, include
from . import oauth_views, payment_views, api_views

app_name = 'auth_payments'

urlpatterns = [
    # OAuth/Social Authentication URLs
    path('social-login/', oauth_views.social_login_view, name='social_login'),
    path('social-connections/', oauth_views.social_connections_view, name='social_connections'),
    path('disconnect/<str:provider>/', oauth_views.disconnect_social_account, name='disconnect_social'),
    path('oauth/success/', oauth_views.oauth_callback_success, name='oauth_success'),
    path('oauth/error/', oauth_views.oauth_callback_error, name='oauth_error'),
    path('api/social-accounts/', oauth_views.social_account_info, name='social_account_info'),
    
    # Payment Method URLs
    path('payment-methods/', payment_views.payment_methods_view, name='payment_methods'),
    path('payment-methods/add/', payment_views.add_payment_method_view, name='add_payment_method'),
    path('payment-methods/delete/<int:payment_method_id>/', payment_views.delete_payment_method, name='delete_payment_method'),
    
    # Subscription URLs
    path('subscriptions/', payment_views.subscriptions_view, name='subscriptions'),
    path('subscriptions/create/', payment_views.create_subscription_view, name='create_subscription'),
    
    # Payment History
    path('payment-history/', payment_views.payment_history_view, name='payment_history'),
    
    # Stripe Webhook
    path('webhooks/stripe/', payment_views.stripe_webhook, name='stripe_webhook'),
    
    # API URLs
    path('api/payment-methods/', api_views.PaymentMethodAPIView.as_view(), name='api_payment_methods'),
    path('api/payment-history/', api_views.PaymentHistoryAPIView.as_view(), name='api_payment_history'),
    path('api/process-payment/', api_views.PaymentProcessingAPIView.as_view(), name='api_process_payment'),
    path('api/subscriptions/', api_views.SubscriptionAPIView.as_view(), name='api_subscriptions'),
    
    # Include django-allauth URLs
    path('accounts/', include('allauth.urls')),
]
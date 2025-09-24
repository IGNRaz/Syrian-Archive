"""Django settings configuration for auth_payments app"""

from django.conf import settings
import os

# Auth Payments App Configuration
AUTH_PAYMENTS_SETTINGS = {
    # Payment Gateway Configuration
    'PAYMENT_GATEWAYS': {
        'stripe': {
            'enabled': True,
            'publishable_key': os.environ.get('STRIPE_PUBLISHABLE_KEY', ''),
            'secret_key': os.environ.get('STRIPE_SECRET_KEY', ''),
            'webhook_secret': os.environ.get('STRIPE_WEBHOOK_SECRET', ''),
        },
        'paypal': {
            'enabled': True,
            'client_id': os.environ.get('PAYPAL_CLIENT_ID', ''),
            'client_secret': os.environ.get('PAYPAL_CLIENT_SECRET', ''),
            'mode': os.environ.get('PAYPAL_MODE', 'sandbox'),  # 'sandbox' or 'live'
            'webhook_secret': os.environ.get('PAYPAL_WEBHOOK_SECRET', ''),
        },
    },
    
    # Default payment gateway
    'DEFAULT_GATEWAY': 'stripe',
    
    # OAuth Configuration
    'OAUTH_PROVIDERS': {
        'google': {
            'enabled': True,
            'client_id': os.environ.get('GOOGLE_OAUTH_CLIENT_ID', ''),
            'client_secret': os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET', ''),
            'scope': ['openid', 'email', 'profile'],
        },
        'facebook': {
            'enabled': True,
            'app_id': os.environ.get('FACEBOOK_APP_ID', ''),
            'app_secret': os.environ.get('FACEBOOK_APP_SECRET', ''),
            'scope': ['email'],
        },
        'github': {
            'enabled': True,
            'client_id': os.environ.get('GITHUB_CLIENT_ID', 'Ov23lihrmRviwOMZCpWt'),
            'client_secret': os.environ.get('GITHUB_CLIENT_SECRET', '3dd95af4bf0c36b5248c5e5befba5d2098e138a2'),
            'scope': ['user:email'],
        },
    },
    
    # Security Configuration
    'SECURITY': {
        'encryption_key': os.environ.get('PAYMENT_ENCRYPTION_KEY', ''),
        'rate_limiting': {
            'enabled': True,
            'payment_attempts': 5,  # per hour
            'login_attempts': 10,   # per hour
            'webhook_requests': 100,  # per hour
        },
        'fraud_detection': {
            'enabled': True,
            'max_failed_attempts': 3,
            'suspicious_patterns': [
                'rapid_multiple_cards',
                'high_value_transactions',
                'unusual_locations',
            ],
        },
        'ip_blocking': {
            'enabled': True,
            'max_violations': 5,
            'block_duration': 3600,  # seconds
        },
    },
    
    # Subscription Plans
    'SUBSCRIPTION_PLANS': {
        'basic': {
            'name': 'Basic Plan',
            'price': 9.99,
            'currency': 'USD',
            'interval': 'month',
            'features': [
                'Access to basic archive',
                'Standard search',
                'Email support',
            ],
            'stripe_price_id': os.environ.get('STRIPE_BASIC_PRICE_ID', ''),
            'paypal_plan_id': os.environ.get('PAYPAL_BASIC_PLAN_ID', ''),
        },
        'premium': {
            'name': 'Premium Plan',
            'price': 19.99,
            'currency': 'USD',
            'interval': 'month',
            'features': [
                'Full archive access',
                'Advanced search & filters',
                'Priority support',
                'Export capabilities',
                'API access',
            ],
            'stripe_price_id': os.environ.get('STRIPE_PREMIUM_PRICE_ID', ''),
            'paypal_plan_id': os.environ.get('PAYPAL_PREMIUM_PLAN_ID', ''),
        },
        'enterprise': {
            'name': 'Enterprise Plan',
            'price': 49.99,
            'currency': 'USD',
            'interval': 'month',
            'features': [
                'Complete archive access',
                'Advanced analytics',
                'Dedicated support',
                'Custom integrations',
                'Bulk operations',
                'White-label options',
            ],
            'stripe_price_id': os.environ.get('STRIPE_ENTERPRISE_PRICE_ID', ''),
            'paypal_plan_id': os.environ.get('PAYPAL_ENTERPRISE_PLAN_ID', ''),
        },
    },
    
    # Email Configuration
    'EMAIL_TEMPLATES': {
        'payment_success': 'auth_payments/emails/payment_success.html',
        'payment_failure': 'auth_payments/emails/payment_failure.html',
        'subscription_created': 'auth_payments/emails/subscription_created.html',
        'subscription_canceled': 'auth_payments/emails/subscription_canceled.html',
        'subscription_renewal': 'auth_payments/emails/subscription_renewal.html',
        'payment_method_added': 'auth_payments/emails/payment_method_added.html',
        'suspicious_activity': 'auth_payments/emails/suspicious_activity.html',
        'account_flagged': 'auth_payments/emails/account_flagged.html',
    },
    
    # Logging Configuration
    'LOGGING': {
        'payment_operations': True,
        'security_events': True,
        'webhook_events': True,
        'retention_days': 90,
    },
    
    # Cache Configuration
    'CACHE': {
        'rate_limit_cache': 'default',
        'session_cache': 'default',
        'payment_cache': 'default',
        'timeout': 3600,  # 1 hour
    },
    
    # Feature Flags
    'FEATURES': {
        'social_login': True,
        'subscription_management': True,
        'payment_methods': True,
        'payment_history': True,
        'fraud_detection': True,
        'webhook_processing': True,
    },
}

# Django Allauth Configuration
ALLAUTH_SETTINGS = {
    'ACCOUNT_EMAIL_REQUIRED': True,
    'ACCOUNT_EMAIL_VERIFICATION': 'mandatory',
    'ACCOUNT_USERNAME_REQUIRED': False,
    'ACCOUNT_AUTHENTICATION_METHOD': 'email',
    'ACCOUNT_UNIQUE_EMAIL': True,
    'ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION': True,
    'ACCOUNT_LOGOUT_ON_GET': True,
    'ACCOUNT_SESSION_REMEMBER': True,
    'SOCIALACCOUNT_AUTO_SIGNUP': True,
    'SOCIALACCOUNT_EMAIL_VERIFICATION': 'none',
    'SOCIALACCOUNT_QUERY_EMAIL': True,
    'SOCIALACCOUNT_PROVIDERS': {
        'google': {
            'SCOPE': [
                'profile',
                'email',
            ],
            'AUTH_PARAMS': {
                'access_type': 'online',
            },
            'OAUTH_PKCE_ENABLED': True,
        },
        'facebook': {
            'METHOD': 'oauth2',
            'SDK_URL': '//connect.facebook.net/{locale}/sdk.js',
            'SCOPE': ['email', 'public_profile'],
            'AUTH_PARAMS': {'auth_type': 'reauthenticate'},
            'INIT_PARAMS': {'cookie': True},
            'FIELDS': [
                'id',
                'first_name',
                'last_name',
                'middle_name',
                'name',
                'name_format',
                'picture',
                'short_name',
                'email',
            ],
            'EXCHANGE_TOKEN': True,
            'LOCALE_FUNC': 'path.to.callable',
            'VERIFIED_EMAIL': False,
            'VERSION': 'v13.0',
        },
        'github': {
            'SCOPE': [
                'user:email',
            ],
        },
    },
}

# Middleware Configuration
MIDDLEWARE_SETTINGS = [
    'auth_payments.middleware.PaymentSecurityMiddleware',
    'auth_payments.middleware.SessionSecurityMiddleware',
    'auth_payments.middleware.PaymentLoggingMiddleware',
    'auth_payments.middleware.CORSMiddleware',
]

# Database Configuration
DATABASE_SETTINGS = {
    # Add any specific database settings for auth_payments
    'OPTIONS': {
        'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
    },
}

# Static Files Configuration
STATIC_FILES_SETTINGS = {
    'STATICFILES_DIRS': [
        ('auth_payments', os.path.join(os.path.dirname(__file__), 'static')),
    ],
}

# Template Configuration
TEMPLATE_SETTINGS = {
    'DIRS': [
        os.path.join(os.path.dirname(__file__), 'templates'),
    ],
    'OPTIONS': {
        'context_processors': [
            'auth_payments.context_processors.payment_context',
            'auth_payments.context_processors.subscription_context',
        ],
    },
}

# URL Configuration
URL_SETTINGS = {
    'LOGIN_URL': '/auth/login/',
    'LOGIN_REDIRECT_URL': '/dashboard/',
    'LOGOUT_REDIRECT_URL': '/',
}

# Session Configuration
SESSION_SETTINGS = {
    'SESSION_COOKIE_AGE': 86400,  # 24 hours
    'SESSION_COOKIE_SECURE': True,
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_SAMESITE': 'Lax',
    'SESSION_SAVE_EVERY_REQUEST': True,
}

# CSRF Configuration
CSRF_SETTINGS = {
    'CSRF_COOKIE_SECURE': True,
    'CSRF_COOKIE_HTTPONLY': True,
    'CSRF_COOKIE_SAMESITE': 'Lax',
    'CSRF_TRUSTED_ORIGINS': [
        'https://yourdomain.com',
    ],
}

# Security Headers
SECURITY_HEADERS = {
    'SECURE_BROWSER_XSS_FILTER': True,
    'SECURE_CONTENT_TYPE_NOSNIFF': True,
    'SECURE_HSTS_SECONDS': 31536000,
    'SECURE_HSTS_INCLUDE_SUBDOMAINS': True,
    'SECURE_HSTS_PRELOAD': True,
    'X_FRAME_OPTIONS': 'DENY',
}

# Logging Configuration
LOGGING_SETTINGS = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'payment_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(settings.BASE_DIR, 'logs', 'payments.log'),
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(settings.BASE_DIR, 'logs', 'security.log'),
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'auth_payments.payments': {
            'handlers': ['payment_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'auth_payments.security': {
            'handlers': ['security_file'],
            'level': 'WARNING',
            'propagate': True,
        },
    },
}

# Helper function to merge settings
def configure_django_settings():
    """Configure Django settings for auth_payments app"""
    
    # Add to INSTALLED_APPS if not already present
    if 'auth_payments' not in settings.INSTALLED_APPS:
        settings.INSTALLED_APPS += ['auth_payments']
    
    # Add allauth apps if not present
    allauth_apps = [
        'allauth',
        'allauth.account',
        'allauth.socialaccount',
        'allauth.socialaccount.providers.google',
        'allauth.socialaccount.providers.facebook',
        'allauth.socialaccount.providers.github',
    ]
    
    for app in allauth_apps:
        if app not in settings.INSTALLED_APPS:
            settings.INSTALLED_APPS += [app]
    
    # Add middleware
    for middleware in MIDDLEWARE_SETTINGS:
        if middleware not in settings.MIDDLEWARE:
            settings.MIDDLEWARE += [middleware]
    
    # Configure allauth settings
    for key, value in ALLAUTH_SETTINGS.items():
        setattr(settings, key, value)
    
    # Configure URL settings
    for key, value in URL_SETTINGS.items():
        setattr(settings, key, value)
    
    # Configure session settings
    for key, value in SESSION_SETTINGS.items():
        setattr(settings, key, value)
    
    # Configure CSRF settings
    for key, value in CSRF_SETTINGS.items():
        setattr(settings, key, value)
    
    # Configure security headers
    for key, value in SECURITY_HEADERS.items():
        setattr(settings, key, value)
    
    # Add auth_payments settings
    settings.AUTH_PAYMENTS = AUTH_PAYMENTS_SETTINGS
    
    # Configure logging
    if hasattr(settings, 'LOGGING'):
        # Merge with existing logging configuration
        existing_logging = settings.LOGGING
        for key, value in LOGGING_SETTINGS.items():
            if key in existing_logging:
                if isinstance(value, dict):
                    existing_logging[key].update(value)
                else:
                    existing_logging[key] = value
            else:
                existing_logging[key] = value
    else:
        settings.LOGGING = LOGGING_SETTINGS

# Environment variables validation
def validate_environment_variables():
    """Validate required environment variables"""
    required_vars = [
        'STRIPE_PUBLISHABLE_KEY',
        'STRIPE_SECRET_KEY',
        'GOOGLE_OAUTH_CLIENT_ID',
        'GOOGLE_OAUTH_CLIENT_SECRET',
        'PAYMENT_ENCRYPTION_KEY',
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )

# Auto-configure when imported
if hasattr(settings, 'INSTALLED_APPS'):
    configure_django_settings()
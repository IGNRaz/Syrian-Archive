from django.conf import settings
import os
from typing import Dict, Any

# Payment Gateway Configuration
PAYMENT_GATEWAYS = {
    'stripe': {
        'public_key': os.environ.get('STRIPE_PUBLIC_KEY', ''),
        'secret_key': os.environ.get('STRIPE_SECRET_KEY', ''),
        'webhook_secret': os.environ.get('STRIPE_WEBHOOK_SECRET', ''),
        'api_version': '2023-10-16',
        'enabled': True,
    },
    'paypal': {
        'client_id': os.environ.get('PAYPAL_CLIENT_ID', ''),
        'client_secret': os.environ.get('PAYPAL_CLIENT_SECRET', ''),
        'webhook_id': os.environ.get('PAYPAL_WEBHOOK_ID', ''),
        'sandbox': os.environ.get('PAYPAL_SANDBOX', 'True').lower() == 'true',
        'enabled': False,  # Disabled by default
    }
}

# OAuth Provider Configuration
OAUTH_PROVIDERS = {
    'google': {
        'client_id': os.environ.get('GOOGLE_OAUTH_CLIENT_ID', ''),
        'client_secret': os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET', ''),
        'scope': ['openid', 'email', 'profile'],
        'enabled': True,
    },
    'microsoft': {
        'client_id': os.environ.get('MICROSOFT_CLIENT_ID', ''),
        'client_secret': os.environ.get('MICROSOFT_CLIENT_SECRET', ''),
        'scope': ['openid', 'email', 'profile'],
        'enabled': True,
    },
    'github': {
        'client_id': os.environ.get('GITHUB_CLIENT_ID', ''),
        'client_secret': os.environ.get('GITHUB_CLIENT_SECRET', ''),
        'scope': ['user:email'],
        'enabled': True,
    },
    'linkedin': {
        'client_id': os.environ.get('LINKEDIN_CLIENT_ID', ''),
        'client_secret': os.environ.get('LINKEDIN_CLIENT_SECRET', ''),
        'scope': ['r_liteprofile', 'r_emailaddress'],
        'enabled': True,
    }
}

# Security Configuration
SECURITY_SETTINGS = {
    # Rate Limiting
    'RATE_LIMIT_ENABLED': True,
    'RATE_LIMIT_REQUESTS_PER_HOUR': 100,
    'RATE_LIMIT_REQUESTS_PER_MINUTE': 10,
    
    # Payment Security
    'MAX_PAYMENT_ATTEMPTS': 3,
    'PAYMENT_ATTEMPT_LOCKOUT_MINUTES': 15,
    'REQUIRE_CVV_VERIFICATION': True,
    'REQUIRE_ADDRESS_VERIFICATION': True,
    
    # Authentication Security
    'MAX_LOGIN_ATTEMPTS': 5,
    'LOGIN_LOCKOUT_MINUTES': 30,
    'REQUIRE_EMAIL_VERIFICATION': True,
    'PASSWORD_RESET_TIMEOUT_HOURS': 24,
    
    # Session Security
    'SESSION_TIMEOUT_MINUTES': 60,
    'REQUIRE_HTTPS': not settings.DEBUG,
    'SECURE_COOKIES': not settings.DEBUG,
    
    # Fraud Detection
    'ENABLE_FRAUD_DETECTION': True,
    'SUSPICIOUS_ACTIVITY_THRESHOLD': 10,
    'AUTO_BAN_SUSPICIOUS_IPS': True,
    'IP_BAN_DURATION_HOURS': 24,
    
    # Data Protection
    'ENCRYPT_SENSITIVE_DATA': True,
    'LOG_PAYMENT_ACTIVITIES': True,
    'ANONYMIZE_LOGS_AFTER_DAYS': 90,
    'GDPR_COMPLIANCE_MODE': True,
}

# Subscription Plans Configuration
SUBSCRIPTION_PLANS = {
    'basic': {
        'name': 'Basic Plan',
        'description': 'Access to basic archive features',
        'price_monthly': 9.99,
        'price_yearly': 99.99,
        'currency': 'USD',
        'features': [
            'Access to public archives',
            'Basic search functionality',
            'Download up to 10 documents per month',
            'Email support'
        ],
        'limits': {
            'downloads_per_month': 10,
            'storage_gb': 1,
            'api_calls_per_day': 100
        },
        'stripe_price_id_monthly': os.environ.get('STRIPE_BASIC_MONTHLY_PRICE_ID', ''),
        'stripe_price_id_yearly': os.environ.get('STRIPE_BASIC_YEARLY_PRICE_ID', ''),
    },
    'premium': {
        'name': 'Premium Plan',
        'description': 'Enhanced access with advanced features',
        'price_monthly': 19.99,
        'price_yearly': 199.99,
        'currency': 'USD',
        'features': [
            'Access to all archives including restricted content',
            'Advanced search with filters and sorting',
            'Unlimited downloads',
            'Priority email support',
            'API access',
            'Export to multiple formats'
        ],
        'limits': {
            'downloads_per_month': -1,  # Unlimited
            'storage_gb': 10,
            'api_calls_per_day': 1000
        },
        'stripe_price_id_monthly': os.environ.get('STRIPE_PREMIUM_MONTHLY_PRICE_ID', ''),
        'stripe_price_id_yearly': os.environ.get('STRIPE_PREMIUM_YEARLY_PRICE_ID', ''),
    },
    'enterprise': {
        'name': 'Enterprise Plan',
        'description': 'Full access for organizations and researchers',
        'price_monthly': 49.99,
        'price_yearly': 499.99,
        'currency': 'USD',
        'features': [
            'Complete archive access',
            'Advanced analytics and reporting',
            'Bulk download capabilities',
            'Dedicated support manager',
            'Full API access with higher limits',
            'Custom integrations',
            'White-label options',
            'Data export and backup services'
        ],
        'limits': {
            'downloads_per_month': -1,  # Unlimited
            'storage_gb': 100,
            'api_calls_per_day': 10000
        },
        'stripe_price_id_monthly': os.environ.get('STRIPE_ENTERPRISE_MONTHLY_PRICE_ID', ''),
        'stripe_price_id_yearly': os.environ.get('STRIPE_ENTERPRISE_YEARLY_PRICE_ID', ''),
    }
}

# Email Configuration for Notifications
EMAIL_TEMPLATES = {
    'payment_success': {
        'subject': 'Payment Confirmation - Syrian Archive',
        'template': 'auth_payments/emails/payment_success.html',
    },
    'payment_failed': {
        'subject': 'Payment Failed - Syrian Archive',
        'template': 'auth_payments/emails/payment_failed.html',
    },
    'subscription_created': {
        'subject': 'Welcome to Syrian Archive - Subscription Activated',
        'template': 'auth_payments/emails/subscription_created.html',
    },
    'subscription_cancelled': {
        'subject': 'Subscription Cancelled - Syrian Archive',
        'template': 'auth_payments/emails/subscription_cancelled.html',
    },
    'subscription_renewed': {
        'subject': 'Subscription Renewed - Syrian Archive',
        'template': 'auth_payments/emails/subscription_renewed.html',
    },
    'account_flagged': {
        'subject': 'Account Security Alert - Syrian Archive',
        'template': 'auth_payments/emails/account_flagged.html',
    }
}

# Logging Configuration
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'payment_formatter': {
            'format': '[{levelname}] {asctime} - {name} - {message}',
            'style': '{',
        },
        'security_formatter': {
            'format': '[SECURITY] {asctime} - {levelname} - {name} - {message}',
            'style': '{',
        },
    },
    'handlers': {
        'payment_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(settings.BASE_DIR, 'logs', 'payments.log'),
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
            'formatter': 'payment_formatter',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(settings.BASE_DIR, 'logs', 'security.log'),
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 10,
            'formatter': 'security_formatter',
        },
        'console': {
            'level': 'DEBUG' if settings.DEBUG else 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'payment_formatter',
        },
    },
    'loggers': {
        'auth_payments.payment_views': {
            'handlers': ['payment_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'auth_payments.security': {
            'handlers': ['security_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'auth_payments.oauth_views': {
            'handlers': ['payment_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Webhook Configuration
WEBHOOK_SETTINGS = {
    'stripe': {
        'endpoint_secret': os.environ.get('STRIPE_WEBHOOK_SECRET', ''),
        'events': [
            'payment_intent.succeeded',
            'payment_intent.payment_failed',
            'invoice.payment_succeeded',
            'invoice.payment_failed',
            'customer.subscription.created',
            'customer.subscription.updated',
            'customer.subscription.deleted',
        ],
    },
    'paypal': {
        'webhook_id': os.environ.get('PAYPAL_WEBHOOK_ID', ''),
        'events': [
            'PAYMENT.CAPTURE.COMPLETED',
            'PAYMENT.CAPTURE.DENIED',
            'BILLING.SUBSCRIPTION.CREATED',
            'BILLING.SUBSCRIPTION.CANCELLED',
        ],
    }
}

# API Configuration
API_SETTINGS = {
    'PAGINATION_PAGE_SIZE': 20,
    'MAX_PAGE_SIZE': 100,
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'premium': '5000/hour',
        'enterprise': '10000/hour',
    },
    'AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# Cache Configuration
CACHE_SETTINGS = {
    'PAYMENT_CACHE_TIMEOUT': 300,  # 5 minutes
    'SUBSCRIPTION_CACHE_TIMEOUT': 3600,  # 1 hour
    'RATE_LIMIT_CACHE_TIMEOUT': 3600,  # 1 hour
    'SECURITY_CACHE_TIMEOUT': 86400,  # 24 hours
}

# Feature Flags
FEATURE_FLAGS = {
    'ENABLE_PAYPAL': False,
    'ENABLE_CRYPTOCURRENCY': False,
    'ENABLE_GIFT_CARDS': False,
    'ENABLE_REFERRAL_PROGRAM': False,
    'ENABLE_TRIAL_PERIODS': True,
    'ENABLE_PROMO_CODES': True,
    'ENABLE_MULTI_CURRENCY': False,
    'ENABLE_INVOICE_GENERATION': True,
    'ENABLE_USAGE_ANALYTICS': True,
    'ENABLE_A_B_TESTING': False,
}

# Utility Functions
def get_payment_gateway_config(gateway_name: str) -> Dict[str, Any]:
    """Get configuration for a specific payment gateway"""
    return PAYMENT_GATEWAYS.get(gateway_name, {})

def get_oauth_provider_config(provider_name: str) -> Dict[str, Any]:
    """Get configuration for a specific OAuth provider"""
    return OAUTH_PROVIDERS.get(provider_name, {})

def get_subscription_plan(plan_name: str) -> Dict[str, Any]:
    """Get configuration for a specific subscription plan"""
    return SUBSCRIPTION_PLANS.get(plan_name, {})

def is_feature_enabled(feature_name: str) -> bool:
    """Check if a feature flag is enabled"""
    return FEATURE_FLAGS.get(feature_name, False)

def get_security_setting(setting_name: str, default=None):
    """Get a security setting value"""
    return SECURITY_SETTINGS.get(setting_name, default)

def get_all_enabled_payment_gateways() -> Dict[str, Dict[str, Any]]:
    """Get all enabled payment gateways"""
    return {name: config for name, config in PAYMENT_GATEWAYS.items() if config.get('enabled', False)}

def get_all_enabled_oauth_providers() -> Dict[str, Dict[str, Any]]:
    """Get all enabled OAuth providers"""
    return {name: config for name, config in OAUTH_PROVIDERS.items() if config.get('enabled', False)}

def validate_environment_variables() -> Dict[str, list]:
    """Validate that required environment variables are set"""
    missing_vars = []
    warnings = []
    
    # Check Stripe configuration
    if PAYMENT_GATEWAYS['stripe']['enabled']:
        stripe_vars = ['STRIPE_PUBLIC_KEY', 'STRIPE_SECRET_KEY', 'STRIPE_WEBHOOK_SECRET']
        for var in stripe_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
    
    # Check OAuth providers
    for provider, config in OAUTH_PROVIDERS.items():
        if config['enabled']:
            if provider == 'google':
                required_vars = ['GOOGLE_OAUTH_CLIENT_ID', 'GOOGLE_OAUTH_CLIENT_SECRET']
            elif provider == 'facebook':
                required_vars = ['FACEBOOK_APP_ID', 'FACEBOOK_APP_SECRET']
            elif provider == 'github':
                required_vars = ['GITHUB_CLIENT_ID', 'GITHUB_CLIENT_SECRET']
            else:
                continue
            
            for var in required_vars:
                if not os.environ.get(var):
                    missing_vars.append(var)
    
    # Check if running in production without proper security settings
    if not settings.DEBUG:
        if not settings.SECRET_KEY or settings.SECRET_KEY == 'your-secret-key-here':
            missing_vars.append('SECRET_KEY (production-ready)')
        
        if not SECURITY_SETTINGS['REQUIRE_HTTPS']:
            warnings.append('HTTPS should be required in production')
    
    return {
        'missing_required': missing_vars,
        'warnings': warnings
    }
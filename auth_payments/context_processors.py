"""Context processors for auth_payments app"""

from django.conf import settings
from .models import PaymentMethod, Subscription, PaymentTransaction
from .settings_config import get_payment_config, get_subscription_plans
from decimal import Decimal
from datetime import datetime, timedelta

def payment_context(request):
    """Add payment-related context to templates"""
    context = {
        'payment_gateways_enabled': False,
        'stripe_enabled': False,
        'paypal_enabled': False,
        'stripe_publishable_key': '',
        'user_has_payment_methods': False,
        'user_default_payment_method': None,
    }
    
    try:
        config = get_payment_config()
        
        # Gateway availability
        stripe_config = config.get('stripe', {})
        paypal_config = config.get('paypal', {})
        
        context['stripe_enabled'] = stripe_config.get('enabled', False)
        context['paypal_enabled'] = paypal_config.get('enabled', False)
        context['payment_gateways_enabled'] = context['stripe_enabled'] or context['paypal_enabled']
        
        # Stripe public key for frontend
        if context['stripe_enabled']:
            context['stripe_publishable_key'] = stripe_config.get('publishable_key', '')
        
        # User-specific payment data
        if request.user.is_authenticated:
            user_payment_methods = PaymentMethod.objects.filter(
                user=request.user, 
                is_active=True
            )
            
            context['user_has_payment_methods'] = user_payment_methods.exists()
            context['user_payment_methods_count'] = user_payment_methods.count()
            
            # Default payment method
            default_method = user_payment_methods.filter(is_default=True).first()
            if default_method:
                context['user_default_payment_method'] = {
                    'id': default_method.id,
                    'type': default_method.payment_type,
                    'brand': default_method.card_brand,
                    'last_four': default_method.card_last_four,
                    'exp_month': default_method.card_exp_month,
                    'exp_year': default_method.card_exp_year,
                }
            
            # Recent payment activity
            recent_transactions = PaymentTransaction.objects.filter(
                user=request.user
            ).order_by('-created_at')[:5]
            
            context['recent_transactions'] = [
                {
                    'id': t.id,
                    'amount': t.amount,
                    'currency': t.currency,
                    'status': t.status,
                    'description': t.description,
                    'created_at': t.created_at,
                    'gateway': t.gateway,
                }
                for t in recent_transactions
            ]
            
            # Payment statistics
            total_spent = PaymentTransaction.objects.filter(
                user=request.user,
                status='completed'
            ).aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0.00')
            
            context['user_total_spent'] = total_spent
            
            # Failed payments in last 30 days
            thirty_days_ago = datetime.now() - timedelta(days=30)
            failed_payments = PaymentTransaction.objects.filter(
                user=request.user,
                status='failed',
                created_at__gte=thirty_days_ago
            ).count()
            
            context['recent_failed_payments'] = failed_payments
    
    except Exception as e:
        # Log error but don't break the template
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in payment_context: {e}")
    
    return context

def subscription_context(request):
    """Add subscription-related context to templates"""
    context = {
        'subscription_plans': [],
        'user_has_subscription': False,
        'user_subscription': None,
        'subscription_features_enabled': False,
    }
    
    try:
        # Available subscription plans
        plans = get_subscription_plans()
        context['subscription_plans'] = [
            {
                'id': plan_id,
                'name': plan_data['name'],
                'price': plan_data['price'],
                'currency': plan_data['currency'],
                'interval': plan_data['interval'],
                'features': plan_data['features'],
            }
            for plan_id, plan_data in plans.items()
        ]
        
        # Check if subscriptions are enabled
        auth_payments_config = getattr(settings, 'AUTH_PAYMENTS', {})
        features = auth_payments_config.get('FEATURES', {})
        context['subscription_features_enabled'] = features.get('subscription_management', False)
        
        # User-specific subscription data
        if request.user.is_authenticated:
            user_subscription = Subscription.objects.filter(
                user=request.user,
                status__in=['active', 'trialing', 'past_due']
            ).first()
            
            if user_subscription:
                context['user_has_subscription'] = True
                context['user_subscription'] = {
                    'id': user_subscription.id,
                    'plan_id': user_subscription.plan_id,
                    'status': user_subscription.status,
                    'current_period_start': user_subscription.current_period_start,
                    'current_period_end': user_subscription.current_period_end,
                    'cancel_at_period_end': user_subscription.cancel_at_period_end,
                    'gateway': user_subscription.gateway,
                }
                
                # Add plan details
                plan_data = plans.get(user_subscription.plan_id, {})
                context['user_subscription'].update({
                    'plan_name': plan_data.get('name', 'Unknown Plan'),
                    'plan_price': plan_data.get('price', 0),
                    'plan_features': plan_data.get('features', []),
                })
                
                # Days until renewal/expiry
                if user_subscription.current_period_end:
                    days_until_renewal = (user_subscription.current_period_end.date() - datetime.now().date()).days
                    context['user_subscription']['days_until_renewal'] = days_until_renewal
                    context['user_subscription']['renewal_soon'] = days_until_renewal <= 7
            
            # Subscription history
            subscription_history = Subscription.objects.filter(
                user=request.user
            ).order_by('-created_at')[:5]
            
            context['subscription_history'] = [
                {
                    'id': s.id,
                    'plan_id': s.plan_id,
                    'status': s.status,
                    'created_at': s.created_at,
                    'canceled_at': s.canceled_at,
                }
                for s in subscription_history
            ]
    
    except Exception as e:
        # Log error but don't break the template
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in subscription_context: {e}")
    
    return context

def auth_context(request):
    """Add authentication-related context to templates"""
    context = {
        'social_login_enabled': False,
        'google_login_enabled': False,
        'facebook_login_enabled': False,
        'github_login_enabled': False,
        'oauth_providers': [],
    }
    
    try:
        auth_payments_config = getattr(settings, 'AUTH_PAYMENTS', {})
        oauth_config = auth_payments_config.get('OAUTH_PROVIDERS', {})
        features = auth_payments_config.get('FEATURES', {})
        
        context['social_login_enabled'] = features.get('social_login', False)
        
        if context['social_login_enabled']:
            # Check individual providers
            google_config = oauth_config.get('google', {})
            facebook_config = oauth_config.get('facebook', {})
            github_config = oauth_config.get('github', {})
            
            context['google_login_enabled'] = google_config.get('enabled', False)
            context['facebook_login_enabled'] = facebook_config.get('enabled', False)
            context['github_login_enabled'] = github_config.get('enabled', False)
            
            # Available providers list
            if context['google_login_enabled']:
                context['oauth_providers'].append({
                    'id': 'google',
                    'name': 'Google',
                    'icon': 'fab fa-google',
                    'color': '#db4437',
                })
            
            if context['facebook_login_enabled']:
                context['oauth_providers'].append({
                    'id': 'facebook',
                    'name': 'Facebook',
                    'icon': 'fab fa-facebook-f',
                    'color': '#3b5998',
                })
            
            if context['github_login_enabled']:
                context['oauth_providers'].append({
                    'id': 'github',
                    'name': 'GitHub',
                    'icon': 'fab fa-github',
                    'color': '#333',
                })
        
        # User social connections
        if request.user.is_authenticated:
            try:
                from allauth.socialaccount.models import SocialAccount
                social_accounts = SocialAccount.objects.filter(user=request.user)
                
                context['user_social_connections'] = [
                    {
                        'provider': account.provider,
                        'uid': account.uid,
                        'extra_data': account.extra_data,
                    }
                    for account in social_accounts
                ]
                
                context['connected_providers'] = [account.provider for account in social_accounts]
                
            except ImportError:
                # allauth not available
                context['user_social_connections'] = []
                context['connected_providers'] = []
    
    except Exception as e:
        # Log error but don't break the template
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in auth_context: {e}")
    
    return context

def security_context(request):
    """Add security-related context to templates"""
    context = {
        'security_features_enabled': False,
        'two_factor_enabled': False,
        'account_security_score': 0,
        'security_recommendations': [],
    }
    
    try:
        auth_payments_config = getattr(settings, 'AUTH_PAYMENTS', {})
        features = auth_payments_config.get('FEATURES', {})
        security_config = auth_payments_config.get('SECURITY', {})
        
        context['security_features_enabled'] = features.get('fraud_detection', False)
        
        if request.user.is_authenticated:
            # Calculate security score
            score = 0
            recommendations = []
            
            # Email verification
            if hasattr(request.user, 'emailaddress_set'):
                verified_emails = request.user.emailaddress_set.filter(verified=True)
                if verified_emails.exists():
                    score += 25
                else:
                    recommendations.append({
                        'type': 'email_verification',
                        'message': 'Verify your email address',
                        'action_url': '/accounts/email/',
                    })
            
            # Social account connections
            try:
                from allauth.socialaccount.models import SocialAccount
                social_accounts = SocialAccount.objects.filter(user=request.user)
                if social_accounts.exists():
                    score += 15
                else:
                    recommendations.append({
                        'type': 'social_connection',
                        'message': 'Connect a social account for easier login',
                        'action_url': '/auth/social-connections/',
                    })
            except ImportError:
                pass
            
            # Payment method added
            if PaymentMethod.objects.filter(user=request.user, is_active=True).exists():
                score += 20
            else:
                recommendations.append({
                    'type': 'payment_method',
                    'message': 'Add a payment method to secure your account',
                    'action_url': '/payments/methods/add/',
                })
            
            # Recent activity
            recent_logins = getattr(request.user, 'last_login', None)
            if recent_logins:
                score += 10
            
            # Strong password (basic check)
            if len(getattr(request.user, 'password', '')) > 60:  # Hashed password length
                score += 30
            else:
                recommendations.append({
                    'type': 'password_strength',
                    'message': 'Use a stronger password',
                    'action_url': '/accounts/password/change/',
                })
            
            context['account_security_score'] = min(score, 100)
            context['security_recommendations'] = recommendations
    
    except Exception as e:
        # Log error but don't break the template
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in security_context: {e}")
    
    return context

def feature_flags_context(request):
    """Add feature flags context to templates"""
    context = {'features': {}}
    
    try:
        auth_payments_config = getattr(settings, 'AUTH_PAYMENTS', {})
        features = auth_payments_config.get('FEATURES', {})
        
        context['features'] = {
            'social_login': features.get('social_login', False),
            'subscription_management': features.get('subscription_management', False),
            'payment_methods': features.get('payment_methods', False),
            'payment_history': features.get('payment_history', False),
            'fraud_detection': features.get('fraud_detection', False),
            'webhook_processing': features.get('webhook_processing', False),
        }
    
    except Exception as e:
        # Log error but don't break the template
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in feature_flags_context: {e}")
    
    return context
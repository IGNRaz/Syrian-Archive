from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User
from .models import PaymentTransaction, Subscription
from .settings_config import EMAIL_TEMPLATES, get_subscription_plan
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class NotificationManager:
    """Manages email notifications for payment and authentication events"""
    
    def __init__(self):
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@syrianarchive.org')
        self.support_email = getattr(settings, 'SUPPORT_EMAIL', 'support@syrianarchive.org')
    
    def send_payment_success_notification(self, transaction: PaymentTransaction) -> bool:
        """Send notification for successful payment"""
        try:
            user = transaction.user
            template_config = EMAIL_TEMPLATES['payment_success']
            
            context = {
                'user': user,
                'transaction': transaction,
                'amount': transaction.amount,
                'currency': transaction.currency,
                'transaction_id': transaction.stripe_payment_intent_id or transaction.id,
                'date': transaction.created_at,
                'support_email': self.support_email,
                'site_name': 'Syrian Archive',
            }
            
            # Add subscription details if this is a subscription payment
            if transaction.subscription:
                context['subscription'] = transaction.subscription
                context['plan'] = get_subscription_plan(transaction.subscription.plan_type)
            
            return self._send_email(
                template_config['subject'],
                template_config['template'],
                context,
                [user.email]
            )
        
        except Exception as e:
            logger.error(f"Failed to send payment success notification: {str(e)}")
            return False
    
    def send_payment_failed_notification(self, transaction: PaymentTransaction, error_message: str = None) -> bool:
        """Send notification for failed payment"""
        try:
            user = transaction.user
            template_config = EMAIL_TEMPLATES['payment_failed']
            
            context = {
                'user': user,
                'transaction': transaction,
                'amount': transaction.amount,
                'currency': transaction.currency,
                'error_message': error_message or 'Payment processing failed',
                'date': transaction.created_at,
                'support_email': self.support_email,
                'retry_url': f'/payment/retry/{transaction.id}/',
                'site_name': 'Syrian Archive',
            }
            
            return self._send_email(
                template_config['subject'],
                template_config['template'],
                context,
                [user.email]
            )
        
        except Exception as e:
            logger.error(f"Failed to send payment failed notification: {str(e)}")
            return False
    
    def send_subscription_created_notification(self, subscription: Subscription) -> bool:
        """Send welcome notification for new subscription"""
        try:
            user = subscription.user
            template_config = EMAIL_TEMPLATES['subscription_created']
            plan_config = get_subscription_plan(subscription.plan_type)
            
            context = {
                'user': user,
                'subscription': subscription,
                'plan': plan_config,
                'plan_name': plan_config.get('name', subscription.plan_type.title()),
                'features': plan_config.get('features', []),
                'next_billing_date': subscription.current_period_end,
                'amount': subscription.amount,
                'currency': subscription.currency,
                'support_email': self.support_email,
                'dashboard_url': '/subscription/',
                'site_name': 'Syrian Archive',
            }
            
            return self._send_email(
                template_config['subject'],
                template_config['template'],
                context,
                [user.email]
            )
        
        except Exception as e:
            logger.error(f"Failed to send subscription created notification: {str(e)}")
            return False
    
    def send_subscription_cancelled_notification(self, subscription: Subscription, reason: str = None) -> bool:
        """Send notification for cancelled subscription"""
        try:
            user = subscription.user
            template_config = EMAIL_TEMPLATES['subscription_cancelled']
            plan_config = get_subscription_plan(subscription.plan_type)
            
            context = {
                'user': user,
                'subscription': subscription,
                'plan_name': plan_config.get('name', subscription.plan_type.title()),
                'cancellation_reason': reason,
                'access_until': subscription.current_period_end,
                'reactivate_url': '/subscription/reactivate/',
                'support_email': self.support_email,
                'site_name': 'Syrian Archive',
            }
            
            return self._send_email(
                template_config['subject'],
                template_config['template'],
                context,
                [user.email]
            )
        
        except Exception as e:
            logger.error(f"Failed to send subscription cancelled notification: {str(e)}")
            return False
    
    def send_subscription_renewed_notification(self, subscription: Subscription, transaction: PaymentTransaction) -> bool:
        """Send notification for subscription renewal"""
        try:
            user = subscription.user
            template_config = EMAIL_TEMPLATES['subscription_renewed']
            plan_config = get_subscription_plan(subscription.plan_type)
            
            context = {
                'user': user,
                'subscription': subscription,
                'transaction': transaction,
                'plan_name': plan_config.get('name', subscription.plan_type.title()),
                'amount': transaction.amount,
                'currency': transaction.currency,
                'next_billing_date': subscription.current_period_end,
                'invoice_url': f'/payment/invoice/{transaction.id}/',
                'dashboard_url': '/subscription/',
                'support_email': self.support_email,
                'site_name': 'Syrian Archive',
            }
            
            return self._send_email(
                template_config['subject'],
                template_config['template'],
                context,
                [user.email]
            )
        
        except Exception as e:
            logger.error(f"Failed to send subscription renewed notification: {str(e)}")
            return False
    
    def send_account_flagged_notification(self, user: User, reason: str, details: Dict[str, Any]) -> bool:
        """Send security alert for flagged account"""
        try:
            template_config = EMAIL_TEMPLATES['account_flagged']
            
            context = {
                'user': user,
                'reason': reason,
                'details': details,
                'timestamp': timezone.now(),
                'support_email': self.support_email,
                'security_url': '/auth/security/',
                'site_name': 'Syrian Archive',
            }
            
            return self._send_email(
                template_config['subject'],
                template_config['template'],
                context,
                [user.email]
            )
        
        except Exception as e:
            logger.error(f"Failed to send account flagged notification: {str(e)}")
            return False
    
    def send_payment_reminder(self, subscription: Subscription, days_until_renewal: int) -> bool:
        """Send payment reminder before subscription renewal"""
        try:
            user = subscription.user
            plan_config = get_subscription_plan(subscription.plan_type)
            
            context = {
                'user': user,
                'subscription': subscription,
                'plan_name': plan_config.get('name', subscription.plan_type.title()),
                'days_until_renewal': days_until_renewal,
                'renewal_date': subscription.current_period_end,
                'amount': subscription.amount,
                'currency': subscription.currency,
                'payment_methods_url': '/payment/methods/',
                'dashboard_url': '/subscription/',
                'support_email': self.support_email,
                'site_name': 'Syrian Archive',
            }
            
            subject = f"Payment Reminder - Your {plan_config.get('name', 'subscription')} renews in {days_until_renewal} days"
            
            return self._send_email(
                subject,
                'auth_payments/emails/payment_reminder.html',
                context,
                [user.email]
            )
        
        except Exception as e:
            logger.error(f"Failed to send payment reminder: {str(e)}")
            return False
    
    def send_payment_method_added_notification(self, user: User, payment_method_details: Dict[str, Any]) -> bool:
        """Send notification when new payment method is added"""
        try:
            context = {
                'user': user,
                'payment_method': payment_method_details,
                'timestamp': timezone.now(),
                'security_url': '/auth/security/',
                'payment_methods_url': '/payment/methods/',
                'support_email': self.support_email,
                'site_name': 'Syrian Archive',
            }
            
            subject = "New Payment Method Added - Syrian Archive"
            
            return self._send_email(
                subject,
                'auth_payments/emails/payment_method_added.html',
                context,
                [user.email]
            )
        
        except Exception as e:
            logger.error(f"Failed to send payment method added notification: {str(e)}")
            return False
    
    def send_suspicious_activity_alert(self, user: User, activity_details: Dict[str, Any]) -> bool:
        """Send alert for suspicious account activity"""
        try:
            context = {
                'user': user,
                'activity': activity_details,
                'timestamp': timezone.now(),
                'security_url': '/auth/security/',
                'support_email': self.support_email,
                'site_name': 'Syrian Archive',
            }
            
            subject = "Security Alert - Suspicious Activity Detected"
            
            return self._send_email(
                subject,
                'auth_payments/emails/suspicious_activity.html',
                context,
                [user.email]
            )
        
        except Exception as e:
            logger.error(f"Failed to send suspicious activity alert: {str(e)}")
            return False
    
    def _send_email(self, subject: str, template_path: str, context: Dict[str, Any], recipients: List[str]) -> bool:
        """Send email using Django's email system"""
        try:
            # Render HTML content
            html_content = render_to_string(template_path, context)
            
            # Create text version (basic fallback)
            text_content = self._html_to_text(html_content)
            
            # Create email message
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=self.from_email,
                to=recipients
            )
            
            # Attach HTML version
            msg.attach_alternative(html_content, "text/html")
            
            # Send email
            msg.send()
            
            logger.info(f"Email sent successfully: {subject} to {', '.join(recipients)}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send email '{subject}' to {recipients}: {str(e)}")
            return False
    
    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML content to plain text (basic implementation)"""
        import re
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html_content)
        
        # Replace HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text

class NotificationScheduler:
    """Handles scheduled notifications like payment reminders"""
    
    def __init__(self):
        self.notification_manager = NotificationManager()
    
    def send_payment_reminders(self) -> Dict[str, int]:
        """Send payment reminders for upcoming renewals"""
        results = {
            'sent': 0,
            'failed': 0,
            'skipped': 0
        }
        
        try:
            # Get subscriptions that need reminders
            reminder_dates = [
                timezone.now().date() + timedelta(days=7),  # 7 days before
                timezone.now().date() + timedelta(days=3),  # 3 days before
                timezone.now().date() + timedelta(days=1),  # 1 day before
            ]
            
            for days_ahead, reminder_date in enumerate([7, 3, 1], 1):
                target_date = timezone.now().date() + timedelta(days=days_ahead)
                
                subscriptions = Subscription.objects.filter(
                    status='active',
                    current_period_end__date=target_date
                )
                
                for subscription in subscriptions:
                    # Check if reminder already sent
                    cache_key = f"reminder_sent:{subscription.id}:{days_ahead}"
                    from django.core.cache import cache
                    
                    if cache.get(cache_key):
                        results['skipped'] += 1
                        continue
                    
                    # Send reminder
                    if self.notification_manager.send_payment_reminder(subscription, days_ahead):
                        results['sent'] += 1
                        # Mark as sent (cache for 24 hours)
                        cache.set(cache_key, True, 86400)
                    else:
                        results['failed'] += 1
            
            logger.info(f"Payment reminders processed: {results}")
            return results
        
        except Exception as e:
            logger.error(f"Failed to process payment reminders: {str(e)}")
            results['failed'] += 1
            return results
    
    def send_failed_payment_followups(self) -> Dict[str, int]:
        """Send follow-up notifications for failed payments"""
        results = {
            'sent': 0,
            'failed': 0,
            'skipped': 0
        }
        
        try:
            # Get failed transactions from the last 7 days
            week_ago = timezone.now() - timedelta(days=7)
            
            failed_transactions = PaymentTransaction.objects.filter(
                status='failed',
                created_at__gte=week_ago
            ).select_related('user', 'subscription')
            
            for transaction in failed_transactions:
                # Check if follow-up already sent
                cache_key = f"followup_sent:{transaction.id}"
                from django.core.cache import cache
                
                if cache.get(cache_key):
                    results['skipped'] += 1
                    continue
                
                # Send follow-up
                if self.notification_manager.send_payment_failed_notification(
                    transaction, 
                    "Please update your payment method to continue your subscription."
                ):
                    results['sent'] += 1
                    # Mark as sent (cache for 7 days)
                    cache.set(cache_key, True, 604800)
                else:
                    results['failed'] += 1
            
            logger.info(f"Failed payment follow-ups processed: {results}")
            return results
        
        except Exception as e:
            logger.error(f"Failed to process payment follow-ups: {str(e)}")
            results['failed'] += 1
            return results

# Utility functions for common notification scenarios
def notify_payment_success(transaction: PaymentTransaction) -> bool:
    """Quick function to send payment success notification"""
    manager = NotificationManager()
    return manager.send_payment_success_notification(transaction)

def notify_payment_failed(transaction: PaymentTransaction, error_message: str = None) -> bool:
    """Quick function to send payment failed notification"""
    manager = NotificationManager()
    return manager.send_payment_failed_notification(transaction, error_message)

def notify_subscription_created(subscription: Subscription) -> bool:
    """Quick function to send subscription created notification"""
    manager = NotificationManager()
    return manager.send_subscription_created_notification(subscription)

def notify_subscription_cancelled(subscription: Subscription, reason: str = None) -> bool:
    """Quick function to send subscription cancelled notification"""
    manager = NotificationManager()
    return manager.send_subscription_cancelled_notification(subscription, reason)

def notify_subscription_renewed(subscription: Subscription, transaction: PaymentTransaction) -> bool:
    """Quick function to send subscription renewed notification"""
    manager = NotificationManager()
    return manager.send_subscription_renewed_notification(subscription, transaction)

def notify_account_flagged(user: User, reason: str, details: Dict[str, Any]) -> bool:
    """Quick function to send account flagged notification"""
    manager = NotificationManager()
    return manager.send_account_flagged_notification(user, reason, details)

def notify_suspicious_activity(user: User, activity_details: Dict[str, Any]) -> bool:
    """Quick function to send suspicious activity alert"""
    manager = NotificationManager()
    return manager.send_suspicious_activity_alert(user, activity_details)
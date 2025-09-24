from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views import View
from django.conf import settings
import json
import stripe
import hashlib
import hmac
import logging
from .payment_gateways import process_webhook
from .models import PaymentTransaction, Subscription
from .notifications import NotificationManager
from .security import PaymentSecurityManager

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(require_POST, name='dispatch')
class StripeWebhookView(View):
    """Handle Stripe webhooks"""
    
    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        endpoint_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
        
        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except ValueError:
            logger.error("Invalid payload in Stripe webhook")
            return HttpResponseBadRequest("Invalid payload")
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid signature in Stripe webhook")
            return HttpResponseBadRequest("Invalid signature")
        
        # Handle the event
        try:
            self._handle_stripe_event(event)
            return HttpResponse(status=200)
        except Exception as e:
            logger.error(f"Error handling Stripe webhook: {e}")
            return HttpResponse(status=500)
    
    def _handle_stripe_event(self, event):
        """Handle different types of Stripe events"""
        event_type = event['type']
        data = event['data']['object']
        
        if event_type == 'payment_intent.succeeded':
            self._handle_payment_success(data)
        elif event_type == 'payment_intent.payment_failed':
            self._handle_payment_failed(data)
        elif event_type == 'invoice.payment_succeeded':
            self._handle_invoice_payment_success(data)
        elif event_type == 'invoice.payment_failed':
            self._handle_invoice_payment_failed(data)
        elif event_type == 'customer.subscription.created':
            self._handle_subscription_created(data)
        elif event_type == 'customer.subscription.updated':
            self._handle_subscription_updated(data)
        elif event_type == 'customer.subscription.deleted':
            self._handle_subscription_deleted(data)
        elif event_type == 'payment_method.attached':
            self._handle_payment_method_attached(data)
        else:
            logger.info(f"Unhandled Stripe event type: {event_type}")
    
    def _handle_payment_success(self, payment_intent):
        """Handle successful payment"""
        try:
            transaction = PaymentTransaction.objects.get(
                gateway_transaction_id=payment_intent['id']
            )
            transaction.status = 'completed'
            transaction.gateway_response = payment_intent
            transaction.save()
            
            # Send success notification
            NotificationManager().send_payment_success_email(
                transaction.user, transaction
            )
            
            logger.info(f"Payment succeeded: {payment_intent['id']}")
        except PaymentTransaction.DoesNotExist:
            logger.warning(f"Transaction not found for payment intent: {payment_intent['id']}")
    
    def _handle_payment_failed(self, payment_intent):
        """Handle failed payment"""
        try:
            transaction = PaymentTransaction.objects.get(
                gateway_transaction_id=payment_intent['id']
            )
            transaction.status = 'failed'
            transaction.gateway_response = payment_intent
            transaction.save()
            
            # Send failure notification
            NotificationManager().send_payment_failure_email(
                transaction.user, transaction
            )
            
            logger.info(f"Payment failed: {payment_intent['id']}")
        except PaymentTransaction.DoesNotExist:
            logger.warning(f"Transaction not found for payment intent: {payment_intent['id']}")
    
    def _handle_invoice_payment_success(self, invoice):
        """Handle successful subscription payment"""
        subscription_id = invoice.get('subscription')
        if subscription_id:
            try:
                subscription = Subscription.objects.get(
                    gateway_subscription_id=subscription_id
                )
                subscription.status = 'active'
                subscription.save()
                
                # Send renewal notification
                NotificationManager().send_subscription_renewal_email(
                    subscription.user, subscription
                )
                
                logger.info(f"Subscription payment succeeded: {subscription_id}")
            except Subscription.DoesNotExist:
                logger.warning(f"Subscription not found: {subscription_id}")
    
    def _handle_invoice_payment_failed(self, invoice):
        """Handle failed subscription payment"""
        subscription_id = invoice.get('subscription')
        if subscription_id:
            try:
                subscription = Subscription.objects.get(
                    gateway_subscription_id=subscription_id
                )
                subscription.status = 'past_due'
                subscription.save()
                
                # Send failure notification
                NotificationManager().send_payment_failure_email(
                    subscription.user, None, subscription
                )
                
                logger.info(f"Subscription payment failed: {subscription_id}")
            except Subscription.DoesNotExist:
                logger.warning(f"Subscription not found: {subscription_id}")
    
    def _handle_subscription_created(self, subscription):
        """Handle subscription creation"""
        try:
            sub = Subscription.objects.get(
                gateway_subscription_id=subscription['id']
            )
            sub.status = subscription['status']
            sub.current_period_start = subscription['current_period_start']
            sub.current_period_end = subscription['current_period_end']
            sub.save()
            
            # Send creation notification
            NotificationManager().send_subscription_created_email(
                sub.user, sub
            )
            
            logger.info(f"Subscription created: {subscription['id']}")
        except Subscription.DoesNotExist:
            logger.warning(f"Subscription not found: {subscription['id']}")
    
    def _handle_subscription_updated(self, subscription):
        """Handle subscription updates"""
        try:
            sub = Subscription.objects.get(
                gateway_subscription_id=subscription['id']
            )
            sub.status = subscription['status']
            sub.current_period_start = subscription['current_period_start']
            sub.current_period_end = subscription['current_period_end']
            sub.save()
            
            logger.info(f"Subscription updated: {subscription['id']}")
        except Subscription.DoesNotExist:
            logger.warning(f"Subscription not found: {subscription['id']}")
    
    def _handle_subscription_deleted(self, subscription):
        """Handle subscription cancellation"""
        try:
            sub = Subscription.objects.get(
                gateway_subscription_id=subscription['id']
            )
            sub.status = 'canceled'
            sub.canceled_at = subscription.get('canceled_at')
            sub.save()
            
            # Send cancellation notification
            NotificationManager().send_subscription_canceled_email(
                sub.user, sub
            )
            
            logger.info(f"Subscription canceled: {subscription['id']}")
        except Subscription.DoesNotExist:
            logger.warning(f"Subscription not found: {subscription['id']}")
    
    def _handle_payment_method_attached(self, payment_method):
        """Handle payment method attachment"""
        logger.info(f"Payment method attached: {payment_method['id']}")

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(require_POST, name='dispatch')
class PayPalWebhookView(View):
    """Handle PayPal webhooks"""
    
    def post(self, request):
        try:
            # Verify PayPal webhook signature
            if not self._verify_paypal_signature(request):
                return HttpResponseBadRequest("Invalid signature")
            
            payload = json.loads(request.body)
            self._handle_paypal_event(payload)
            
            return HttpResponse(status=200)
        except Exception as e:
            logger.error(f"Error handling PayPal webhook: {e}")
            return HttpResponse(status=500)
    
    def _verify_paypal_signature(self, request):
        """Verify PayPal webhook signature"""
        # PayPal signature verification implementation
        # This is a simplified version - in production, use PayPal's SDK
        webhook_secret = getattr(settings, 'PAYPAL_WEBHOOK_SECRET', '')
        if not webhook_secret:
            return True  # Skip verification if no secret configured
        
        signature = request.META.get('HTTP_PAYPAL_TRANSMISSION_SIG')
        if not signature:
            return False
        
        # Implement proper PayPal signature verification here
        return True
    
    def _handle_paypal_event(self, event):
        """Handle PayPal webhook events"""
        event_type = event.get('event_type')
        
        if event_type == 'PAYMENT.SALE.COMPLETED':
            self._handle_payment_completed(event)
        elif event_type == 'PAYMENT.SALE.DENIED':
            self._handle_payment_denied(event)
        elif event_type == 'BILLING.SUBSCRIPTION.CREATED':
            self._handle_subscription_created_paypal(event)
        elif event_type == 'BILLING.SUBSCRIPTION.CANCELLED':
            self._handle_subscription_cancelled_paypal(event)
        else:
            logger.info(f"Unhandled PayPal event type: {event_type}")
    
    def _handle_payment_completed(self, event):
        """Handle completed PayPal payment"""
        resource = event.get('resource', {})
        payment_id = resource.get('parent_payment')
        
        if payment_id:
            try:
                transaction = PaymentTransaction.objects.get(
                    gateway_transaction_id=payment_id
                )
                transaction.status = 'completed'
                transaction.gateway_response = resource
                transaction.save()
                
                # Send success notification
                NotificationManager().send_payment_success_email(
                    transaction.user, transaction
                )
                
                logger.info(f"PayPal payment completed: {payment_id}")
            except PaymentTransaction.DoesNotExist:
                logger.warning(f"Transaction not found for PayPal payment: {payment_id}")
    
    def _handle_payment_denied(self, event):
        """Handle denied PayPal payment"""
        resource = event.get('resource', {})
        payment_id = resource.get('parent_payment')
        
        if payment_id:
            try:
                transaction = PaymentTransaction.objects.get(
                    gateway_transaction_id=payment_id
                )
                transaction.status = 'failed'
                transaction.gateway_response = resource
                transaction.save()
                
                # Send failure notification
                NotificationManager().send_payment_failure_email(
                    transaction.user, transaction
                )
                
                logger.info(f"PayPal payment denied: {payment_id}")
            except PaymentTransaction.DoesNotExist:
                logger.warning(f"Transaction not found for PayPal payment: {payment_id}")
    
    def _handle_subscription_created_paypal(self, event):
        """Handle PayPal subscription creation"""
        resource = event.get('resource', {})
        subscription_id = resource.get('id')
        
        if subscription_id:
            try:
                subscription = Subscription.objects.get(
                    gateway_subscription_id=subscription_id
                )
                subscription.status = 'active'
                subscription.save()
                
                # Send creation notification
                NotificationManager().send_subscription_created_email(
                    subscription.user, subscription
                )
                
                logger.info(f"PayPal subscription created: {subscription_id}")
            except Subscription.DoesNotExist:
                logger.warning(f"Subscription not found: {subscription_id}")
    
    def _handle_subscription_cancelled_paypal(self, event):
        """Handle PayPal subscription cancellation"""
        resource = event.get('resource', {})
        subscription_id = resource.get('id')
        
        if subscription_id:
            try:
                subscription = Subscription.objects.get(
                    gateway_subscription_id=subscription_id
                )
                subscription.status = 'canceled'
                subscription.save()
                
                # Send cancellation notification
                NotificationManager().send_subscription_canceled_email(
                    subscription.user, subscription
                )
                
                logger.info(f"PayPal subscription canceled: {subscription_id}")
            except Subscription.DoesNotExist:
                logger.warning(f"Subscription not found: {subscription_id}")

class WebhookSecurityMixin:
    """Mixin for webhook security features"""
    
    def dispatch(self, request, *args, **kwargs):
        # Log webhook attempt
        logger.info(f"Webhook received from {request.META.get('REMOTE_ADDR')}")
        
        # Check rate limiting
        security_manager = PaymentSecurityManager()
        if not security_manager.check_rate_limit(request, 'webhook'):
            logger.warning(f"Webhook rate limit exceeded from {request.META.get('REMOTE_ADDR')}")
            return HttpResponse(status=429)
        
        return super().dispatch(request, *args, **kwargs)

# Webhook URL patterns helper
def get_webhook_urls():
    """Get webhook URL patterns for inclusion in main urls.py"""
    from django.urls import path
    
    return [
        path('webhooks/stripe/', StripeWebhookView.as_view(), name='stripe_webhook'),
        path('webhooks/paypal/', PayPalWebhookView.as_view(), name='paypal_webhook'),
    ]
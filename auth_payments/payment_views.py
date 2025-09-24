from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from .models import PaymentMethod, PaymentTransaction, Subscription, PaymentLog
from .forms import PaymentMethodForm, SubscriptionForm
import stripe
import json
import logging

# Configure Stripe
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')

logger = logging.getLogger(__name__)


@login_required
def payment_methods_view(request):
    """
    Display user's payment methods
    """
    payment_methods = PaymentMethod.objects.filter(user=request.user, is_active=True)
    context = {
        'payment_methods': payment_methods,
        'stripe_publishable_key': getattr(settings, 'STRIPE_PUBLISHABLE_KEY', ''),
    }
    return render(request, 'auth_payments/payment_methods.html', context)


@login_required
def add_payment_method_view(request):
    """
    Add a new payment method
    """
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST)
        if form.is_valid():
            payment_method = form.save(commit=False)
            payment_method.user = request.user
            
            try:
                # Create Stripe payment method
                stripe_pm = stripe.PaymentMethod.create(
                    type='card',
                    card={
                        'number': form.cleaned_data['card_number'],
                        'exp_month': form.cleaned_data['card_exp_month'],
                        'exp_year': form.cleaned_data['card_exp_year'],
                        'cvc': form.cleaned_data['card_cvc'],
                    },
                )
                
                payment_method.stripe_payment_method_id = stripe_pm.id
                payment_method.card_last_four = stripe_pm.card.last4
                payment_method.card_brand = stripe_pm.card.brand
                payment_method.save()
                
                # Log the payment method addition
                PaymentLog.objects.create(
                    user=request.user,
                    log_type='payment_method_added',
                    message=f'Payment method added: {payment_method.card_brand} ending in {payment_method.card_last_four}',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', 'Unknown'),
                )
                
                messages.success(request, 'Payment method added successfully!')
                return redirect('auth_payments:payment_methods')
                
            except stripe.error.StripeError as e:
                messages.error(request, f'Error adding payment method: {str(e)}')
                logger.error(f'Stripe error adding payment method for user {request.user.id}: {str(e)}')
    else:
        form = PaymentMethodForm()
    
    context = {
        'form': form,
        'stripe_publishable_key': getattr(settings, 'STRIPE_PUBLISHABLE_KEY', ''),
    }
    return render(request, 'auth_payments/add_payment_method.html', context)


@login_required
@require_http_methods(["POST"])
def delete_payment_method(request, payment_method_id):
    """
    Delete a payment method
    """
    payment_method = get_object_or_404(
        PaymentMethod, 
        id=payment_method_id, 
        user=request.user
    )
    
    try:
        # Delete from Stripe if exists
        if payment_method.stripe_payment_method_id:
            stripe.PaymentMethod.detach(payment_method.stripe_payment_method_id)
        
        # Log the deletion
        PaymentLog.objects.create(
            user=request.user,
            log_type='payment_method_deleted',
            message=f'Payment method deleted: {payment_method.card_brand} ending in {payment_method.card_last_four}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', 'Unknown'),
        )
        
        payment_method.delete()
        messages.success(request, 'Payment method deleted successfully!')
        
    except stripe.error.StripeError as e:
        messages.error(request, f'Error deleting payment method: {str(e)}')
        logger.error(f'Stripe error deleting payment method {payment_method_id}: {str(e)}')
    
    return redirect('auth_payments:payment_methods')


@login_required
def subscriptions_view(request):
    """
    Display user's subscriptions
    """
    subscriptions = Subscription.objects.filter(user=request.user)
    context = {
        'subscriptions': subscriptions,
        'available_plans': {
            'basic': {'name': 'Basic Plan', 'price': 9.99},
            'premium': {'name': 'Premium Plan', 'price': 19.99},
            'enterprise': {'name': 'Enterprise Plan', 'price': 49.99},
        }
    }
    return render(request, 'auth_payments/subscriptions.html', context)


@login_required
def create_subscription_view(request):
    """
    Create a new subscription
    """
    if request.method == 'POST':
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            subscription = form.save(commit=False)
            subscription.user = request.user
            
            try:
                # Create Stripe subscription
                stripe_subscription = stripe.Subscription.create(
                    customer=request.user.email,  # You might want to create a Stripe customer first
                    items=[{
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {
                                'name': f'{subscription.plan.title()} Plan',
                            },
                            'unit_amount': int(subscription.monthly_price * 100),  # Convert to cents
                            'recurring': {
                                'interval': 'month',
                            },
                        },
                    }],
                )
                
                subscription.stripe_subscription_id = stripe_subscription.id
                subscription.status = 'active'
                subscription.start_date = timezone.now().date()
                subscription.save()
                
                # Log the subscription creation
                PaymentLog.objects.create(
                    user=request.user,
                    log_type='subscription_created',
                    message=f'Subscription created: {subscription.plan} plan for ${subscription.monthly_price}/month',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', 'Unknown'),
                )
                
                messages.success(request, 'Subscription created successfully!')
                return redirect('auth_payments:subscriptions')
                
            except stripe.error.StripeError as e:
                messages.error(request, f'Error creating subscription: {str(e)}')
                logger.error(f'Stripe error creating subscription for user {request.user.id}: {str(e)}')
    else:
        form = SubscriptionForm()
    
    context = {
        'form': form,
    }
    return render(request, 'auth_payments/create_subscription.html', context)


@login_required
def payment_history_view(request):
    """
    Display user's payment transaction history
    """
    transactions = PaymentTransaction.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'transactions': transactions,
    }
    return render(request, 'auth_payments/payment_history.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def stripe_webhook(request):
    """
    Handle Stripe webhooks
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        logger.error('Invalid payload in Stripe webhook')
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        logger.error('Invalid signature in Stripe webhook')
        return HttpResponse(status=400)
    
    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        # Handle successful payment
        _handle_successful_payment(payment_intent)
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        # Handle failed payment
        _handle_failed_payment(payment_intent)
    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        # Handle successful subscription payment
        _handle_subscription_payment(invoice)
    else:
        logger.info(f'Unhandled Stripe webhook event type: {event["type"]}')
    
    return HttpResponse(status=200)


def _handle_successful_payment(payment_intent):
    """
    Handle successful payment intent
    """
    try:
        # Update payment transaction status
        transaction = PaymentTransaction.objects.get(
            stripe_payment_intent_id=payment_intent['id']
        )
        transaction.status = 'completed'
        transaction.completed_at = timezone.now()
        transaction.save()
        
        # Log the successful payment
        PaymentLog.objects.create(
            user=transaction.user,
            transaction=transaction,
            log_type='payment_completed',
            message=f'Payment completed: ${transaction.amount} {transaction.currency.upper()}',
        )
        
    except PaymentTransaction.DoesNotExist:
        logger.error(f'Payment transaction not found for payment_intent: {payment_intent["id"]}')


def _handle_failed_payment(payment_intent):
    """
    Handle failed payment intent
    """
    try:
        # Update payment transaction status
        transaction = PaymentTransaction.objects.get(
            stripe_payment_intent_id=payment_intent['id']
        )
        transaction.status = 'failed'
        transaction.save()
        
        # Log the failed payment
        PaymentLog.objects.create(
            user=transaction.user,
            transaction=transaction,
            log_type='payment_failed',
            message=f'Payment failed: ${transaction.amount} {transaction.currency.upper()}',
        )
        
    except PaymentTransaction.DoesNotExist:
        logger.error(f'Payment transaction not found for payment_intent: {payment_intent["id"]}')


def _handle_subscription_payment(invoice):
    """
    Handle successful subscription payment
    """
    try:
        # Find subscription by Stripe subscription ID
        subscription = Subscription.objects.get(
            stripe_subscription_id=invoice['subscription']
        )
        
        # Create payment transaction record
        PaymentTransaction.objects.create(
            user=subscription.user,
            transaction_type='subscription',
            amount=invoice['amount_paid'] / 100,  # Convert from cents
            currency=invoice['currency'],
            status='completed',
            description=f'Subscription payment for {subscription.plan} plan',
            completed_at=timezone.now(),
        )
        
        # Log the subscription payment
        PaymentLog.objects.create(
            user=subscription.user,
            log_type='subscription_payment',
            message=f'Subscription payment received: ${invoice["amount_paid"] / 100} for {subscription.plan} plan',
        )
        
    except Subscription.DoesNotExist:
        logger.error(f'Subscription not found for invoice: {invoice["id"]}')
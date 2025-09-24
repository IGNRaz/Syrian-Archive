from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
import stripe
import paypalrestsdk
import logging
from decimal import Decimal
from typing import Dict, Any, Optional
from .models import PaymentMethod, PaymentTransaction
from .settings_config import get_payment_gateway_config, PAYMENT_GATEWAYS

logger = logging.getLogger(__name__)

class PaymentGatewayError(Exception):
    """Base exception for payment gateway errors"""
    pass

class PaymentGateway:
    """Base class for payment gateways"""
    
    def __init__(self):
        self.config = PAYMENT_GATEWAYS
    
    def create_payment_method(self, user, payment_data: Dict[str, Any]) -> PaymentMethod:
        """Create a payment method for the user"""
        raise NotImplementedError
    
    def process_payment(self, amount: Decimal, payment_method: PaymentMethod, 
                      description: str = "") -> PaymentTransaction:
        """Process a payment"""
        raise NotImplementedError
    
    def create_subscription(self, user, plan_id: str, payment_method: PaymentMethod) -> Dict[str, Any]:
        """Create a subscription"""
        raise NotImplementedError
    
    def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel a subscription"""
        raise NotImplementedError
    
    def refund_payment(self, transaction_id: str, amount: Optional[Decimal] = None) -> bool:
        """Refund a payment"""
        raise NotImplementedError

class StripeGateway(PaymentGateway):
    """Stripe payment gateway implementation"""
    
    def __init__(self):
        super().__init__()
        stripe.api_key = self.config['stripe']['secret_key']
        self.publishable_key = self.config['stripe']['public_key']
    
    def create_customer(self, user):
        """Create or get Stripe customer"""
        try:
            # Check if customer already exists
            if hasattr(user, 'stripe_customer_id') and user.stripe_customer_id:
                return stripe.Customer.retrieve(user.stripe_customer_id)
            
            # Create new customer
            customer = stripe.Customer.create(
                email=user.email,
                name=f"{user.first_name} {user.last_name}".strip(),
                metadata={'user_id': user.id}
            )
            
            # Save customer ID to user profile
            user.stripe_customer_id = customer.id
            user.save()
            
            return customer
        except stripe.error.StripeError as e:
            logger.error(f"Stripe customer creation failed: {e}")
            raise PaymentGatewayError(f"Failed to create customer: {e}")
    
    def create_payment_method(self, user, payment_data: Dict[str, Any]) -> PaymentMethod:
        """Create a payment method in Stripe"""
        try:
            customer = self.create_customer(user)
            
            # Create payment method in Stripe
            stripe_pm = stripe.PaymentMethod.create(
                type='card',
                card={
                    'number': payment_data['card_number'],
                    'exp_month': payment_data['exp_month'],
                    'exp_year': payment_data['exp_year'],
                    'cvc': payment_data['cvc'],
                },
                billing_details={
                    'name': payment_data.get('cardholder_name', ''),
                    'email': user.email,
                }
            )
            
            # Attach to customer
            stripe_pm.attach(customer=customer.id)
            
            # Create local payment method record
            payment_method = PaymentMethod.objects.create(
                user=user,
                gateway='stripe',
                gateway_payment_method_id=stripe_pm.id,
                payment_type='credit_card',
                card_brand=stripe_pm.card.brand,
                card_last_four=stripe_pm.card.last4,
                card_exp_month=stripe_pm.card.exp_month,
                card_exp_year=stripe_pm.card.exp_year,
                is_default=not PaymentMethod.objects.filter(user=user).exists()
            )
            
            return payment_method
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe payment method creation failed: {e}")
            raise PaymentGatewayError(f"Failed to create payment method: {e}")
    
    def process_payment(self, amount: Decimal, payment_method: PaymentMethod, 
                      description: str = "") -> PaymentTransaction:
        """Process a payment using Stripe"""
        try:
            # Create payment intent
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency='usd',
                payment_method=payment_method.gateway_payment_method_id,
                customer=payment_method.user.stripe_customer_id,
                description=description,
                confirm=True,
                return_url=settings.SITE_URL + '/payments/return/',
            )
            
            # Create transaction record
            transaction = PaymentTransaction.objects.create(
                user=payment_method.user,
                payment_method=payment_method,
                gateway='stripe',
                gateway_transaction_id=intent.id,
                amount=amount,
                currency='USD',
                status='pending',
                description=description
            )
            
            # Update status based on intent status
            if intent.status == 'succeeded':
                transaction.status = 'completed'
                transaction.gateway_response = {'payment_intent': intent.id}
            elif intent.status == 'requires_action':
                transaction.status = 'pending'
                transaction.gateway_response = {
                    'payment_intent': intent.id,
                    'client_secret': intent.client_secret
                }
            else:
                transaction.status = 'failed'
                transaction.gateway_response = {'error': 'Payment failed'}
            
            transaction.save()
            return transaction
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe payment processing failed: {e}")
            # Create failed transaction record
            transaction = PaymentTransaction.objects.create(
                user=payment_method.user,
                payment_method=payment_method,
                gateway='stripe',
                amount=amount,
                currency='USD',
                status='failed',
                description=description,
                gateway_response={'error': str(e)}
            )
            return transaction
    
    def create_subscription(self, user, plan_id: str, payment_method: PaymentMethod) -> Dict[str, Any]:
        """Create a Stripe subscription"""
        try:
            customer = self.create_customer(user)
            
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{'price': plan_id}],
                default_payment_method=payment_method.gateway_payment_method_id,
                expand=['latest_invoice.payment_intent'],
            )
            
            return {
                'subscription_id': subscription.id,
                'status': subscription.status,
                'current_period_start': subscription.current_period_start,
                'current_period_end': subscription.current_period_end,
                'client_secret': subscription.latest_invoice.payment_intent.client_secret if subscription.latest_invoice.payment_intent else None
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription creation failed: {e}")
            raise PaymentGatewayError(f"Failed to create subscription: {e}")
    
    def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel a Stripe subscription"""
        try:
            subscription = stripe.Subscription.delete(subscription_id)
            return subscription.status == 'canceled'
        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription cancellation failed: {e}")
            return False
    
    def refund_payment(self, transaction_id: str, amount: Optional[Decimal] = None) -> bool:
        """Refund a Stripe payment"""
        try:
            refund_data = {'payment_intent': transaction_id}
            if amount:
                refund_data['amount'] = int(amount * 100)
            
            refund = stripe.Refund.create(**refund_data)
            return refund.status == 'succeeded'
        except stripe.error.StripeError as e:
            logger.error(f"Stripe refund failed: {e}")
            return False

class PayPalGateway(PaymentGateway):
    """PayPal payment gateway implementation"""
    
    def __init__(self):
        super().__init__()
        paypalrestsdk.configure({
            'mode': 'sandbox' if self.config['paypal']['sandbox'] else 'live',
            'client_id': self.config['paypal']['client_id'],
            'client_secret': self.config['paypal']['client_secret']
        })
    
    def create_payment_method(self, user, payment_data: Dict[str, Any]) -> PaymentMethod:
        """Create a PayPal payment method (vault)"""
        try:
            # Create credit card vault
            credit_card = paypalrestsdk.CreditCard({
                'type': payment_data['card_type'].lower(),
                'number': payment_data['card_number'],
                'expire_month': payment_data['exp_month'],
                'expire_year': payment_data['exp_year'],
                'cvv2': payment_data['cvc'],
                'first_name': user.first_name,
                'last_name': user.last_name,
            })
            
            if credit_card.create():
                payment_method = PaymentMethod.objects.create(
                    user=user,
                    gateway='paypal',
                    gateway_payment_method_id=credit_card.id,
                    payment_type='credit_card',
                    card_brand=payment_data['card_type'],
                    card_last_four=payment_data['card_number'][-4:],
                    card_exp_month=payment_data['exp_month'],
                    card_exp_year=payment_data['exp_year'],
                    is_default=not PaymentMethod.objects.filter(user=user).exists()
                )
                return payment_method
            else:
                raise PaymentGatewayError(f"PayPal card creation failed: {credit_card.error}")
                
        except Exception as e:
            logger.error(f"PayPal payment method creation failed: {e}")
            raise PaymentGatewayError(f"Failed to create payment method: {e}")
    
    def process_payment(self, amount: Decimal, payment_method: PaymentMethod, 
                      description: str = "") -> PaymentTransaction:
        """Process a payment using PayPal"""
        try:
            payment = paypalrestsdk.Payment({
                'intent': 'sale',
                'payer': {
                    'payment_method': 'credit_card',
                    'funding_instruments': [{
                        'credit_card_token': {
                            'credit_card_id': payment_method.gateway_payment_method_id
                        }
                    }]
                },
                'transactions': [{
                    'amount': {
                        'total': str(amount),
                        'currency': 'USD'
                    },
                    'description': description
                }]
            })
            
            # Create transaction record
            transaction = PaymentTransaction.objects.create(
                user=payment_method.user,
                payment_method=payment_method,
                gateway='paypal',
                amount=amount,
                currency='USD',
                status='pending',
                description=description
            )
            
            if payment.create():
                transaction.gateway_transaction_id = payment.id
                transaction.status = 'completed'
                transaction.gateway_response = {'payment_id': payment.id}
            else:
                transaction.status = 'failed'
                transaction.gateway_response = {'error': payment.error}
            
            transaction.save()
            return transaction
            
        except Exception as e:
            logger.error(f"PayPal payment processing failed: {e}")
            transaction = PaymentTransaction.objects.create(
                user=payment_method.user,
                payment_method=payment_method,
                gateway='paypal',
                amount=amount,
                currency='USD',
                status='failed',
                description=description,
                gateway_response={'error': str(e)}
            )
            return transaction
    
    def create_subscription(self, user, plan_id: str, payment_method: PaymentMethod) -> Dict[str, Any]:
        """Create a PayPal subscription"""
        # PayPal subscriptions are more complex and require billing plans
        # This is a simplified implementation
        raise NotImplementedError("PayPal subscriptions not implemented yet")
    
    def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel a PayPal subscription"""
        raise NotImplementedError("PayPal subscriptions not implemented yet")
    
    def refund_payment(self, transaction_id: str, amount: Optional[Decimal] = None) -> bool:
        """Refund a PayPal payment"""
        try:
            payment = paypalrestsdk.Payment.find(transaction_id)
            if payment:
                sale = payment.transactions[0].related_resources[0].sale
                refund_data = {}
                if amount:
                    refund_data['amount'] = {
                        'total': str(amount),
                        'currency': 'USD'
                    }
                
                refund = sale.refund(refund_data)
                return refund.success if hasattr(refund, 'success') else False
            return False
        except Exception as e:
            logger.error(f"PayPal refund failed: {e}")
            return False

class PaymentGatewayFactory:
    """Factory for creating payment gateway instances"""
    
    _gateways = {
        'stripe': StripeGateway,
        'paypal': PayPalGateway,
    }
    
    @classmethod
    def get_gateway(cls, gateway_name: str) -> PaymentGateway:
        """Get a payment gateway instance"""
        if gateway_name not in cls._gateways:
            raise ValueError(f"Unknown payment gateway: {gateway_name}")
        
        return cls._gateways[gateway_name]()
    
    @classmethod
    def get_default_gateway(cls) -> PaymentGateway:
        """Get the default payment gateway"""
        config = PAYMENT_GATEWAYS
        default_gateway = config.get('default_gateway', 'stripe')
        return cls.get_gateway(default_gateway)

def process_webhook(gateway_name: str, webhook_data: Dict[str, Any]) -> bool:
    """Process webhook from payment gateway"""
    try:
        gateway = PaymentGatewayFactory.get_gateway(gateway_name)
        
        if gateway_name == 'stripe':
            return _process_stripe_webhook(webhook_data)
        elif gateway_name == 'paypal':
            return _process_paypal_webhook(webhook_data)
        
        return False
    except Exception as e:
        logger.error(f"Webhook processing failed for {gateway_name}: {e}")
        return False

def _process_stripe_webhook(webhook_data: Dict[str, Any]) -> bool:
    """Process Stripe webhook"""
    event_type = webhook_data.get('type')
    
    if event_type == 'payment_intent.succeeded':
        payment_intent = webhook_data['data']['object']
        # Update transaction status
        try:
            transaction = PaymentTransaction.objects.get(
                gateway_transaction_id=payment_intent['id']
            )
            transaction.status = 'completed'
            transaction.save()
        except PaymentTransaction.DoesNotExist:
            logger.warning(f"Transaction not found for payment intent: {payment_intent['id']}")
    
    elif event_type == 'payment_intent.payment_failed':
        payment_intent = webhook_data['data']['object']
        try:
            transaction = PaymentTransaction.objects.get(
                gateway_transaction_id=payment_intent['id']
            )
            transaction.status = 'failed'
            transaction.save()
        except PaymentTransaction.DoesNotExist:
            logger.warning(f"Transaction not found for payment intent: {payment_intent['id']}")
    
    return True

def _process_paypal_webhook(webhook_data: Dict[str, Any]) -> bool:
    """Process PayPal webhook"""
    # PayPal webhook processing implementation
    event_type = webhook_data.get('event_type')
    
    if event_type == 'PAYMENT.SALE.COMPLETED':
        # Handle completed payment
        pass
    elif event_type == 'PAYMENT.SALE.DENIED':
        # Handle failed payment
        pass
    
    return True
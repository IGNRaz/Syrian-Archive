from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from decimal import Decimal
import uuid

User = get_user_model()

class PaymentMethod(models.Model):
    """Model to store user payment methods"""
    PAYMENT_TYPES = [
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('paypal', 'PayPal'),
        ('stripe', 'Stripe'),
        ('bank_transfer', 'Bank Transfer'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Card details (encrypted in production)
    card_last_four = models.CharField(max_length=4, blank=True, null=True)
    card_brand = models.CharField(max_length=20, blank=True, null=True)  # Visa, MasterCard, etc.
    card_exp_month = models.IntegerField(blank=True, null=True)
    card_exp_year = models.IntegerField(blank=True, null=True)
    
    # External payment provider IDs
    stripe_payment_method_id = models.CharField(max_length=255, blank=True, null=True)
    paypal_payment_method_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
        
    def __str__(self):
        if self.card_last_four:
            return f"{self.get_payment_type_display()} ending in {self.card_last_four}"
        return f"{self.get_payment_type_display()} - {self.user.username}"
    
    def save(self, *args, **kwargs):
        # Ensure only one default payment method per user
        if self.is_default:
            PaymentMethod.objects.filter(
                user=self.user, 
                is_default=True
            ).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)

class PaymentTransaction(models.Model):
    """Model to track all payment transactions"""
    TRANSACTION_TYPES = [
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('subscription', 'Subscription'),
        ('donation', 'Donation'),
    ]
    
    TRANSACTION_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Transaction details
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS, default='pending')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    description = models.TextField(blank=True)
    
    # External transaction IDs
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    paypal_transaction_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Metadata
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.get_transaction_type_display()} - ${self.amount} - {self.status}"

class Subscription(models.Model):
    """Model for managing user subscriptions"""
    SUBSCRIPTION_PLANS = [
        ('basic', 'Basic Plan'),
        ('premium', 'Premium Plan'),
        ('pro', 'Professional Plan'),
    ]
    
    SUBSCRIPTION_STATUS = [
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.CharField(max_length=20, choices=SUBSCRIPTION_PLANS)
    status = models.CharField(max_length=20, choices=SUBSCRIPTION_STATUS, default='active')
    
    # Subscription details
    monthly_price = models.DecimalField(max_digits=8, decimal_places=2)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(blank=True, null=True)
    next_billing_date = models.DateTimeField(blank=True, null=True)
    
    # External subscription IDs
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    paypal_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.user.username} - {self.get_plan_display()} - {self.status}"
    
    @property
    def is_active(self):
        return self.status == 'active'

class PaymentLog(models.Model):
    """Model to log all payment-related activities for audit purposes"""
    LOG_TYPES = [
        ('payment_attempt', 'Payment Attempt'),
        ('payment_success', 'Payment Success'),
        ('payment_failure', 'Payment Failure'),
        ('refund_request', 'Refund Request'),
        ('subscription_created', 'Subscription Created'),
        ('subscription_cancelled', 'Subscription Cancelled'),
        ('webhook_received', 'Webhook Received'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_logs', null=True, blank=True)
    transaction = models.ForeignKey(PaymentTransaction, on_delete=models.CASCADE, null=True, blank=True)
    
    log_type = models.CharField(max_length=30, choices=LOG_TYPES)
    message = models.TextField()
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    
    # Additional data as JSON
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.get_log_type_display()} - {self.created_at}"

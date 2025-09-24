"""Serializers for auth_payments app"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from decimal import Decimal
from .models import PaymentMethod, PaymentTransaction, Subscription

User = get_user_model()

class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for PaymentMethod model"""
    
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'payment_type', 'card_brand', 'card_last_four',
            'card_exp_month', 'card_exp_year', 'is_default', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def to_representation(self, instance):
        """Customize the serialized representation"""
        data = super().to_representation(instance)
        
        # Add display name for payment method
        if instance.payment_type == 'credit_card':
            data['display_name'] = f"{instance.card_brand} ****{instance.card_last_four}"
        else:
            data['display_name'] = instance.payment_type.replace('_', ' ').title()
        
        # Add expiry status
        if instance.card_exp_month and instance.card_exp_year:
            from datetime import datetime
            current_year = datetime.now().year
            current_month = datetime.now().month
            
            is_expired = (
                instance.card_exp_year < current_year or 
                (instance.card_exp_year == current_year and instance.card_exp_month < current_month)
            )
            data['is_expired'] = is_expired
            
            # Check if expiring soon (within 2 months)
            months_until_expiry = (instance.card_exp_year - current_year) * 12 + (instance.card_exp_month - current_month)
            data['expiring_soon'] = 0 < months_until_expiry <= 2
        
        return data

class PaymentTransactionSerializer(serializers.ModelSerializer):
    """Serializer for PaymentTransaction model"""
    
    payment_method_display = serializers.SerializerMethodField()
    amount_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentTransaction
        fields = [
            'id', 'gateway', 'gateway_transaction_id', 'amount', 'currency',
            'status', 'transaction_type', 'description', 'created_at', 'updated_at',
            'payment_method_display', 'amount_display', 'status_display'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_payment_method_display(self, obj):
        """Get display name for payment method"""
        if obj.payment_method:
            return PaymentMethodSerializer(obj.payment_method).data
        return None
    
    def get_amount_display(self, obj):
        """Get formatted amount display"""
        if obj.amount >= 0:
            return f"+{obj.currency} {obj.amount:.2f}"
        else:
            return f"-{obj.currency} {abs(obj.amount):.2f}"
    
    def get_status_display(self, obj):
        """Get human-readable status"""
        status_map = {
            'pending': 'Pending',
            'completed': 'Completed',
            'failed': 'Failed',
            'canceled': 'Canceled',
            'refunded': 'Refunded'
        }
        return status_map.get(obj.status, obj.status.title())

class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for Subscription model"""
    
    plan_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    next_billing_date = serializers.SerializerMethodField()
    days_until_renewal = serializers.SerializerMethodField()
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'plan_id', 'gateway', 'status', 'current_period_start',
            'current_period_end', 'cancel_at_period_end', 'canceled_at',
            'created_at', 'updated_at', 'plan_display', 'status_display',
            'next_billing_date', 'days_until_renewal'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_plan_display(self, obj):
        """Get plan details"""
        from .settings_config import get_subscription_plans
        
        plans = get_subscription_plans()
        plan_data = plans.get(obj.plan_id, {})
        
        return {
            'id': obj.plan_id,
            'name': plan_data.get('name', 'Unknown Plan'),
            'price': plan_data.get('price', 0),
            'currency': plan_data.get('currency', 'USD'),
            'interval': plan_data.get('interval', 'month'),
            'features': plan_data.get('features', [])
        }
    
    def get_status_display(self, obj):
        """Get human-readable status"""
        status_map = {
            'active': 'Active',
            'trialing': 'Trial',
            'past_due': 'Past Due',
            'canceled': 'Canceled',
            'unpaid': 'Unpaid',
            'incomplete': 'Incomplete'
        }
        return status_map.get(obj.status, obj.status.title())
    
    def get_next_billing_date(self, obj):
        """Get next billing date"""
        if obj.status in ['active', 'trialing'] and obj.current_period_end:
            return obj.current_period_end
        return None
    
    def get_days_until_renewal(self, obj):
        """Get days until next renewal"""
        if obj.current_period_end:
            from datetime import datetime
            days = (obj.current_period_end.date() - datetime.now().date()).days
            return max(0, days)
        return None

class CreatePaymentMethodSerializer(serializers.Serializer):
    """Serializer for creating payment methods"""
    
    gateway = serializers.ChoiceField(
        choices=['stripe', 'paypal'],
        default='stripe'
    )
    card_number = serializers.CharField(max_length=20)
    exp_month = serializers.IntegerField(min_value=1, max_value=12)
    exp_year = serializers.IntegerField(min_value=2024, max_value=2050)
    cvc = serializers.CharField(max_length=4)
    cardholder_name = serializers.CharField(max_length=100, required=False)
    card_type = serializers.CharField(max_length=20, required=False)
    
    def validate_card_number(self, value):
        """Validate card number format"""
        # Remove spaces and dashes
        card_number = ''.join(value.split()).replace('-', '')
        
        # Check if all digits
        if not card_number.isdigit():
            raise serializers.ValidationError("Card number must contain only digits")
        
        # Check length
        if len(card_number) < 13 or len(card_number) > 19:
            raise serializers.ValidationError("Invalid card number length")
        
        # Basic Luhn algorithm check
        def luhn_check(card_num):
            def digits_of(n):
                return [int(d) for d in str(n)]
            
            digits = digits_of(card_num)
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d*2))
            return checksum % 10 == 0
        
        if not luhn_check(card_number):
            raise serializers.ValidationError("Invalid card number")
        
        return card_number
    
    def validate_exp_year(self, value):
        """Validate expiration year"""
        from datetime import datetime
        current_year = datetime.now().year
        
        if value < current_year:
            raise serializers.ValidationError("Card has expired")
        
        return value
    
    def validate(self, data):
        """Validate expiration date"""
        from datetime import datetime
        
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        if data['exp_year'] == current_year and data['exp_month'] < current_month:
            raise serializers.ValidationError("Card has expired")
        
        return data

class CreatePaymentSerializer(serializers.Serializer):
    """Serializer for creating payments"""
    
    payment_method_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    currency = serializers.CharField(max_length=3, default='USD')
    description = serializers.CharField(max_length=255, required=False)
    
    def validate_payment_method_id(self, value):
        """Validate payment method exists and belongs to user"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required")
        
        try:
            payment_method = PaymentMethod.objects.get(
                id=value,
                user=request.user,
                is_active=True
            )
        except PaymentMethod.DoesNotExist:
            raise serializers.ValidationError("Payment method not found")
        
        return value

class CreateSubscriptionSerializer(serializers.Serializer):
    """Serializer for creating subscriptions"""
    
    plan_id = serializers.CharField(max_length=50)
    payment_method_id = serializers.IntegerField()
    
    def validate_plan_id(self, value):
        """Validate plan exists"""
        from .settings_config import get_subscription_plans
        
        plans = get_subscription_plans()
        if value not in plans:
            raise serializers.ValidationError("Invalid plan ID")
        
        return value
    
    def validate_payment_method_id(self, value):
        """Validate payment method exists and belongs to user"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required")
        
        try:
            payment_method = PaymentMethod.objects.get(
                id=value,
                user=request.user,
                is_active=True
            )
        except PaymentMethod.DoesNotExist:
            raise serializers.ValidationError("Payment method not found")
        
        return value
    
    def validate(self, data):
        """Validate user doesn't have active subscription"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            existing_subscription = Subscription.objects.filter(
                user=request.user,
                status__in=['active', 'trialing']
            ).first()
            
            if existing_subscription:
                raise serializers.ValidationError(
                    "User already has an active subscription"
                )
        
        return data

class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile with payment info"""
    
    payment_methods_count = serializers.SerializerMethodField()
    active_subscription = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'date_joined',
            'payment_methods_count', 'active_subscription', 'total_spent'
        ]
        read_only_fields = ['id', 'date_joined']
    
    def get_payment_methods_count(self, obj):
        """Get count of active payment methods"""
        return PaymentMethod.objects.filter(
            user=obj,
            is_active=True
        ).count()
    
    def get_active_subscription(self, obj):
        """Get active subscription info"""
        subscription = Subscription.objects.filter(
            user=obj,
            status__in=['active', 'trialing']
        ).first()
        
        if subscription:
            return SubscriptionSerializer(subscription).data
        return None
    
    def get_total_spent(self, obj):
        """Get total amount spent by user"""
        from django.db.models import Sum
        
        total = PaymentTransaction.objects.filter(
            user=obj,
            status='completed',
            amount__gt=0
        ).aggregate(total=Sum('amount'))['total']
        
        return float(total) if total else 0.0

class PaymentStatisticsSerializer(serializers.Serializer):
    """Serializer for payment statistics"""
    
    total_spent = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_refunded = serializers.DecimalField(max_digits=10, decimal_places=2)
    net_spent = serializers.DecimalField(max_digits=10, decimal_places=2)
    transaction_counts = serializers.DictField()
    monthly_spending = serializers.ListField()
    
    class Meta:
        fields = [
            'total_spent', 'total_refunded', 'net_spent',
            'transaction_counts', 'monthly_spending'
        ]
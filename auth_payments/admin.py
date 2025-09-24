from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum
from django.utils import timezone
from datetime import datetime, timedelta

from .models import PaymentMethod, PaymentTransaction, Subscription, PaymentLog

User = get_user_model()

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'payment_type', 'card_display', 'is_default', 'is_active', 'expiry_status', 'created_at']
    list_filter = ['payment_type', 'is_default', 'is_active', 'card_brand', 'created_at']
    search_fields = ['user__username', 'user__email', 'card_last_four']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']
    list_per_page = 50
    
    def user_link(self, obj):
        """Create link to user admin page"""
        url = reverse('admin:auth_user_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.email or obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__email'
    
    def card_display(self, obj):
        """Display card information"""
        if obj.payment_type == 'credit_card':
            return f"{obj.card_brand} ****{obj.card_last_four}"
        return obj.payment_type.replace('_', ' ').title()
    card_display.short_description = 'Card'
    
    def expiry_status(self, obj):
        """Show expiry status with color coding"""
        if not obj.card_exp_month or not obj.card_exp_year:
            return '-'
        
        current_date = datetime.now()
        exp_date = datetime(obj.card_exp_year, obj.card_exp_month, 1)
        
        if exp_date < current_date:
            return format_html(
                '<span style="color: red; font-weight: bold;">Expired</span>'
            )
        elif exp_date < current_date + timedelta(days=60):
            return format_html(
                '<span style="color: orange; font-weight: bold;">Expiring Soon</span>'
            )
        else:
            return format_html(
                '<span style="color: green;">Valid</span>'
            )
    expiry_status.short_description = 'Expiry Status'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'payment_type', 'is_default', 'is_active')
        }),
        ('Card Details', {
            'fields': ('card_last_four', 'card_brand', 'card_exp_month', 'card_exp_year'),
            'classes': ('collapse',)
        }),
        ('External IDs', {
            'fields': ('stripe_payment_method_id', 'paypal_payment_method_id'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'amount_display', 'status_display', 'transaction_type', 'created_at']
    list_filter = ['transaction_type', 'status', 'currency', 'created_at']
    search_fields = ['user__username', 'user__email', 'description', 'stripe_payment_intent_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']
    list_per_page = 50
    actions = ['mark_as_completed', 'mark_as_failed']
    
    def user_link(self, obj):
        """Create link to user admin page"""
        url = reverse('admin:auth_user_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.email or obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__email'
    
    def amount_display(self, obj):
        """Display amount with currency and color coding"""
        color = 'green' if obj.amount >= 0 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {:.2f}</span>',
            color, obj.currency, obj.amount
        )
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'
    
    def status_display(self, obj):
        """Display status with color coding"""
        status_colors = {
            'pending': 'orange',
            'completed': 'green',
            'failed': 'red',
            'canceled': 'gray',
            'refunded': 'blue'
        }
        color = status_colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.status.title()
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'
    
    def mark_as_completed(self, request, queryset):
        """Mark selected transactions as completed"""
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} transactions marked as completed.')
    mark_as_completed.short_description = 'Mark selected as completed'
    
    def mark_as_failed(self, request, queryset):
        """Mark selected transactions as failed"""
        updated = queryset.update(status='failed')
        self.message_user(request, f'{updated} transactions marked as failed.')
    mark_as_failed.short_description = 'Mark selected as failed'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'payment_method', 'transaction_type', 'status')
        }),
        ('Transaction Details', {
            'fields': ('amount', 'currency', 'description')
        }),
        ('External IDs', {
            'fields': ('stripe_payment_intent_id', 'paypal_transaction_id'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'plan_display', 'status_display', 'monthly_price', 'next_billing_date', 'created_at']
    list_filter = ['plan', 'status', 'start_date']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']
    list_per_page = 50
    actions = ['cancel_subscriptions', 'reactivate_subscriptions']
    
    def user_link(self, obj):
        """Create link to user admin page"""
        url = reverse('admin:auth_user_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.email or obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__email'
    
    def plan_display(self, obj):
        """Display plan with price"""
        return f"{obj.plan} (${obj.monthly_price}/month)"
    plan_display.short_description = 'Plan'
    
    def status_display(self, obj):
        """Display status with color coding"""
        status_colors = {
            'active': 'green',
            'trialing': 'blue',
            'past_due': 'orange',
            'canceled': 'red',
            'unpaid': 'red'
        }
        color = status_colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.status.title()
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'
    
    def cancel_subscriptions(self, request, queryset):
        """Cancel selected subscriptions"""
        updated = queryset.update(status='canceled')
        self.message_user(request, f'{updated} subscriptions canceled.')
    cancel_subscriptions.short_description = 'Cancel selected subscriptions'
    
    def reactivate_subscriptions(self, request, queryset):
        """Reactivate selected subscriptions"""
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} subscriptions reactivated.')
    reactivate_subscriptions.short_description = 'Reactivate selected subscriptions'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'plan', 'status')
        }),
        ('Subscription Details', {
            'fields': ('monthly_price', 'start_date', 'end_date', 'next_billing_date')
        }),
        ('External IDs', {
            'fields': ('stripe_subscription_id', 'paypal_subscription_id'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'log_type', 'message', 'ip_address', 'created_at']
    list_filter = ['log_type', 'created_at']
    search_fields = ['user__username', 'user__email', 'message', 'ip_address']
    readonly_fields = ['id', 'created_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'transaction', 'log_type')
        }),
        ('Log Details', {
            'fields': ('message', 'ip_address', 'user_agent')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

# Extend User admin to include payment information
class PaymentInline(admin.TabularInline):
    """Inline for user's payment methods"""
    model = PaymentMethod
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    fields = [
        'payment_type', 'card_brand', 'card_last_four',
        'is_default', 'is_active', 'created_at'
    ]

class TransactionInline(admin.TabularInline):
    """Inline for user's recent transactions"""
    model = PaymentTransaction
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    fields = [
        'amount', 'currency', 'status', 'transaction_type', 'created_at'
    ]
    
    def get_queryset(self, request):
        """Limit to recent transactions"""
        return super().get_queryset(request).order_by('-created_at')[:10]

class SubscriptionInline(admin.TabularInline):
    """Inline for user's subscriptions"""
    model = Subscription
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    fields = [
        'plan', 'status', 'next_billing_date', 'created_at'
    ]

class UserAdminExtended(BaseUserAdmin):
    """Extended User admin with payment information"""
    
    inlines = BaseUserAdmin.inlines + (
        PaymentInline,
        TransactionInline,
        SubscriptionInline,
    )
    
    def get_fieldsets(self, request, obj=None):
        """Add payment statistics to user admin"""
        fieldsets = list(super().get_fieldsets(request, obj))
        
        if obj:  # Editing existing user
            # Add payment statistics section
            payment_stats = (
                'Payment Statistics', {
                    'fields': (
                        'payment_methods_count', 'total_spent',
                        'active_subscription_info'
                    ),
                    'classes': ('collapse',)
                }
            )
            fieldsets.append(payment_stats)
        
        return fieldsets
    
    def get_readonly_fields(self, request, obj=None):
        """Add payment statistics as readonly fields"""
        readonly_fields = list(super().get_readonly_fields(request, obj))
        
        if obj:  # Editing existing user
            readonly_fields.extend([
                'payment_methods_count', 'total_spent',
                'active_subscription_info'
            ])
        
        return readonly_fields
    
    def payment_methods_count(self, obj):
        """Count of user's payment methods"""
        return PaymentMethod.objects.filter(
            user=obj, is_active=True
        ).count()
    payment_methods_count.short_description = 'Active Payment Methods'
    
    def total_spent(self, obj):
        """Total amount spent by user"""
        total = PaymentTransaction.objects.filter(
            user=obj, status='completed', amount__gt=0
        ).aggregate(total=Sum('amount'))['total']
        
        return f"${total:.2f}" if total else "$0.00"
    total_spent.short_description = 'Total Spent'
    
    def active_subscription_info(self, obj):
        """Active subscription information"""
        subscription = Subscription.objects.filter(
            user=obj, status__in=['active', 'trialing']
        ).first()
        
        if subscription:
            return format_html(
                '<strong>{}</strong> ({})<br>Next billing: {}',
                subscription.plan,
                subscription.status.title(),
                subscription.next_billing_date.strftime('%Y-%m-%d') if subscription.next_billing_date else 'N/A'
            )
        
        return 'No active subscription'
    active_subscription_info.short_description = 'Active Subscription'

# Unregister the default User admin and register our extended version
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

admin.site.register(User, UserAdminExtended)

# Customize admin site header and title
admin.site.site_header = 'Syrian Archive - Payment & Auth Admin'
admin.site.site_title = 'Payment & Auth Admin'
admin.site.index_title = 'Payment & Authentication Management'

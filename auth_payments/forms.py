from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import PaymentMethod, Subscription
import re
from datetime import date


class PaymentMethodForm(forms.ModelForm):
    """
    Form for adding payment methods
    """
    card_number = forms.CharField(
        max_length=19,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '1234 5678 9012 3456',
            'data-mask': '0000 0000 0000 0000'
        }),
        label='Card Number'
    )
    
    card_cvc = forms.CharField(
        max_length=4,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '123',
            'data-mask': '000'
        }),
        label='CVC'
    )
    
    cardholder_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'John Doe'
        }),
        label='Cardholder Name'
    )
    
    class Meta:
        model = PaymentMethod
        fields = ['payment_type', 'card_exp_month', 'card_exp_year', 'is_default']
        widgets = {
            'payment_type': forms.Select(attrs={'class': 'form-control'}),
            'card_exp_month': forms.Select(
                choices=[(i, f'{i:02d}') for i in range(1, 13)],
                attrs={'class': 'form-control'}
            ),
            'card_exp_year': forms.Select(
                choices=[(i, str(i)) for i in range(timezone.now().year, timezone.now().year + 20)],
                attrs={'class': 'form-control'}
            ),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_card_number(self):
        card_number = self.cleaned_data.get('card_number', '').replace(' ', '')
        
        # Basic card number validation
        if not re.match(r'^\d{13,19}$', card_number):
            raise ValidationError('Please enter a valid card number.')
        
        # Luhn algorithm validation
        if not self._luhn_check(card_number):
            raise ValidationError('Please enter a valid card number.')
        
        return card_number
    
    def clean_card_cvc(self):
        cvc = self.cleaned_data.get('card_cvc', '')
        
        if not re.match(r'^\d{3,4}$', cvc):
            raise ValidationError('Please enter a valid CVC.')
        
        return cvc
    
    def clean(self):
        cleaned_data = super().clean()
        exp_month = cleaned_data.get('card_exp_month')
        exp_year = cleaned_data.get('card_exp_year')
        
        if exp_month and exp_year:
            exp_date = date(exp_year, exp_month, 1)
            current_date = date(timezone.now().year, timezone.now().month, 1)
            
            if exp_date < current_date:
                raise ValidationError('Card expiration date cannot be in the past.')
        
        return cleaned_data
    
    def _luhn_check(self, card_number):
        """
        Validate card number using Luhn algorithm
        """
        def digits_of(n):
            return [int(d) for d in str(n)]
        
        digits = digits_of(card_number)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d*2))
        return checksum % 10 == 0


class SubscriptionForm(forms.ModelForm):
    """
    Form for creating subscriptions
    """
    PLAN_CHOICES = [
        ('basic', 'Basic Plan - $9.99/month'),
        ('premium', 'Premium Plan - $19.99/month'),
        ('enterprise', 'Enterprise Plan - $49.99/month'),
    ]
    
    plan = forms.ChoiceField(
        choices=PLAN_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='Select Plan'
    )
    
    payment_method = forms.ModelChoiceField(
        queryset=PaymentMethod.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Payment Method',
        empty_label='Select a payment method'
    )
    
    terms_accepted = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='I accept the terms and conditions'
    )
    
    class Meta:
        model = Subscription
        fields = ['plan']
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['payment_method'].queryset = PaymentMethod.objects.filter(
                user=user, 
                is_active=True
            )
    
    def clean_plan(self):
        plan = self.cleaned_data.get('plan')
        
        # Set monthly price based on plan
        plan_prices = {
            'basic': 9.99,
            'premium': 19.99,
            'enterprise': 49.99,
        }
        
        self.monthly_price = plan_prices.get(plan, 0)
        return plan
    
    def save(self, commit=True):
        subscription = super().save(commit=False)
        subscription.monthly_price = self.monthly_price
        subscription.status = 'pending'
        
        if commit:
            subscription.save()
        
        return subscription


class PaymentForm(forms.Form):
    """
    Form for one-time payments
    """
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.50,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01'
        }),
        label='Amount ($)'
    )
    
    description = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Payment description (optional)'
        }),
        label='Description'
    )
    
    payment_method = forms.ModelChoiceField(
        queryset=PaymentMethod.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Payment Method',
        empty_label='Select a payment method'
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['payment_method'].queryset = PaymentMethod.objects.filter(
                user=user, 
                is_active=True
            )
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        
        if amount and amount > 10000:
            raise ValidationError('Payment amount cannot exceed $10,000.')
        
        return amount


class BillingAddressForm(forms.Form):
    """
    Form for billing address information
    """
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='First Name'
    )
    
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Last Name'
    )
    
    address_line_1 = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Address Line 1'
    )
    
    address_line_2 = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Address Line 2 (Optional)'
    )
    
    city = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='City'
    )
    
    state = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='State/Province'
    )
    
    postal_code = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Postal Code'
    )
    
    country = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Country'
    )
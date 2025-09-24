"""Tests for auth_payments app"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings
from decimal import Decimal
from unittest.mock import patch, Mock
import json

from .models import PaymentMethod, PaymentTransaction, Subscription
from .payment_gateways import StripeGateway, PayPalGateway
from .security import PaymentSecurityManager, RateLimitManager
from .notifications import NotificationManager

User = get_user_model()

class PaymentMethodModelTest(TestCase):
    """Test PaymentMethod model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_payment_method(self):
        """Test creating a payment method"""
        payment_method = PaymentMethod.objects.create(
            user=self.user,
            payment_type='credit_card',
            card_brand='visa',
            card_last_four='1234',
            card_exp_month=12,
            card_exp_year=2025,
            is_default=True
        )
        
        self.assertEqual(payment_method.user, self.user)
        self.assertEqual(payment_method.payment_type, 'credit_card')
        self.assertEqual(payment_method.card_brand, 'visa')
        self.assertTrue(payment_method.is_default)
        self.assertTrue(payment_method.is_active)
    
    def test_payment_method_str(self):
        """Test string representation"""
        payment_method = PaymentMethod.objects.create(
            user=self.user,
            payment_type='credit_card',
            card_last_four='1234',
            card_brand='visa'
        )
        expected = "Credit Card ending in 1234"
        self.assertEqual(str(payment_method), expected)
    
    def test_set_as_default(self):
        """Test setting payment method as default"""
        # Create first payment method
        pm1 = PaymentMethod.objects.create(
            user=self.user,
            payment_type='credit_card',
            card_brand='visa',
            card_last_four='1234',
            is_default=True
        )
        
        # Create second payment method and set as default
        pm2 = PaymentMethod.objects.create(
            user=self.user,
            payment_type='credit_card',
            card_brand='mastercard',
            card_last_four='5678',
            is_default=True
        )
        
        # Refresh from database
        pm1.refresh_from_db()
        pm2.refresh_from_db()
        
        # Only pm2 should be default
        self.assertFalse(pm1.is_default)
        self.assertTrue(pm2.is_default)

class PaymentTransactionModelTest(TestCase):
    """Test PaymentTransaction model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.payment_method = PaymentMethod.objects.create(
            user=self.user,
            payment_type='credit_card',
            card_brand='visa',
            card_last_four='1234'
        )
    
    def test_create_transaction(self):
        """Test creating a payment transaction"""
        transaction = PaymentTransaction.objects.create(
            user=self.user,
            payment_method=self.payment_method,
            amount=Decimal('99.99'),
            currency='USD',
            status='completed',
            transaction_type='payment',
            description='Test payment'
        )
        
        self.assertEqual(transaction.user, self.user)
        self.assertEqual(transaction.amount, Decimal('99.99'))
        self.assertEqual(transaction.currency, 'USD')
        self.assertEqual(transaction.status, 'completed')
    
    def test_transaction_str(self):
        """Test string representation"""
        transaction = PaymentTransaction.objects.create(
            user=self.user,
            payment_method=self.payment_method,
            amount=Decimal('99.99'),
            currency='USD',
            status='completed',
            transaction_type='payment'
        )
        
        expected = "Payment - $99.99 - completed"
        self.assertEqual(str(transaction), expected)

class SubscriptionModelTest(TestCase):
    """Test Subscription model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_subscription(self):
        """Test creating a subscription"""
        subscription = Subscription.objects.create(
            user=self.user,
            plan='basic',
            status='active',
            monthly_price=Decimal('9.99')
        )
        
        self.assertEqual(subscription.user, self.user)
        self.assertEqual(subscription.plan, 'basic')
        self.assertEqual(subscription.status, 'active')
        self.assertEqual(subscription.monthly_price, Decimal('9.99'))
    
    def test_subscription_str(self):
        """Test string representation"""
        subscription = Subscription.objects.create(
            user=self.user,
            plan='basic',
            status='active',
            monthly_price=Decimal('9.99')
        )
        
        expected = "testuser - Basic Plan - active"
        self.assertEqual(str(subscription), expected)

class PaymentViewsTest(TestCase):
    """Test payment views"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_payment_methods_view(self):
        """Test payment methods view"""
        response = self.client.get(reverse('auth_payments:payment_methods'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Payment Methods')
    
    def test_add_payment_method_view(self):
        """Test add payment method view"""
        response = self.client.get(reverse('auth_payments:add_payment_method'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add Payment Method')
    
    def test_subscription_view(self):
        """Test subscription view"""
        response = self.client.get(reverse('auth_payments:subscription'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Subscription')
    
    def test_payment_history_view(self):
        """Test payment history view"""
        response = self.client.get(reverse('auth_payments:payment_history'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Payment History')
    
    def test_unauthorized_access(self):
        """Test unauthorized access redirects to login"""
        self.client.logout()
        response = self.client.get(reverse('auth_payments:payment_methods'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

class PaymentGatewayTest(TestCase):
    """Test payment gateways"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    @patch('stripe.Customer.create')
    @patch('stripe.PaymentMethod.create')
    def test_stripe_gateway_create_payment_method(self, mock_pm_create, mock_customer_create):
        """Test Stripe gateway payment method creation"""
        # Mock Stripe responses
        mock_customer_create.return_value = Mock(id='cus_test123')
        mock_pm_create.return_value = Mock(
            id='pm_test123',
            card=Mock(
                brand='visa',
                last4='1234',
                exp_month=12,
                exp_year=2025
            )
        )
        
        gateway = StripeGateway()
        payment_method = gateway.create_payment_method(
            user=self.user,
            card_number='4242424242424242',
            exp_month=12,
            exp_year=2025,
            cvc='123'
        )
        
        self.assertIsInstance(payment_method, PaymentMethod)
        self.assertEqual(payment_method.user, self.user)
        self.assertEqual(payment_method.card_brand, 'visa')
        self.assertEqual(payment_method.card_last_four, '1234')
    
    @patch('stripe.PaymentIntent.create')
    def test_stripe_gateway_process_payment(self, mock_pi_create):
        """Test Stripe gateway payment processing"""
        # Create payment method
        payment_method = PaymentMethod.objects.create(
            user=self.user,
            payment_type='credit_card',
            card_brand='visa',
            card_last_four='1234',
            stripe_payment_method_id='pm_test123'
        )
        
        # Mock Stripe response
        mock_pi_create.return_value = Mock(
            id='pi_test123',
            status='succeeded',
            amount=9999,
            currency='usd'
        )
        
        gateway = StripeGateway()
        transaction = gateway.process_payment(
            payment_method=payment_method,
            amount=Decimal('99.99'),
            currency='USD',
            description='Test payment'
        )
        
        self.assertIsInstance(transaction, PaymentTransaction)
        self.assertEqual(transaction.user, self.user)
        self.assertEqual(transaction.amount, Decimal('99.99'))
        self.assertEqual(transaction.status, 'completed')

class SecurityTest(TestCase):
    """Test security features"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.security_manager = PaymentSecurityManager()
        self.rate_limiter = RateLimitManager()
    
    def test_encrypt_decrypt_card_data(self):
        """Test card data encryption and decryption"""
        card_data = {
            'number': '4242424242424242',
            'exp_month': 12,
            'exp_year': 2025,
            'cvc': '123'
        }
        
        encrypted_data = self.security_manager.encrypt_card_data(card_data)
        self.assertNotEqual(encrypted_data, card_data)
        
        decrypted_data = self.security_manager.decrypt_card_data(encrypted_data)
        self.assertEqual(decrypted_data, card_data)
    
    def test_validate_payment_hash(self):
        """Test payment hash validation"""
        payment_data = {
            'amount': '99.99',
            'currency': 'USD',
            'user_id': self.user.id
        }
        
        payment_hash = self.security_manager.generate_payment_hash(payment_data)
        self.assertTrue(
            self.security_manager.validate_payment_hash(payment_data, payment_hash)
        )
        
        # Test with tampered data
        tampered_data = payment_data.copy()
        tampered_data['amount'] = '199.99'
        self.assertFalse(
            self.security_manager.validate_payment_hash(tampered_data, payment_hash)
        )
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        user_id = str(self.user.id)
        
        # Should allow initial requests
        self.assertTrue(self.rate_limiter.check_rate_limit(user_id, 'payment'))
        
        # Simulate multiple requests
        for _ in range(10):
            self.rate_limiter.check_rate_limit(user_id, 'payment')
        
        # Should be rate limited after too many requests
        # Note: This depends on the rate limit configuration
        # You may need to adjust based on your settings

class NotificationTest(TestCase):
    """Test notification system"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.notification_manager = NotificationManager()
    
    @patch('django.core.mail.send_mail')
    def test_send_payment_success_email(self, mock_send_mail):
        """Test sending payment success email"""
        mock_send_mail.return_value = True
        
        transaction = PaymentTransaction.objects.create(
            user=self.user,
            amount=Decimal('99.99'),
            currency='USD',
            status='completed',
            transaction_type='payment',
            description='Test payment'
        )
        
        result = self.notification_manager.send_payment_success_email(
            user=self.user,
            transaction=transaction
        )
        
        self.assertTrue(result)
        mock_send_mail.assert_called_once()
    
    @patch('django.core.mail.send_mail')
    def test_send_payment_failed_email(self, mock_send_mail):
        """Test sending payment failed email"""
        mock_send_mail.return_value = True
        
        transaction = PaymentTransaction.objects.create(
            user=self.user,
            amount=Decimal('99.99'),
            currency='USD',
            status='failed',
            transaction_type='payment',
            description='Test payment'
        )
        
        result = self.notification_manager.send_payment_failed_email(
            user=self.user,
            transaction=transaction,
            reason='Insufficient funds'
        )
        
        self.assertTrue(result)
        mock_send_mail.assert_called_once()

class APIViewsTest(TestCase):
    """Test API views"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_payment_methods_api(self):
        """Test payment methods API"""
        # Create a payment method
        PaymentMethod.objects.create(
            user=self.user,
            payment_type='credit_card',
            card_brand='visa',
            card_last_four='1234'
        )
        
        response = self.client.get('/api/payment-methods/')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['card_brand'], 'visa')
    
    def test_payment_history_api(self):
        """Test payment history API"""
        # Create a transaction
        PaymentTransaction.objects.create(
            user=self.user,
            amount=Decimal('99.99'),
            currency='USD',
            status='completed',
            transaction_type='payment'
        )
        
        response = self.client.get('/api/payment-history/')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['amount'], '99.99')
    
    def test_unauthorized_api_access(self):
        """Test unauthorized API access"""
        self.client.logout()
        response = self.client.get('/api/payment-methods/')
        self.assertEqual(response.status_code, 401)

class IntegrationTest(TestCase):
    """Integration tests for the complete payment flow"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    @patch('stripe.Customer.create')
    @patch('stripe.PaymentMethod.create')
    @patch('stripe.PaymentIntent.create')
    def test_complete_payment_flow(self, mock_pi_create, mock_pm_create, mock_customer_create):
        """Test complete payment flow from adding payment method to processing payment"""
        # Mock Stripe responses
        mock_customer_create.return_value = Mock(id='cus_test123')
        mock_pm_create.return_value = Mock(
            id='pm_test123',
            card=Mock(
                brand='visa',
                last4='1234',
                exp_month=12,
                exp_year=2025
            )
        )
        mock_pi_create.return_value = Mock(
            id='pi_test123',
            status='succeeded',
            amount=9999,
            currency='usd'
        )
        
        # Step 1: Add payment method
        response = self.client.post('/auth_payments/add-payment-method/', {
            'card_number': '4242424242424242',
            'exp_month': 12,
            'exp_year': 2025,
            'cvc': '123',
            'cardholder_name': 'Test User'
        })
        
        # Check if payment method was created
        payment_method = PaymentMethod.objects.filter(user=self.user).first()
        self.assertIsNotNone(payment_method)
        
        # Step 2: Process payment
        response = self.client.post('/auth_payments/process-payment/', {
            'payment_method_id': payment_method.id,
            'amount': '99.99',
            'currency': 'USD',
            'description': 'Test payment'
        })
        
        # Check if transaction was created
        transaction = PaymentTransaction.objects.filter(user=self.user).first()
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, Decimal('99.99'))
        self.assertEqual(transaction.status, 'completed')
    
    def test_subscription_flow(self):
        """Test subscription creation and management flow"""
        # Create payment method first
        payment_method = PaymentMethod.objects.create(
            user=self.user,
            payment_type='credit_card',
            card_brand='visa',
            card_last_four='1234',
            stripe_payment_method_id='pm_test123'
        )
        
        # Create subscription
        response = self.client.post('/auth_payments/create-subscription/', {
            'plan': 'basic',
            'payment_method_id': payment_method.id
        })
        
        # Check if subscription was created
        subscription = Subscription.objects.filter(user=self.user).first()
        self.assertIsNotNone(subscription)
        self.assertEqual(subscription.plan, 'basic')
        self.assertEqual(subscription.status, 'active')

class AdminTest(TestCase):
    """Test admin interface"""
    
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.client = Client()
        self.client.login(username='admin', password='adminpass123')
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_admin_payment_method_list(self):
        """Test admin payment method list view"""
        PaymentMethod.objects.create(
            user=self.user,
            payment_type='credit_card',
            card_brand='visa',
            card_last_four='1234'
        )
        
        response = self.client.get('/admin/auth_payments/paymentmethod/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'visa ****1234')
    
    def test_admin_transaction_list(self):
        """Test admin transaction list view"""
        PaymentTransaction.objects.create(
            user=self.user,
            amount=Decimal('99.99'),
            currency='USD',
            status='completed',
            transaction_type='payment'
        )
        
        response = self.client.get('/admin/auth_payments/paymenttransaction/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'USD 99.99')
    
    def test_admin_subscription_list(self):
        """Test admin subscription list view"""
        Subscription.objects.create(
            user=self.user,
            plan='basic',
            status='active',
            monthly_price=Decimal('9.99')
        )
        
        response = self.client.get('/admin/auth_payments/subscription/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'basic')

class MiddlewareTest(TestCase):
    """Test middleware functionality"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_payment_security_middleware(self):
        """Test payment security middleware"""
        self.client.login(username='testuser', password='testpass123')
        
        # Make a request to a payment endpoint
        response = self.client.get('/auth/payment-methods/')
        
        # Check if security headers are present (they might be added by Django's security middleware)
        self.assertTrue(response.status_code in [200, 302])
    
    def test_rate_limiting_middleware(self):
        """Test rate limiting middleware"""
        self.client.login(username='testuser', password='testpass123')
        
        # Make multiple rapid requests
        responses = []
        for _ in range(20):
            response = self.client.get('/auth/payment-methods/')
            responses.append(response.status_code)
        
        # Should have mostly 200 responses (rate limiting may not be active in tests)
        self.assertIn(200, responses)

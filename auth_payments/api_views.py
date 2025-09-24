"""API views for auth_payments app"""

from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
import logging
from decimal import Decimal
from .models import PaymentMethod, PaymentTransaction, Subscription
from .payment_gateways import PaymentGatewayFactory
from .security import PaymentSecurityManager, rate_limit, payment_security_check
from .notifications import NotificationManager
from .serializers import (
    PaymentMethodSerializer, PaymentTransactionSerializer, 
    SubscriptionSerializer, CreatePaymentSerializer
)

logger = logging.getLogger(__name__)

class PaymentMethodAPIView(APIView):
    """API for managing payment methods"""
    permission_classes = [permissions.IsAuthenticated]
    
    @method_decorator(rate_limit('payment_api', 10))
    @method_decorator(payment_security_check)
    def get(self, request):
        """Get user's payment methods"""
        try:
            payment_methods = PaymentMethod.objects.filter(
                user=request.user,
                is_active=True
            ).order_by('-is_default', '-created_at')
            
            serializer = PaymentMethodSerializer(payment_methods, many=True)
            return Response({
                'success': True,
                'payment_methods': serializer.data
            })
        
        except Exception as e:
            logger.error(f"Error fetching payment methods for user {request.user.id}: {e}")
            return Response({
                'success': False,
                'error': 'Failed to fetch payment methods'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @method_decorator(rate_limit('payment_api', 5))
    @method_decorator(payment_security_check)
    def post(self, request):
        """Add a new payment method"""
        try:
            data = request.data
            gateway_name = data.get('gateway', 'stripe')
            
            # Validate required fields
            required_fields = ['card_number', 'exp_month', 'exp_year', 'cvc']
            for field in required_fields:
                if not data.get(field):
                    return Response({
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get payment gateway
            gateway = PaymentGatewayFactory.get_gateway(gateway_name)
            
            # Create payment method
            payment_method = gateway.create_payment_method(request.user, data)
            
            # Send notification
            NotificationManager().send_payment_method_added_email(
                request.user, payment_method
            )
            
            serializer = PaymentMethodSerializer(payment_method)
            return Response({
                'success': True,
                'payment_method': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"Error creating payment method for user {request.user.id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @method_decorator(rate_limit('payment_api', 5))
    def delete(self, request, payment_method_id):
        """Delete a payment method"""
        try:
            payment_method = PaymentMethod.objects.get(
                id=payment_method_id,
                user=request.user
            )
            
            payment_method.is_active = False
            payment_method.save()
            
            return Response({
                'success': True,
                'message': 'Payment method deleted successfully'
            })
        
        except PaymentMethod.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Payment method not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            logger.error(f"Error deleting payment method {payment_method_id}: {e}")
            return Response({
                'success': False,
                'error': 'Failed to delete payment method'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PaymentProcessingAPIView(APIView):
    """API for processing payments"""
    permission_classes = [permissions.IsAuthenticated]
    
    @method_decorator(rate_limit('payment_processing', 3))
    @method_decorator(payment_security_check)
    def post(self, request):
        """Process a payment"""
        try:
            serializer = CreatePaymentSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            data = serializer.validated_data
            
            # Get payment method
            payment_method = PaymentMethod.objects.get(
                id=data['payment_method_id'],
                user=request.user,
                is_active=True
            )
            
            # Get payment gateway
            gateway = PaymentGatewayFactory.get_gateway(payment_method.gateway)
            
            # Process payment
            transaction = gateway.process_payment(
                amount=data['amount'],
                payment_method=payment_method,
                description=data.get('description', '')
            )
            
            serializer = PaymentTransactionSerializer(transaction)
            return Response({
                'success': True,
                'transaction': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        except PaymentMethod.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Payment method not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            logger.error(f"Error processing payment for user {request.user.id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class SubscriptionAPIView(APIView):
    """API for managing subscriptions"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get user's subscriptions"""
        try:
            subscriptions = Subscription.objects.filter(
                user=request.user
            ).order_by('-created_at')
            
            serializer = SubscriptionSerializer(subscriptions, many=True)
            return Response({
                'success': True,
                'subscriptions': serializer.data
            })
        
        except Exception as e:
            logger.error(f"Error fetching subscriptions for user {request.user.id}: {e}")
            return Response({
                'success': False,
                'error': 'Failed to fetch subscriptions'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @method_decorator(rate_limit('subscription_api', 3))
    @method_decorator(payment_security_check)
    def post(self, request):
        """Create a new subscription"""
        try:
            data = request.data
            plan_id = data.get('plan_id')
            payment_method_id = data.get('payment_method_id')
            
            if not plan_id or not payment_method_id:
                return Response({
                    'success': False,
                    'error': 'Missing plan_id or payment_method_id'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get payment method
            payment_method = PaymentMethod.objects.get(
                id=payment_method_id,
                user=request.user,
                is_active=True
            )
            
            # Check for existing active subscription
            existing_subscription = Subscription.objects.filter(
                user=request.user,
                status__in=['active', 'trialing']
            ).first()
            
            if existing_subscription:
                return Response({
                    'success': False,
                    'error': 'User already has an active subscription'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get payment gateway
            gateway = PaymentGatewayFactory.get_gateway(payment_method.gateway)
            
            # Create subscription
            subscription_data = gateway.create_subscription(
                request.user, plan_id, payment_method
            )
            
            # Create local subscription record
            subscription = Subscription.objects.create(
                user=request.user,
                plan_id=plan_id,
                gateway=payment_method.gateway,
                gateway_subscription_id=subscription_data['subscription_id'],
                status=subscription_data['status'],
                current_period_start=subscription_data.get('current_period_start'),
                current_period_end=subscription_data.get('current_period_end')
            )
            
            serializer = SubscriptionSerializer(subscription)
            return Response({
                'success': True,
                'subscription': serializer.data,
                'client_secret': subscription_data.get('client_secret')
            }, status=status.HTTP_201_CREATED)
        
        except PaymentMethod.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Payment method not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            logger.error(f"Error creating subscription for user {request.user.id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @method_decorator(rate_limit('subscription_api', 5))
    def delete(self, request, subscription_id):
        """Cancel a subscription"""
        try:
            subscription = Subscription.objects.get(
                id=subscription_id,
                user=request.user
            )
            
            # Cancel with payment gateway
            gateway = PaymentGatewayFactory.get_gateway(subscription.gateway)
            success = gateway.cancel_subscription(subscription.gateway_subscription_id)
            
            if success:
                subscription.status = 'canceled'
                subscription.cancel_at_period_end = True
                subscription.save()
                
                return Response({
                    'success': True,
                    'message': 'Subscription canceled successfully'
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Failed to cancel subscription with payment gateway'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except Subscription.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Subscription not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            logger.error(f"Error canceling subscription {subscription_id}: {e}")
            return Response({
                'success': False,
                'error': 'Failed to cancel subscription'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PaymentHistoryAPIView(APIView):
    """API for payment history"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get user's payment history"""
        try:
            # Pagination parameters
            page = int(request.GET.get('page', 1))
            per_page = min(int(request.GET.get('per_page', 20)), 100)
            
            # Filtering parameters
            status_filter = request.GET.get('status')
            gateway_filter = request.GET.get('gateway')
            
            # Build query
            transactions = PaymentTransaction.objects.filter(user=request.user)
            
            if status_filter:
                transactions = transactions.filter(status=status_filter)
            
            if gateway_filter:
                transactions = transactions.filter(gateway=gateway_filter)
            
            # Order by most recent
            transactions = transactions.order_by('-created_at')
            
            # Pagination
            start = (page - 1) * per_page
            end = start + per_page
            paginated_transactions = transactions[start:end]
            
            # Calculate totals
            total_count = transactions.count()
            total_pages = (total_count + per_page - 1) // per_page
            
            serializer = PaymentTransactionSerializer(paginated_transactions, many=True)
            
            return Response({
                'success': True,
                'transactions': serializer.data,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                }
            })
        
        except Exception as e:
            logger.error(f"Error fetching payment history for user {request.user.id}: {e}")
            return Response({
                'success': False,
                'error': 'Failed to fetch payment history'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@rate_limit('payment_api', 5)
def set_default_payment_method(request, payment_method_id):
    """Set a payment method as default"""
    try:
        # Remove default from all user's payment methods
        PaymentMethod.objects.filter(
            user=request.user,
            is_default=True
        ).update(is_default=False)
        
        # Set new default
        payment_method = PaymentMethod.objects.get(
            id=payment_method_id,
            user=request.user,
            is_active=True
        )
        payment_method.is_default = True
        payment_method.save()
        
        return Response({
            'success': True,
            'message': 'Default payment method updated'
        })
    
    except PaymentMethod.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Payment method not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        logger.error(f"Error setting default payment method {payment_method_id}: {e}")
        return Response({
            'success': False,
            'error': 'Failed to update default payment method'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@rate_limit('payment_api', 3)
def refund_payment(request, transaction_id):
    """Refund a payment"""
    try:
        transaction = PaymentTransaction.objects.get(
            id=transaction_id,
            user=request.user,
            status='completed'
        )
        
        amount = request.data.get('amount')
        if amount:
            amount = Decimal(str(amount))
            if amount > transaction.amount:
                return Response({
                    'success': False,
                    'error': 'Refund amount cannot exceed original payment amount'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Process refund with gateway
        gateway = PaymentGatewayFactory.get_gateway(transaction.gateway)
        success = gateway.refund_payment(
            transaction.gateway_transaction_id,
            amount
        )
        
        if success:
            # Create refund transaction record
            refund_transaction = PaymentTransaction.objects.create(
                user=request.user,
                payment_method=transaction.payment_method,
                gateway=transaction.gateway,
                amount=-(amount or transaction.amount),
                currency=transaction.currency,
                status='completed',
                transaction_type='refund',
                description=f'Refund for transaction {transaction.id}',
                related_transaction=transaction
            )
            
            return Response({
                'success': True,
                'message': 'Refund processed successfully',
                'refund_transaction_id': refund_transaction.id
            })
        else:
            return Response({
                'success': False,
                'error': 'Failed to process refund with payment gateway'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    except PaymentTransaction.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Transaction not found or not eligible for refund'
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        logger.error(f"Error processing refund for transaction {transaction_id}: {e}")
        return Response({
            'success': False,
            'error': 'Failed to process refund'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def payment_statistics(request):
    """Get payment statistics for the user"""
    try:
        from django.db.models import Sum, Count, Q
        from datetime import datetime, timedelta
        
        # Calculate statistics
        total_spent = PaymentTransaction.objects.filter(
            user=request.user,
            status='completed',
            amount__gt=0
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        total_refunded = PaymentTransaction.objects.filter(
            user=request.user,
            status='completed',
            amount__lt=0
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Monthly spending (last 12 months)
        monthly_data = []
        for i in range(12):
            month_start = datetime.now().replace(day=1) - timedelta(days=30*i)
            month_end = month_start.replace(day=28) + timedelta(days=4)
            month_end = month_end - timedelta(days=month_end.day)
            
            monthly_spent = PaymentTransaction.objects.filter(
                user=request.user,
                status='completed',
                amount__gt=0,
                created_at__gte=month_start,
                created_at__lte=month_end
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            monthly_data.append({
                'month': month_start.strftime('%Y-%m'),
                'amount': float(monthly_spent)
            })
        
        # Transaction counts
        transaction_counts = PaymentTransaction.objects.filter(
            user=request.user
        ).aggregate(
            total=Count('id'),
            successful=Count('id', filter=Q(status='completed')),
            failed=Count('id', filter=Q(status='failed')),
            pending=Count('id', filter=Q(status='pending'))
        )
        
        return Response({
            'success': True,
            'statistics': {
                'total_spent': float(total_spent),
                'total_refunded': float(abs(total_refunded)),
                'net_spent': float(total_spent + total_refunded),
                'transaction_counts': transaction_counts,
                'monthly_spending': monthly_data[::-1],  # Reverse to show oldest first
            }
        })
    
    except Exception as e:
        logger.error(f"Error calculating payment statistics for user {request.user.id}: {e}")
        return Response({
            'success': False,
            'error': 'Failed to calculate payment statistics'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
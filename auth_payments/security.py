from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser
from cryptography.fernet import Fernet
from functools import wraps
import hashlib
import hmac
import json
import logging
import re
import time
from datetime import timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Security Configuration
SECURITY_CONFIG = {
    'MAX_PAYMENT_ATTEMPTS': 3,
    'PAYMENT_ATTEMPT_WINDOW': 300,  # 5 minutes
    'MAX_LOGIN_ATTEMPTS': 5,
    'LOGIN_ATTEMPT_WINDOW': 900,  # 15 minutes
    'RATE_LIMIT_REQUESTS': 100,
    'RATE_LIMIT_WINDOW': 3600,  # 1 hour
    'SUSPICIOUS_ACTIVITY_THRESHOLD': 10,
    'IP_BAN_DURATION': 86400,  # 24 hours
}

class SecurityError(Exception):
    """Custom exception for security-related errors"""
    pass

class PaymentSecurityManager:
    """Handles payment-specific security measures"""
    
    @staticmethod
    def encrypt_sensitive_data(data: str) -> str:
        """Encrypt sensitive payment data"""
        try:
            # Use Django's SECRET_KEY to generate encryption key
            key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()[:32]
            f = Fernet(Fernet.generate_key())
            encrypted_data = f.encrypt(data.encode())
            return encrypted_data.decode()
        except Exception as e:
            logger.error(f"Encryption error: {str(e)}")
            raise SecurityError("Failed to encrypt sensitive data")
    
    @staticmethod
    def decrypt_sensitive_data(encrypted_data: str, key: str) -> str:
        """Decrypt sensitive payment data"""
        try:
            f = Fernet(key.encode())
            decrypted_data = f.decrypt(encrypted_data.encode())
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Decryption error: {str(e)}")
            raise SecurityError("Failed to decrypt sensitive data")
    
    @staticmethod
    def validate_card_number(card_number: str) -> bool:
        """Validate credit card number using Luhn algorithm"""
        # Remove spaces and non-digits
        card_number = re.sub(r'\D', '', card_number)
        
        if len(card_number) < 13 or len(card_number) > 19:
            return False
        
        # Luhn algorithm
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
        
        return luhn_check(card_number)
    
    @staticmethod
    def validate_cvv(cvv: str, card_type: str = None) -> bool:
        """Validate CVV code"""
        if not cvv or not cvv.isdigit():
            return False
        
        # American Express uses 4-digit CVV, others use 3-digit
        if card_type and card_type.lower() == 'amex':
            return len(cvv) == 4
        else:
            return len(cvv) == 3
    
    @staticmethod
    def validate_expiry_date(month: int, year: int) -> bool:
        """Validate card expiry date"""
        try:
            current_date = timezone.now().date()
            expiry_date = timezone.datetime(year, month, 1).date()
            return expiry_date >= current_date.replace(day=1)
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def generate_payment_hash(amount: float, currency: str, user_id: int, timestamp: str) -> str:
        """Generate secure hash for payment verification"""
        data = f"{amount}:{currency}:{user_id}:{timestamp}"
        return hmac.new(
            settings.SECRET_KEY.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
    
    @staticmethod
    def verify_payment_hash(amount: float, currency: str, user_id: int, timestamp: str, provided_hash: str) -> bool:
        """Verify payment hash"""
        expected_hash = PaymentSecurityManager.generate_payment_hash(amount, currency, user_id, timestamp)
        return hmac.compare_digest(expected_hash, provided_hash)

class RateLimitManager:
    """Handles rate limiting for various operations"""
    
    @staticmethod
    def get_client_ip(request) -> str:
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @staticmethod
    def is_rate_limited(key: str, max_requests: int, window: int) -> bool:
        """Check if a key is rate limited"""
        current_time = int(time.time())
        window_start = current_time - window
        
        # Get existing requests in the window
        cache_key = f"rate_limit:{key}"
        requests = cache.get(cache_key, [])
        
        # Filter requests within the window
        requests = [req_time for req_time in requests if req_time > window_start]
        
        # Check if limit exceeded
        if len(requests) >= max_requests:
            return True
        
        # Add current request
        requests.append(current_time)
        cache.set(cache_key, requests, window)
        
        return False
    
    @staticmethod
    def increment_failed_attempts(identifier: str, attempt_type: str) -> int:
        """Increment failed attempts counter"""
        cache_key = f"failed_attempts:{attempt_type}:{identifier}"
        attempts = cache.get(cache_key, 0) + 1
        
        # Set expiry based on attempt type
        if attempt_type == 'payment':
            timeout = SECURITY_CONFIG['PAYMENT_ATTEMPT_WINDOW']
        elif attempt_type == 'login':
            timeout = SECURITY_CONFIG['LOGIN_ATTEMPT_WINDOW']
        else:
            timeout = 3600  # Default 1 hour
        
        cache.set(cache_key, attempts, timeout)
        return attempts
    
    @staticmethod
    def get_failed_attempts(identifier: str, attempt_type: str) -> int:
        """Get number of failed attempts"""
        cache_key = f"failed_attempts:{attempt_type}:{identifier}"
        return cache.get(cache_key, 0)
    
    @staticmethod
    def clear_failed_attempts(identifier: str, attempt_type: str):
        """Clear failed attempts counter"""
        cache_key = f"failed_attempts:{attempt_type}:{identifier}"
        cache.delete(cache_key)

class SuspiciousActivityDetector:
    """Detects and handles suspicious activities"""
    
    @staticmethod
    def log_suspicious_activity(user, activity_type: str, details: Dict[str, Any], request=None):
        """Log suspicious activity"""
        activity_data = {
            'user_id': user.id if user and not isinstance(user, AnonymousUser) else None,
            'activity_type': activity_type,
            'details': details,
            'timestamp': timezone.now().isoformat(),
            'ip_address': RateLimitManager.get_client_ip(request) if request else None,
            'user_agent': request.META.get('HTTP_USER_AGENT') if request else None,
        }
        
        logger.warning(f"Suspicious activity detected: {json.dumps(activity_data)}")
        
        # Store in cache for analysis
        cache_key = f"suspicious_activity:{user.id if user else 'anonymous'}"
        activities = cache.get(cache_key, [])
        activities.append(activity_data)
        
        # Keep only recent activities
        one_hour_ago = timezone.now() - timedelta(hours=1)
        activities = [
            activity for activity in activities 
            if timezone.datetime.fromisoformat(activity['timestamp']) > one_hour_ago
        ]
        
        cache.set(cache_key, activities, 3600)  # Store for 1 hour
        
        # Check if threshold exceeded
        if len(activities) >= SECURITY_CONFIG['SUSPICIOUS_ACTIVITY_THRESHOLD']:
            SuspiciousActivityDetector.handle_suspicious_user(user, request)
    
    @staticmethod
    def handle_suspicious_user(user, request=None):
        """Handle user with suspicious activity"""
        if request:
            ip_address = RateLimitManager.get_client_ip(request)
            # Temporarily ban IP
            cache.set(
                f"banned_ip:{ip_address}", 
                True, 
                SECURITY_CONFIG['IP_BAN_DURATION']
            )
            logger.critical(f"IP {ip_address} temporarily banned due to suspicious activity")
        
        if user and not isinstance(user, AnonymousUser):
            # Flag user account for review
            cache.set(f"flagged_user:{user.id}", True, 86400)  # 24 hours
            logger.critical(f"User {user.id} flagged for suspicious activity")
    
    @staticmethod
    def is_ip_banned(ip_address: str) -> bool:
        """Check if IP is banned"""
        return cache.get(f"banned_ip:{ip_address}", False)
    
    @staticmethod
    def is_user_flagged(user_id: int) -> bool:
        """Check if user is flagged"""
        return cache.get(f"flagged_user:{user_id}", False)

# Decorators for security
def rate_limit(max_requests: int = None, window: int = None, per: str = 'ip'):
    """Rate limiting decorator"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Use default values if not provided
            _max_requests = max_requests or SECURITY_CONFIG['RATE_LIMIT_REQUESTS']
            _window = window or SECURITY_CONFIG['RATE_LIMIT_WINDOW']
            
            # Determine rate limit key
            if per == 'ip':
                key = RateLimitManager.get_client_ip(request)
            elif per == 'user' and request.user.is_authenticated:
                key = f"user_{request.user.id}"
            else:
                key = RateLimitManager.get_client_ip(request)
            
            if RateLimitManager.is_rate_limited(key, _max_requests, _window):
                logger.warning(f"Rate limit exceeded for {key}")
                return HttpResponseForbidden("Rate limit exceeded. Please try again later.")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def payment_security_check(view_func):
    """Security check decorator for payment views"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if IP is banned
        ip_address = RateLimitManager.get_client_ip(request)
        if SuspiciousActivityDetector.is_ip_banned(ip_address):
            logger.warning(f"Banned IP {ip_address} attempted to access payment view")
            return HttpResponseForbidden("Access denied.")
        
        # Check if user is flagged
        if request.user.is_authenticated and SuspiciousActivityDetector.is_user_flagged(request.user.id):
            logger.warning(f"Flagged user {request.user.id} attempted to access payment view")
            return HttpResponseForbidden("Account under review. Please contact support.")
        
        # Check payment attempts
        if request.user.is_authenticated:
            failed_attempts = RateLimitManager.get_failed_attempts(
                str(request.user.id), 'payment'
            )
            if failed_attempts >= SECURITY_CONFIG['MAX_PAYMENT_ATTEMPTS']:
                logger.warning(f"User {request.user.id} exceeded payment attempts")
                return HttpResponseForbidden("Too many failed payment attempts. Please try again later.")
        
        return view_func(request, *args, **kwargs)
    return wrapper

def log_payment_activity(activity_type: str):
    """Decorator to log payment activities"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            start_time = time.time()
            
            try:
                response = view_func(request, *args, **kwargs)
                
                # Log successful activity
                logger.info(f"Payment activity: {activity_type} - User: {request.user.id if request.user.is_authenticated else 'Anonymous'} - Duration: {time.time() - start_time:.2f}s")
                
                return response
            except Exception as e:
                # Log failed activity
                logger.error(f"Payment activity failed: {activity_type} - User: {request.user.id if request.user.is_authenticated else 'Anonymous'} - Error: {str(e)}")
                
                # Increment failed attempts if user is authenticated
                if request.user.is_authenticated:
                    RateLimitManager.increment_failed_attempts(
                        str(request.user.id), 'payment'
                    )
                
                # Log suspicious activity for multiple failures
                if request.user.is_authenticated:
                    failed_attempts = RateLimitManager.get_failed_attempts(
                        str(request.user.id), 'payment'
                    )
                    if failed_attempts >= 2:  # Log after 2nd failure
                        SuspiciousActivityDetector.log_suspicious_activity(
                            request.user,
                            'repeated_payment_failures',
                            {
                                'activity_type': activity_type,
                                'failed_attempts': failed_attempts,
                                'error': str(e)
                            },
                            request
                        )
                
                raise
        return wrapper
    return decorator

# Middleware for security checks
class PaymentSecurityMiddleware:
    """Middleware for payment security checks"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if accessing payment-related URLs
        if '/auth/' in request.path or '/payment/' in request.path:
            # Check IP ban
            ip_address = RateLimitManager.get_client_ip(request)
            if SuspiciousActivityDetector.is_ip_banned(ip_address):
                logger.warning(f"Banned IP {ip_address} attempted to access {request.path}")
                return HttpResponseForbidden("Access denied.")
            
            # Check user flag
            if request.user.is_authenticated and SuspiciousActivityDetector.is_user_flagged(request.user.id):
                logger.warning(f"Flagged user {request.user.id} attempted to access {request.path}")
                return HttpResponseForbidden("Account under review. Please contact support.")
        
        response = self.get_response(request)
        return response

# Utility functions
def sanitize_payment_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize payment data by removing/masking sensitive information"""
    sanitized = data.copy()
    
    # Mask credit card numbers
    if 'card_number' in sanitized:
        card_number = sanitized['card_number']
        if len(card_number) > 4:
            sanitized['card_number'] = '*' * (len(card_number) - 4) + card_number[-4:]
    
    # Remove CVV
    if 'cvv' in sanitized:
        sanitized['cvv'] = '***'
    
    # Remove sensitive keys
    sensitive_keys = ['password', 'secret', 'key', 'token']
    for key in list(sanitized.keys()):
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            sanitized[key] = '[REDACTED]'
    
    return sanitized

def validate_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """Validate webhook signature (e.g., from Stripe)"""
    try:
        expected_signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={expected_signature}", signature)
    except Exception as e:
        logger.error(f"Webhook signature validation error: {str(e)}")
        return False
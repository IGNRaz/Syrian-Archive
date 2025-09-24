from django.http import HttpResponseForbidden, JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from django.conf import settings
from .security import RateLimitManager, SuspiciousActivityDetector, SECURITY_CONFIG
from .settings_config import SECURITY_SETTINGS, get_security_setting
import logging
import json
import time
from typing import Optional

logger = logging.getLogger(__name__)

class PaymentSecurityMiddleware(MiddlewareMixin):
    """Comprehensive security middleware for payment and authentication systems"""
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.get_response = get_response
        
        # Paths that require enhanced security
        self.protected_paths = [
            '/auth/',
            '/payment/',
            '/subscription/',
            '/api/payment/',
            '/api/auth/',
            '/webhook/',
        ]
        
        # Paths that should be excluded from rate limiting
        self.rate_limit_exempt_paths = [
            '/static/',
            '/media/',
            '/favicon.ico',
            '/health/',
        ]
    
    def __call__(self, request):
        response = self.process_request(request)
        if response:
            return response
        
        response = self.get_response(request)
        return self.process_response(request, response)
    
    def process_request(self, request):
        """Process incoming request for security checks"""
        start_time = time.time()
        request._security_start_time = start_time
        
        # Get client information
        ip_address = RateLimitManager.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Store request info for logging
        request._security_info = {
            'ip_address': ip_address,
            'user_agent': user_agent,
            'path': request.path,
            'method': request.method,
        }
        
        # Check if IP is banned
        if SuspiciousActivityDetector.is_ip_banned(ip_address):
            logger.warning(f"Banned IP {ip_address} attempted to access {request.path}")
            return self._create_security_response(
                "Access denied. Your IP has been temporarily banned.",
                status=403
            )
        
        # Check if user is flagged (for authenticated users)
        if (request.user.is_authenticated and 
            not isinstance(request.user, AnonymousUser) and
            SuspiciousActivityDetector.is_user_flagged(request.user.id)):
            logger.warning(f"Flagged user {request.user.id} attempted to access {request.path}")
            return self._create_security_response(
                "Account under review. Please contact support.",
                status=403
            )
        
        # Apply rate limiting
        if self._should_apply_rate_limiting(request):
            rate_limit_response = self._check_rate_limits(request)
            if rate_limit_response:
                return rate_limit_response
        
        # Enhanced security for protected paths
        if self._is_protected_path(request.path):
            security_response = self._enhanced_security_check(request)
            if security_response:
                return security_response
        
        return None
    
    def process_response(self, request, response):
        """Process response and log security events"""
        # Calculate request duration
        start_time = getattr(request, '_security_start_time', time.time())
        duration = time.time() - start_time
        
        # Log security events
        self._log_request(request, response, duration)
        
        # Add security headers
        response = self._add_security_headers(response)
        
        # Handle failed authentication/payment attempts
        if response.status_code in [401, 403] and self._is_protected_path(request.path):
            self._handle_failed_attempt(request, response.status_code)
        
        return response
    
    def _should_apply_rate_limiting(self, request) -> bool:
        """Determine if rate limiting should be applied"""
        if not get_security_setting('RATE_LIMIT_ENABLED', True):
            return False
        
        # Skip rate limiting for exempt paths
        for exempt_path in self.rate_limit_exempt_paths:
            if request.path.startswith(exempt_path):
                return False
        
        return True
    
    def _check_rate_limits(self, request) -> Optional[JsonResponse]:
        """Check various rate limits"""
        ip_address = request._security_info['ip_address']
        
        # General rate limiting per IP
        requests_per_hour = get_security_setting('RATE_LIMIT_REQUESTS_PER_HOUR', 100)
        if RateLimitManager.is_rate_limited(f"general:{ip_address}", requests_per_hour, 3600):
            logger.warning(f"Rate limit exceeded for IP {ip_address}")
            return self._create_security_response(
                "Rate limit exceeded. Please try again later.",
                status=429
            )
        
        # More strict rate limiting for authenticated users on sensitive operations
        if request.user.is_authenticated and self._is_protected_path(request.path):
            requests_per_minute = get_security_setting('RATE_LIMIT_REQUESTS_PER_MINUTE', 10)
            user_key = f"user:{request.user.id}"
            if RateLimitManager.is_rate_limited(user_key, requests_per_minute, 60):
                logger.warning(f"User rate limit exceeded for user {request.user.id}")
                return self._create_security_response(
                    "Too many requests. Please slow down.",
                    status=429
                )
        
        return None
    
    def _is_protected_path(self, path: str) -> bool:
        """Check if path requires enhanced security"""
        return any(path.startswith(protected) for protected in self.protected_paths)
    
    def _enhanced_security_check(self, request) -> Optional[JsonResponse]:
        """Perform enhanced security checks for protected paths"""
        # Check for suspicious patterns in request
        suspicious_patterns = [
            'script',
            'javascript:',
            '<script',
            'eval(',
            'document.cookie',
            'union select',
            'drop table',
        ]
        
        # Check query parameters and POST data
        request_data = {}
        if hasattr(request, 'GET'):
            request_data.update(request.GET.dict())
        if hasattr(request, 'POST'):
            request_data.update(request.POST.dict())
        
        for key, value in request_data.items():
            if isinstance(value, str):
                value_lower = value.lower()
                for pattern in suspicious_patterns:
                    if pattern in value_lower:
                        logger.warning(
                            f"Suspicious pattern '{pattern}' detected in request from "
                            f"{request._security_info['ip_address']}"
                        )
                        
                        # Log suspicious activity
                        SuspiciousActivityDetector.log_suspicious_activity(
                            request.user if request.user.is_authenticated else None,
                            'suspicious_input_pattern',
                            {
                                'pattern': pattern,
                                'parameter': key,
                                'path': request.path,
                            },
                            request
                        )
                        
                        return self._create_security_response(
                            "Invalid request detected.",
                            status=400
                        )
        
        # Check for payment-specific security requirements
        if '/payment/' in request.path or '/subscription/' in request.path:
            return self._check_payment_security(request)
        
        return None
    
    def _check_payment_security(self, request) -> Optional[JsonResponse]:
        """Additional security checks for payment operations"""
        # Require HTTPS in production for payment operations
        if (not settings.DEBUG and 
            get_security_setting('REQUIRE_HTTPS', True) and 
            not request.is_secure()):
            logger.warning(f"Insecure payment request from {request._security_info['ip_address']}")
            return self._create_security_response(
                "Secure connection required for payment operations.",
                status=400
            )
        
        # Check payment attempt limits for authenticated users
        if request.user.is_authenticated:
            max_attempts = get_security_setting('MAX_PAYMENT_ATTEMPTS', 3)
            failed_attempts = RateLimitManager.get_failed_attempts(
                str(request.user.id), 'payment'
            )
            
            if failed_attempts >= max_attempts:
                lockout_minutes = get_security_setting('PAYMENT_ATTEMPT_LOCKOUT_MINUTES', 15)
                logger.warning(
                    f"User {request.user.id} exceeded payment attempts "
                    f"({failed_attempts}/{max_attempts})"
                )
                return self._create_security_response(
                    f"Too many failed payment attempts. Please try again in {lockout_minutes} minutes.",
                    status=429
                )
        
        return None
    
    def _handle_failed_attempt(self, request, status_code):
        """Handle failed authentication or payment attempts"""
        if not request.user.is_authenticated:
            return
        
        # Determine attempt type based on path
        if '/payment/' in request.path or '/subscription/' in request.path:
            attempt_type = 'payment'
        elif '/auth/' in request.path or '/login/' in request.path:
            attempt_type = 'login'
        else:
            attempt_type = 'general'
        
        # Increment failed attempts
        failed_attempts = RateLimitManager.increment_failed_attempts(
            str(request.user.id), attempt_type
        )
        
        # Log suspicious activity if multiple failures
        if failed_attempts >= 2:
            SuspiciousActivityDetector.log_suspicious_activity(
                request.user,
                f'repeated_{attempt_type}_failures',
                {
                    'failed_attempts': failed_attempts,
                    'status_code': status_code,
                    'path': request.path,
                },
                request
            )
    
    def _log_request(self, request, response, duration):
        """Log request for security monitoring"""
        security_info = getattr(request, '_security_info', {})
        
        log_data = {
            'ip_address': security_info.get('ip_address'),
            'user_id': request.user.id if request.user.is_authenticated else None,
            'path': security_info.get('path'),
            'method': security_info.get('method'),
            'status_code': response.status_code,
            'duration': round(duration, 3),
            'user_agent': security_info.get('user_agent', '')[:200],  # Truncate long user agents
            'timestamp': timezone.now().isoformat(),
        }
        
        # Log based on status code and path sensitivity
        if response.status_code >= 400:
            if self._is_protected_path(request.path):
                logger.warning(f"Security event: {json.dumps(log_data)}")
            else:
                logger.info(f"Request failed: {json.dumps(log_data)}")
        elif self._is_protected_path(request.path):
            logger.info(f"Protected path access: {json.dumps(log_data)}")
    
    def _add_security_headers(self, response):
        """Add security headers to response"""
        # Content Security Policy
        if not response.get('Content-Security-Policy'):
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://js.stripe.com https://checkout.stripe.com; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https://api.stripe.com; "
                "frame-src https://checkout.stripe.com https://js.stripe.com;"
            )
            response['Content-Security-Policy'] = csp
        
        # Other security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # HTTPS-related headers (only in production)
        if not settings.DEBUG and get_security_setting('REQUIRE_HTTPS', True):
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response
    
    def _create_security_response(self, message: str, status: int = 403) -> JsonResponse:
        """Create a standardized security response"""
        return JsonResponse(
            {
                'error': 'Security Error',
                'message': message,
                'status': status,
                'timestamp': timezone.now().isoformat(),
            },
            status=status
        )

class SessionSecurityMiddleware(MiddlewareMixin):
    """Middleware for session security management"""
    
    def process_request(self, request):
        """Check session security"""
        if not request.user.is_authenticated:
            return None
        
        # Check session timeout
        session_timeout = get_security_setting('SESSION_TIMEOUT_MINUTES', 60)
        last_activity = request.session.get('last_activity')
        
        if last_activity:
            last_activity_time = timezone.datetime.fromisoformat(last_activity)
            if timezone.now() - last_activity_time > timezone.timedelta(minutes=session_timeout):
                # Session expired
                request.session.flush()
                logger.info(f"Session expired for user {request.user.id}")
                return JsonResponse(
                    {
                        'error': 'Session Expired',
                        'message': 'Your session has expired. Please log in again.',
                        'redirect': '/auth/login/'
                    },
                    status=401
                )
        
        # Update last activity
        request.session['last_activity'] = timezone.now().isoformat()
        
        # Rotate session key periodically for security
        session_created = request.session.get('session_created')
        if not session_created:
            request.session['session_created'] = timezone.now().isoformat()
        else:
            created_time = timezone.datetime.fromisoformat(session_created)
            if timezone.now() - created_time > timezone.timedelta(hours=24):
                # Rotate session key daily
                request.session.cycle_key()
                request.session['session_created'] = timezone.now().isoformat()
                logger.info(f"Session key rotated for user {request.user.id}")
        
        return None

class PaymentLoggingMiddleware(MiddlewareMixin):
    """Middleware for comprehensive payment operation logging"""
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.payment_paths = [
            '/payment/',
            '/subscription/',
            '/api/payment/',
            '/webhook/stripe/',
            '/webhook/paypal/',
        ]
    
    def process_request(self, request):
        """Log payment-related requests"""
        if any(request.path.startswith(path) for path in self.payment_paths):
            # Store request start time
            request._payment_log_start = time.time()
            
            # Log payment request initiation
            logger.info(
                f"Payment operation initiated: {request.method} {request.path} "
                f"by user {request.user.id if request.user.is_authenticated else 'anonymous'} "
                f"from IP {RateLimitManager.get_client_ip(request)}"
            )
        
        return None
    
    def process_response(self, request, response):
        """Log payment operation results"""
        if (hasattr(request, '_payment_log_start') and 
            any(request.path.startswith(path) for path in self.payment_paths)):
            
            duration = time.time() - request._payment_log_start
            
            log_data = {
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'duration': round(duration, 3),
                'user_id': request.user.id if request.user.is_authenticated else None,
                'ip_address': RateLimitManager.get_client_ip(request),
                'timestamp': timezone.now().isoformat(),
            }
            
            if response.status_code >= 400:
                logger.error(f"Payment operation failed: {json.dumps(log_data)}")
            else:
                logger.info(f"Payment operation completed: {json.dumps(log_data)}")
        
        return response

class CORSMiddleware(MiddlewareMixin):
    """Custom CORS middleware for payment APIs"""
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        # Allowed origins for payment operations (should be configured per environment)
        self.allowed_origins = [
            'https://checkout.stripe.com',
            'https://js.stripe.com',
        ]
        
        # Add development origins if in debug mode
        if settings.DEBUG:
            self.allowed_origins.extend([
                'http://localhost:3000',
                'http://127.0.0.1:3000',
                'http://localhost:8000',
                'http://127.0.0.1:8000',
            ])
    
    def process_response(self, request, response):
        """Add CORS headers for payment-related requests"""
        origin = request.META.get('HTTP_ORIGIN')
        
        # Only add CORS headers for payment-related paths
        if (origin and 
            any(request.path.startswith(path) for path in ['/api/payment/', '/webhook/'])):
            
            if origin in self.allowed_origins:
                response['Access-Control-Allow-Origin'] = origin
                response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
                response['Access-Control-Allow-Headers'] = (
                    'Accept, Content-Type, Content-Length, Accept-Encoding, '
                    'X-CSRF-Token, Authorization, X-Requested-With'
                )
                response['Access-Control-Allow-Credentials'] = 'true'
                response['Access-Control-Max-Age'] = '86400'
        
        return response
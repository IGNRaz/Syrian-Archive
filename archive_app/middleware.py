from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import render
from django.utils.deprecation import MiddlewareMixin
from django.urls import resolve
from django.utils import timezone
from django.conf import settings
from .models import IPBan
from .logging_utils import file_logger

class IPBanMiddleware:
    """
    Middleware to block banned IP addresses from accessing the application
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Get client IP address
        ip_address = self.get_client_ip(request)
        
        # Check if IP is banned
        if self.is_ip_banned(ip_address):
            return render(request, 'errors/ip_banned.html', status=403)
        
        response = self.get_response(request)
        return response
    
    def get_client_ip(self, request):
        """
        Get the client's IP address from the request
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def is_ip_banned(self, ip_address):
        """
        Check if the given IP address is banned
        """
        try:
            ban = IPBan.objects.get(ip_address=ip_address, is_active=True)
            return True
        except IPBan.DoesNotExist:
            return False


class SecurityMiddleware(MiddlewareMixin):
    """Middleware to log security events and unauthorized access attempts"""
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """Process view to detect unauthorized access attempts"""
        try:
            # Get the URL name
            url_name = resolve(request.path_info).url_name
            
            # Check for admin page access attempts
            if url_name and url_name.startswith('admin_'):
                # Log admin page access attempt
                user = request.user if request.user.is_authenticated else None
                
                if not user or not hasattr(user, 'role') or user.role != 'admin':
                    # Unauthorized admin access attempt
                    file_logger.log_security(
                        ip_address=self.get_client_ip(request),
                        message=f"Unauthorized admin access attempt to {url_name}",
                        extra_data={
                            'event_type': 'unauthorized_admin_access',
                            'url_name': url_name,
                            'path': request.path_info,
                            'user_id': user.id if user else None,
                            'username': user.username if user else 'Anonymous',
                            'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown'),
                            'timestamp': timezone.now().isoformat(),
                            'severity': 'high'
                        }
                    )
                    
                    # Detect suspicious admin access patterns
                    from .signals import detect_suspicious_activity
                    detect_suspicious_activity(self.get_client_ip(request), 'unauthorized_admin_access')
                    
                else:
                    # Authorized admin access - log for audit trail
                    file_logger.log_security(
                        ip_address=self.get_client_ip(request),
                        message=f"Admin access to {url_name} by {user.username}",
                        extra_data={
                            'event_type': 'admin_access',
                            'url_name': url_name,
                            'path': request.path_info,
                            'user_id': user.id,
                            'username': user.username,
                            'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown'),
                            'timestamp': timezone.now().isoformat(),
                            'severity': 'info'
                        }
                    )
            
            # Check for suspicious request patterns
            if request.method == 'POST':
                # Log POST requests to sensitive endpoints
                sensitive_endpoints = ['login', 'register', 'password_reset', 'admin_']
                if any(endpoint in request.path_info for endpoint in sensitive_endpoints):
                    file_logger.log_security(
                        ip_address=self.get_client_ip(request),
                        message=f"POST request to sensitive endpoint: {request.path_info}",
                        extra_data={
                            'event_type': 'sensitive_post_request',
                            'path': request.path_info,
                            'method': request.method,
                            'user_id': request.user.id if request.user.is_authenticated else None,
                            'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown'),
                            'timestamp': timezone.now().isoformat()
                        }
                    )
                    
        except Exception as e:
            # Don't let middleware errors break the application
            print(f"SecurityMiddleware error: {e}")
        
        return None
    
    def process_exception(self, request, exception):
        """Log security-related exceptions"""
        try:
            # Log security-related exceptions
            if isinstance(exception, (PermissionError, HttpResponseForbidden)):
                file_logger.log_security(
                    ip_address=self.get_client_ip(request),
                    message=f"Security exception: {type(exception).__name__}",
                    extra_data={
                        'event_type': 'security_exception',
                        'exception_type': type(exception).__name__,
                        'exception_message': str(exception),
                        'path': request.path_info,
                        'user_id': request.user.id if request.user.is_authenticated else None,
                        'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown'),
                        'timestamp': timezone.now().isoformat(),
                        'severity': 'medium'
                    }
                )
        except Exception as e:
            print(f"SecurityMiddleware exception logging error: {e}")
        
        return None


class HostNormalizeMiddleware:
    """
    In DEBUG, normalize 127.0.0.1 to localhost to avoid OAuth redirect_uri mismatches.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            if getattr(settings, 'DEBUG', False):
                host = request.get_host() or ''
                if host.startswith('127.0.0.1'):
                    parts = host.split(':', 1)
                    port = f":{parts[1]}" if len(parts) == 2 else ''
                    new_url = f"http://localhost{port}{request.get_full_path()}"
                    return HttpResponseRedirect(new_url)
        except Exception:
            pass

        return self.get_response(request)
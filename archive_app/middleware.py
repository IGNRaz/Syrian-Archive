from django.http import HttpResponseForbidden
from django.shortcuts import render
from .models import IPBan

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
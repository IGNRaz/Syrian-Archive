import logging
from django.db.models.signals import post_migrate, pre_migrate
from django.core.signals import request_started, request_finished
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
from .logging_utils import file_logger


@receiver(post_migrate)
def log_migration_complete(sender, **kwargs):
    """Log when database migrations are completed"""
    try:
        if sender.name == 'archive_app':
            file_logger.log_server(
                message=f"Database migrations completed for {sender.name}",
                extra_data={
                    'app_name': sender.name,
                    'migration_time': str(timezone.now()),
                    'verbosity': kwargs.get('verbosity', 1)
                }
            )
    except Exception as e:
        logging.error(f"Failed to log migration completion: {str(e)}")


@receiver(pre_migrate)
def log_migration_start(sender, **kwargs):
    """Log when database migrations start"""
    try:
        if sender.name == 'archive_app':
            file_logger.log_server(
                message=f"Database migrations starting for {sender.name}",
                extra_data={
                    'app_name': sender.name,
                    'migration_start_time': str(timezone.now()),
                    'verbosity': kwargs.get('verbosity', 1)
                }
            )
    except Exception as e:
        logging.error(f"Failed to log migration start: {str(e)}")


# Log critical system events
def log_server_shutdown():
    """Log server shutdown event"""
    try:
        file_logger.log_server(
            message="Syrian Archive server shutting down",
            extra_data={
                'shutdown_time': str(timezone.now()),
                'debug_mode': getattr(settings, 'DEBUG', False)
            }
        )
    except Exception as e:
        logging.error(f"Failed to log server shutdown: {str(e)}")


def log_critical_error(error_message, error_type=None, extra_context=None):
    """Log critical system errors"""
    try:
        file_logger.log_server(
            message=f"CRITICAL ERROR: {error_message}",
            extra_data={
                'error_type': error_type or 'Unknown',
                'error_time': str(timezone.now()),
                'context': extra_context or {},
                'debug_mode': getattr(settings, 'DEBUG', False)
            }
        )
    except Exception as e:
        logging.error(f"Failed to log critical error: {str(e)}")


def detect_suspicious_activity(ip_address, activity_type='failed_login'):
    """Detect and log suspicious activities based on patterns"""
    try:
        from django.core.cache import cache
        import time
        
        # Track failed login attempts per IP
        cache_key = f"security_{activity_type}_{ip_address}"
        attempts = cache.get(cache_key, [])
        current_time = time.time()
        
        # Remove attempts older than 1 hour
        attempts = [attempt_time for attempt_time in attempts if current_time - attempt_time < 3600]
        
        # Add current attempt
        attempts.append(current_time)
        
        # Store updated attempts (expire in 1 hour)
        cache.set(cache_key, attempts, 3600)
        
        # Check for suspicious patterns
        if len(attempts) >= 5:  # 5 or more attempts in 1 hour
            file_logger.log_security(
                ip_address=ip_address,
                message=f"Suspicious activity detected: {len(attempts)} {activity_type} attempts from IP {ip_address}",
                extra_data={
                    'event_type': 'suspicious_activity',
                    'activity_type': activity_type,
                    'attempt_count': len(attempts),
                    'time_window': '1_hour',
                    'timestamp': timezone.now().isoformat(),
                    'requires_attention': True
                }
            )
            
        if len(attempts) >= 10:  # 10 or more attempts - critical
            file_logger.log_security(
                ip_address=ip_address,
                message=f"CRITICAL: Potential brute force attack from IP {ip_address} - {len(attempts)} attempts",
                extra_data={
                    'event_type': 'potential_brute_force',
                    'activity_type': activity_type,
                    'attempt_count': len(attempts),
                    'severity': 'critical',
                    'timestamp': timezone.now().isoformat(),
                    'action_required': True
                }
            )
            
    except Exception as e:
        # Fallback logging if detection fails
        print(f"Failed to detect suspicious activity: {e}")
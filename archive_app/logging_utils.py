import os
import logging
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

class FileLogger:
    """
    Custom file logger for Syrian Archive system events
    """
    
    def __init__(self):
        self.logs_dir = os.path.join(settings.BASE_DIR, 'logs')
        self.ensure_logs_directory()
    
    def ensure_logs_directory(self):
        """Create logs directory if it doesn't exist"""
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)
    
    def get_log_filename(self, log_type):
        """Generate log filename based on type and current date"""
        today = timezone.now().strftime('%Y-%m-%d')
        
        # Map log types to specific filenames
        log_file_mapping = {
            'authentication': f'user_auth_{today}.log',
            'user_actions': f'user_actions_{today}.log',
            'admin_actions': f'admin_actions_{today}.log',
            'post_actions': f'post_actions_{today}.log',
            'security': f'security_{today}.log',
            'system': f'server_{today}.log',
            'server': f'server_{today}.log',
            'password_reset_links': f'password_reset_links_{today}.log'
        }
        
        filename = log_file_mapping.get(log_type, f'{log_type}_{today}.log')
        return os.path.join(self.logs_dir, filename)
    
    def write_log(self, log_type, message, user=None, ip_address=None, extra_data=None):
        """Write log entry to file"""
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        log_filename = self.get_log_filename(log_type)
        
        # Format structured log entry
        log_parts = []
        log_parts.append(f"[{timestamp}]")
        log_parts.append(f"[{log_type.upper()}]")
        
        if user:
            log_parts.append(f"USER:{user.username}(ID:{user.id},ROLE:{user.role})")
        
        if ip_address:
            log_parts.append(f"IP:{ip_address}")
        
        log_parts.append(f"EVENT:{message}")
        
        if extra_data:
            log_parts.append(f"DATA:{extra_data}")
        
        log_entry = " | ".join(log_parts) + "\n"
        
        # Write to file
        try:
            with open(log_filename, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            # Fallback to Django logging if file writing fails
            logging.error(f"Failed to write to log file {log_filename}: {str(e)}")
    
    def log_authentication(self, event_type, user=None, ip_address=None, extra_info=None):
        """Log authentication events (login, logout, password reset, etc.)"""
        message = f"Authentication Event: {event_type}"
        if extra_info:
            message += f" - {extra_info}"
        self.write_log('authentication', message, user, ip_address, extra_info)
    
    def log_password_reset(self, user, ip_address, reset_link=None):
        """Log password reset requests"""
        extra_data = {
            'email': user.email,
            'reset_link': reset_link if reset_link else 'Generated but not logged for security'
        }
        self.log_authentication(
            'PASSWORD_RESET_REQUESTED', 
            user, 
            ip_address, 
            f"Password reset requested for email: {user.email}"
        )
    
    def log_password_reset_link(self, user, ip_address, reset_link, user_agent=None):
        """Log password reset links to dedicated file"""
        extra_data = {
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'reset_link': reset_link,
            'user_agent': user_agent or 'Unknown'
        }
        
        message = f"Password reset link generated for user: {user.username} ({user.email})"
        
        self.write_log(
            log_type='password_reset_links',
            message=message,
            user=user,
            ip_address=ip_address,
            extra_data=extra_data
        )
    
    def log_user_action(self, action_type, user, ip_address=None, target=None, details=None):
        """Log general user actions"""
        message = f"User Action: {action_type}"
        if target:
            message += f" | Target: {target}"
        if details:
            message += f" | Details: {details}"
        
        self.write_log('user_actions', message, user, ip_address, details)
    
    def log_admin_action(self, action_type, admin_user, target_user=None, ip_address=None, details=None):
        """Log admin actions"""
        message = f"Admin Action: {action_type}"
        if target_user:
            message += f" | Target User: {target_user.username} (ID: {target_user.id})"
        if details:
            message += f" | Details: {details}"
        
        self.write_log('admin_actions', message, admin_user, ip_address, details)
    
    def log_post_action(self, action_type, user, post_id, ip_address=None, details=None):
        """Log post-related actions"""
        message = f"Post Action: {action_type} | Post ID: {post_id}"
        if details:
            message += f" | Details: {details}"
        
        self.write_log('post_actions', message, user, ip_address, details)
    
    def log_security_event(self, event_type, ip_address, user=None, details=None):
        """Log security-related events"""
        message = f"Security Event: {event_type}"
        if details:
            message += f" | Details: {details}"
        
        self.write_log('security', message, user, ip_address, details)
    
    def log_system_event(self, event_type, details=None):
        """Log system events"""
        message = f"System Event: {event_type}"
        if details:
            message += f" | Details: {details}"
        
        self.write_log('system', message, extra_data=details)
    
    def log_server(self, message=None, extra_data=None):
        """Log server events (startup, shutdown, critical system events)"""
        self.write_log('server', message, None, None, extra_data)
    
    def log_user_action(self, user=None, ip_address=None, message=None, extra_data=None):
        """Log user actions (post creation, editing, submission, etc.)"""
        self.write_log('user_action', message, user, ip_address, extra_data)
    
    def log_security(self, ip_address=None, message=None, extra_data=None):
        """Log security events (failed logins, suspicious activities, etc.)"""
        self.write_log('security', message, None, ip_address, extra_data)
    
    def get_recent_logs(self, log_type, lines=50):
        """Get recent log entries from a specific log type"""
        log_filename = self.get_log_filename(log_type)
        
        if not os.path.exists(log_filename):
            return []
        
        try:
            with open(log_filename, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                return all_lines[-lines:] if len(all_lines) > lines else all_lines
        except Exception as e:
            logging.error(f"Failed to read log file {log_filename}: {str(e)}")
            return []
    
    def search_logs(self, log_type, search_term, max_results=100):
        """Search for specific terms in log files"""
        log_filename = self.get_log_filename(log_type)
        
        if not os.path.exists(log_filename):
            return []
        
        results = []
        try:
            with open(log_filename, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if search_term.lower() in line.lower():
                        results.append({
                            'line_number': line_num,
                            'content': line.strip(),
                            'timestamp': line.split(']')[0][1:] if ']' in line else 'Unknown'
                        })
                        if len(results) >= max_results:
                            break
        except Exception as e:
            logging.error(f"Failed to search log file {log_filename}: {str(e)}")
        
        return results

# Global logger instance
file_logger = FileLogger()

# Convenience functions
def log_password_reset(user, ip_address, reset_link=None):
    """Convenience function to log password reset"""
    file_logger.log_password_reset(user, ip_address, reset_link)

def log_user_login(user, ip_address, success=True):
    """Log user login attempts"""
    event_type = 'LOGIN_SUCCESS' if success else 'LOGIN_FAILED'
    file_logger.log_authentication(
        event_type=event_type,
        user=user,
        ip_address=ip_address
    )

def log_user_logout(user, ip_address):
    """Log user logout"""
    file_logger.log_authentication(
        event_type='LOGOUT',
        user=user,
        ip_address=ip_address
    )

def log_user_registration(user, ip_address):
    """Log user registration"""
    file_logger.log_authentication(
        event_type='USER_REGISTERED',
        user=user,
        ip_address=ip_address,
        extra_info={'message': f"New user registered: {user.username}"}
    )

def log_post_creation(user, post_id, ip_address):
    """Log post creation"""
    file_logger.log_post_action('POST_CREATED', user, post_id, ip_address)

def log_post_verification(user, post_id, verification_type, ip_address):
    """Log post verification"""
    file_logger.log_post_action('POST_VERIFIED', user, post_id, ip_address, f"Verification type: {verification_type}")

def log_admin_action(action_type, admin_user, target_user=None, ip_address=None, details=None):
    """Log admin actions"""
    file_logger.log_admin_action(action_type, admin_user, target_user, ip_address, details)

def log_security_event(event_type, ip_address, user=None, details=None):
    """Log security events"""
    file_logger.log_security_event(event_type, ip_address, user, details)
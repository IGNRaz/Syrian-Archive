import os
import logging
from django.conf import settings


def ensure_logs_dir_and_files():
    """Ensure the logs directory and common log files exist."""
    try:
        logs_dir = os.path.join(settings.BASE_DIR, 'logs')
        os.makedirs(logs_dir, exist_ok=True)

        files = [
            'django.log',
            'authentication.log',
            'user_actions.log',
            'admin_actions.log',
            'post_actions.log',
            'security.log',
            'system.log',
            'server.log',
            'password_reset_links.log',
        ]
        for name in files:
            path = os.path.join(logs_dir, name)
            if not os.path.exists(path):
                # touch the file
                with open(path, 'a', encoding='utf-8'):
                    pass
    except Exception as e:
        logging.error(f"Failed to ensure logs dir/files: {e}")
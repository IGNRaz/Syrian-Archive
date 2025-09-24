"""
WSGI config for syrian_archive project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import atexit

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'syrian_archive.settings')

application = get_wsgi_application()

# Register shutdown logging
try:
    from archive_app.signals import log_server_shutdown
    atexit.register(log_server_shutdown)
except ImportError:
    pass  # App may not be ready yet

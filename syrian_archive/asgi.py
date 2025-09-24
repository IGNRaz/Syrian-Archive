"""
ASGI config for syrian_archive project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
import atexit

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'syrian_archive.settings')

application = get_asgi_application()

# Register shutdown logging
try:
    from archive_app.signals import log_server_shutdown
    atexit.register(log_server_shutdown)
except ImportError:
    pass  # App may not be ready yet

from django.apps import AppConfig
import logging
from django.conf import settings
from django.utils import timezone


class ArchiveAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'archive_app'
    
    def ready(self):
        """Called when Django starts up"""
        # Ensure logs directory and common files exist
        try:
            from .startup_logging import ensure_logs_dir_and_files
            ensure_logs_dir_and_files()
        except Exception as e:
            logging.error(f"Failed to ensure logs dir/files at startup: {str(e)}")
        try:
            from .logging_utils import file_logger
            file_logger.log_server(
                message="Syrian Archive application started successfully",
                extra_data={
                    'app_name': self.name,
                    'startup_time': str(timezone.now()),
                    'debug_mode': getattr(settings, 'DEBUG', False)
                }
            )
        except Exception as e:
            logging.error(f"Failed to log application startup: {str(e)}")
            
        # Import signal handlers
        from . import signals

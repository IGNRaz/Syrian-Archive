import logging
from typing import Any, Dict, Optional

from django.contrib.auth import get_user_model
from django.http import HttpRequest
from allauth.account.adapter import DefaultAccountAdapter

from archive_app.logging_utils import file_logger


def _get_client_ip(request: Optional[HttpRequest]) -> Optional[str]:
    if not request:
        return None
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Extend Allauth adapter to log password reset links to dedicated file.
    """

    def send_mail(self, template_prefix: str, email: str, context: Dict[str, Any]) -> None:
        try:
            # Detect password reset email template and extract reset URL
            # Common template prefixes: 'account/email/password_reset_key'
            if 'password_reset' in template_prefix:
                reset_link = (
                    context.get('password_reset_url')
                    or context.get('url')
                    or context.get('reset_url')
                )
                request: Optional[HttpRequest] = context.get('request')
                user = context.get('user')
                # Fallback: try to resolve user by recipient email
                if user is None:
                    try:
                        User = get_user_model()
                        user = User.objects.filter(email=email).first()
                    except Exception:
                        user = None

                user_agent = request.META.get('HTTP_USER_AGENT') if request else None
                ip = _get_client_ip(request)

                if reset_link and user:
                    file_logger.log_password_reset_link(
                        user=user,
                        ip_address=ip,
                        reset_link=reset_link,
                        user_agent=user_agent,
                    )
                else:
                    # If we cannot resolve user or link, at least log an authentication event
                    file_logger.log_authentication(
                        event_type='PASSWORD_RESET_LINK_GENERATED',
                        user=user,
                        ip_address=ip,
                        extra_info={'email': email, 'note': 'reset link captured but user/link missing'}
                    )
        except Exception as e:
            logging.error(f"Failed to log password reset link: {e}")

        # Always proceed with normal email sending
        super().send_mail(template_prefix, email, context)
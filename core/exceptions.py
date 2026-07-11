import logging
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Delegates to DRF's default handler, which already returns authentication
    errors as {"detail": "<message>"}. Previously this forced every
    AuthenticationFailed exception's message to a single generic
    "User session has been invalidated" string, which also overwrote
    unrelated errors like wrong-password login attempts. The genuinely
    invalidated-session case (see ValidatedJWTAuthentication) already raises
    with that exact message itself, so no override is needed here.
    """
    return exception_handler(exc, context)

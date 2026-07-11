import logging

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import PermissionDenied

from services.token_service import store_refresh_token, delete_refresh_token, store_access_token, delete_access_token

logger = logging.getLogger(__name__)


def login_user(user):
    logger.info(f"Logging in user: {user.email}")
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token
    store_refresh_token(user.id, str(refresh))
    store_access_token(user.id, str(access))
    logger.info(f"User logged in successfully: {user.email}")
    return refresh, access


def logout_user(*, refresh_token, access_token, request_user):
    logger.info(f"Logging out user: {request_user.email}")
    try:
        token = RefreshToken(refresh_token)
        uid = token.get("user_id") or token.get("user")
        if uid and str(uid) != str(request_user.id):
            logger.warning(f"Token mismatch during logout for user: {request_user.email}")
            raise PermissionDenied("Token does not belong to user")
    except Exception as e:
        logger.error(f"Error during logout token validation: {str(e)}")
        pass

    delete_refresh_token(refresh_token)
    if access_token:
        delete_access_token(access_token)
    logger.info(f"User logged out successfully: {request_user.email}")

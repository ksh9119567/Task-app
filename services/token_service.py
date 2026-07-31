import redis
import logging

from datetime import timedelta

from django.conf import settings

from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)

REDIS_KEY_PREFIX = "refresh:"
REDIS_ACCESS_TOKEN_PREFIX = "access:"
REDIS_USER_SESSIONS_PREFIX = "user_sessions:"

def store_refresh_token(user_id, refresh_token, ttl=None):
    """Store refresh token in Redis with expiry."""
    logger.debug(f"Storing refresh token for user {user_id}")
    # prefer configured lifetime if available
    if ttl is None:    
        try:
            ttl = int(settings.SIMPLE_JWT.get("REFRESH_TOKEN_LIFETIME", timedelta(days=1)).total_seconds())
        except Exception:
            ttl = int(timedelta(days=1).total_seconds())
    key = f"{REDIS_KEY_PREFIX}{refresh_token}"
    settings.REDIS_CLIENT.setex(key, ttl, str(user_id))
    logger.info(f"Refresh token stored successfully for user {user_id}")


def store_access_token(user_id, access_token):
    """Store access token in Redis with expiry to track active sessions."""
    logger.debug(f"Storing access token for user {user_id}")
    try:
        ttl = int(settings.SIMPLE_JWT.get("ACCESS_TOKEN_LIFETIME", timedelta(minutes=30)).total_seconds())
    except Exception:
        ttl = int(timedelta(minutes=30).total_seconds())
    key = f"{REDIS_ACCESS_TOKEN_PREFIX}{access_token}"
    settings.REDIS_CLIENT.setex(key, ttl, str(user_id))
    logger.info(f"Access token stored successfully for user {user_id}")


def is_access_token_valid(access_token):
    """Check if access token exists in Redis (user hasn't logged out)."""
    logger.debug("Validating access token")
    key = f"{REDIS_ACCESS_TOKEN_PREFIX}{access_token}"
    val = settings.REDIS_CLIENT.exists(key)
    is_valid = bool(val)
    logger.debug(f"Access token validation result: {is_valid}")
    return is_valid


def is_refresh_token_valid(refresh_token):
    """Check if refresh token exists in Redis."""
    logger.debug("Validating refresh token")
    key = f"{REDIS_KEY_PREFIX}{refresh_token}"
    # redis-py returns int count for exists in older clients, newer return bool
    val = settings.REDIS_CLIENT.exists(key)
    is_valid = bool(val)
    logger.debug(f"Refresh token validation result: {is_valid}")
    return is_valid


def delete_refresh_token(refresh_token):
    """Invalidate refresh token on logout."""
    logger.debug("Deleting refresh token")
    key = f"{REDIS_KEY_PREFIX}{refresh_token}"
    settings.REDIS_CLIENT.delete(key)
    logger.info("Refresh token deleted successfully")


def delete_access_token(access_token):
    """Invalidate access token on logout."""
    logger.debug("Deleting access token")
    key = f"{REDIS_ACCESS_TOKEN_PREFIX}{access_token}"
    settings.REDIS_CLIENT.delete(key)
    logger.info("Access token deleted successfully")

import uuid
import logging

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone

logger = logging.getLogger(__name__)


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        logger.info(f"Creating user with email: {email}")
        if not email:
            logger.error("Email is required for user creation")
            raise ValueError("Email is required")
        if not password:
            logger.error("Password is required for user creation")
            raise ValueError("Password is required")
        
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        logger.info(f"User created successfully: {email}")
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        logger.info(f"Creating superuser with email: {email}")
        if not password:
            logger.error("Superuser must have a password")
            raise ValueError("Superuser must have a password")

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            logger.error("Superuser must have is_staff=True")
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            logger.error("Superuser must have is_superuser=True")
            raise ValueError("Superuser must have is_superuser=True.")

        user = self.create_user(email, password, **extra_fields)
        logger.info(f"Superuser created successfully: {email}")
        return user
        
        
class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, blank=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True)
    phone_no = models.CharField(max_length=20, blank=True, null=True)

    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False) # Soft delete flag
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # Django will only ask for email + password in createsuperuser

    def __str__(self):
        return self.email

    @property
    def phone_number(self):
        """Alias for `phone_no` so callers can use `phone_number` consistently."""
        return self.phone_no

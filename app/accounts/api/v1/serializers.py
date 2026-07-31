import re
from datetime import timedelta

from rest_framework import serializers
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer, TokenObtainSerializer, TokenRefreshSerializer
)

from django.conf import settings
from django.contrib.auth.models import update_last_login
from django.contrib.auth.password_validation import validate_password

from app.accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source="phone_no", read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "username", "first_name", "last_name", "profile_picture", "phone_number", 
                  "is_email_verified", "is_phone_verified", "is_active", "is_staff", "date_joined"]
        read_only_fields = ["id"]


class UserUpdateSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source="phone_no", required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "profile_picture", "phone_number"]
        
    def validate_phone_number(self, value):
        user = self.instance
        phone = re.sub(r'[\s\-\(\)]', '', value)
        if not re.match(r'^\+?1?\d{9,15}$', phone):
            raise serializers.ValidationError("Enter a valid phone number.")
        
        if value and User.objects.filter(phone_no=value).exclude(id=user.id).exists():
            raise serializers.ValidationError("Phone number is already in use.")
        
        return value
    
    def update(self, instance, validated_data):
        phone_no = validated_data.pop("phone_no", None)
        if phone_no is not None:
            instance.phone_no = phone_no
            instance.is_phone_verified = False  # Mark as unverified if phone number changes
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    phone_number = serializers.CharField(required=False, allow_blank=True, write_only=True, source="phone_no")

    class Meta:
        model = User
        fields = ["email", "username", "first_name", "last_name", "password", "phone_number"]

    def create(self, validated_data):
        # serializer `source` mapping puts phone_no into validated_data when provided
        password = validated_data.pop("password")
        user = User.objects.create_user(**validated_data, password=password)
        # note: user.is_email_verified remains False until OTP verified
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    remember_me = serializers.BooleanField(default=False, required=False, write_only=True)
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token['email'] = user.email
        token['username'] = user.username
        return token
    
    def validate(self, attrs):
        data = TokenObtainSerializer.validate(self, attrs)
        remember_me = attrs.get('remember_me', False)
        refresh = self.get_token(self.user)
        refresh['remember_me'] = remember_me
        lifetime = (
            settings.SIMPLE_JWT['REFRESH_TOKEN_REMEMBER_ME_LIFETIME']
            if remember_me else
            settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']
        )
        refresh.set_exp(lifetime=lifetime)
        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)
        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, self.user)
        return data
    

class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        refresh = self.token_class(attrs['refresh'])
        remember_me = bool(refresh.get('remember_me', False))
        data = {'access': str(refresh.access_token)}
        if api_settings.ROTATE_REFRESH_TOKENS:
            if api_settings.BLACKLIST_AFTER_ROTATION:
                try:
                    refresh.blacklist()
                except AttributeError:
                    pass
            refresh.set_jti()
            refresh.set_iat()
            lifetime = (
                settings.SIMPLE_JWT['REFRESH_TOKEN_REMEMBER_ME_LIFETIME']
                if remember_me else
                settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']
            )
            refresh.set_exp(lifetime=lifetime)
            refresh['remember_me'] = remember_me
            data['refresh'] = str(refresh)
        return data


class GetOTPSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["email", "phone"])
    identifier = serializers.CharField()
    purpose = serializers.ChoiceField(choices=["login", "verify"])


class VerifyOTPSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["email", "phone"])
    identifier = serializers.CharField()  # email or phone
    otp = serializers.CharField()


class ForgotPasswordRequestSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["email", "phone"])
    identifier = serializers.CharField()


class ForgotPasswordVerifySerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["email", "phone"])
    identifier = serializers.CharField()
    otp = serializers.CharField()


class ForgotPasswordResetSerializer(serializers.Serializer):
    reset_token = serializers.CharField()
    new_password = serializers.CharField()

    def validate_new_password(self, value):
        validate_password(value)
        return value

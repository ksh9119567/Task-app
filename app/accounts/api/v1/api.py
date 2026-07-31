import logging
import time

from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from app.accounts.api.v1.serializers import (
    CustomTokenRefreshSerializer, RegisterSerializer, UserSerializer, UserUpdateSerializer, 
    CustomTokenObtainPairSerializer, GetOTPSerializer, VerifyOTPSerializer, 
    ForgotPasswordRequestSerializer, ForgotPasswordVerifySerializer, ForgotPasswordResetSerializer, 
)
from app.accounts.services.user_service import delete_user_account
from app.accounts.services.auth_service import login_user, logout_user
from app.accounts.services.otp_flow_service import send_otp, verify_otp_flow
from app.accounts.services.password_reset_service import (
    request_password_reset, verify_password_reset_otp, reset_password,
)

from services.token_service import (
    is_refresh_token_valid, store_refresh_token, delete_refresh_token, store_access_token
)

from core.utils.base_utils import get_user

logger = logging.getLogger(__name__)

# -------------------------------
# Registration and Authentication
# -------------------------------

class RegisterAPI(CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        logger.info(f"User registration attempt for email: {request.data.get('email')}")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh, access = login_user(user)
        logger.info(f"User registered successfully: {user.email}")
        return Response({
            "message": "User created successfully",
            "user": UserSerializer(user).data,
            "refresh": str(refresh),
            "access": str(access),},
            status=status.HTTP_201_CREATED,
        )


class LoginAPI(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    
    def post(self, request):
        logger.info(f"Login attempt for email: {request.data.get('email')}")
        response = super().post(request)
        if response.status_code == status.HTTP_200_OK:
            refresh_token = response.data.get('refresh')
            access_token = response.data.get('access')
            if refresh_token:
                try:
                    token_obj = RefreshToken(refresh_token)
                    uid = token_obj.get('user_id') or token_obj.get('user')
                    if uid:
                        ttl = max(int(token_obj['exp'] - time.time()), 1)
                        store_refresh_token(uid, refresh_token, ttl=ttl)
                        if access_token:
                            store_access_token(uid, access_token)
                        logger.info(f"User logged in successfully, user_id: {uid}")
                except TokenError as e:
                    logger.error(f"Token error during login: {str(e)}")
                    pass
        return response
                

class RefreshAPI(TokenRefreshView):
    serializer_class = CustomTokenRefreshSerializer
    
    def post(self, request):
        logger.info("Token refresh attempt")
        old_refresh = request.data.get("refresh")
        if not old_refresh:
            logger.warning("Refresh token not provided")
            return Response({"message": "Refresh token required"}, status=status.HTTP_400_BAD_REQUEST)
        if not is_refresh_token_valid(old_refresh):
            logger.warning("Invalid refresh token provided")
            return Response({"message": "Invalid refresh token"}, status=401)

        response = super().post(request)
        new_refresh = response.data.get("refresh")
        new_access = response.data.get("access")

        if new_refresh:
            token = RefreshToken(new_refresh)
            uid = token["user_id"]
            ttl = max(int(token['exp'] - time.time()), 1)
            store_refresh_token(uid, new_refresh, ttl=ttl)
            if new_access:
                store_access_token(uid, new_access)
            delete_refresh_token(old_refresh)
            logger.info("Token refreshed successfully")

        return response


class LogoutAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logger.info(f"Logout attempt for user: {request.user.email}")
        logout_user(
            refresh_token=request.data.get("refresh"),
            access_token=request.data.get("access"),
            request_user=request.user,
        )
        logger.info(f"User logged out successfully: {request.user.email}")
        return Response({"message": "Logged out"}, status=205)

# ---------------------------------------
# USER: Get Profile / Update Profile / Delete Profile
# ---------------------------------------

class GetUserAPI(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        logger.debug(f"Get user info request for: {request.user.email}")
        return Response({"message": "Success", "data": UserSerializer(request.user).data}, status=status.HTTP_200_OK)
    
    def put(self, request):
        logger.info(f"Update user profile attempt for user: {request.user.email}")
        serializer = UserUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
            context = {"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info(f"User profile updated successfully for user:")
        
        return Response({
            "message": "User updated successfully",
            "data": UserSerializer(request.user).data},
            status=status.HTTP_200_OK
        )
    
    def delete(self, request):
        try:
            logger.info(f"Delete user account attempt for user: {request.user.email}")
            delete_user_account(request.user)
            logger.info(f"User account deleted successfully for user: {request.user.email}")
            
            return Response({
                "message": "User account deleted"}, 
                status=status.HTTP_204_NO_CONTENT
            )
        
        except ValidationError as e:
            logger.warning(f"Validation error during account deletion for user: {request.user.email} - {str(e)}")
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"Error deleting user account for user: {request.user.email}, error: {str(e)}")
    
# ---------------------------------------
# OTP: Email / Phone Verification & Login
# ---------------------------------------

class GetOTPAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        logger.info(f"OTP request for {request.data.get('kind')}: {request.data.get('identifier')}")
        serializer = GetOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        send_otp(
            kind=serializer.validated_data["kind"],
            identifier=serializer.validated_data["identifier"],
            purpose=serializer.validated_data["purpose"],
        )
        return Response({"message": "OTP sent"})


class VerifyOTPAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        logger.info(f"OTP verification for {request.data.get('kind')}: {request.data.get('identifier')}")
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        verify_otp_flow(
            kind=serializer.validated_data["kind"],
            identifier=serializer.validated_data["identifier"],
            otp=serializer.validated_data["otp"],
            purpose="verify",
        )

        user = get_user(serializer.validated_data["identifier"], serializer.validated_data["kind"])
        if not user:
            logger.warning(f"User not found after OTP verification: {serializer.validated_data['identifier']}")
            return Response({"message": "Invalid request"}, status=status.HTTP_400_BAD_REQUEST)
        
        if serializer.validated_data["kind"] == "email":
            user.is_email_verified = True
        else:
            user.is_phone_verified = True
        user.save()
        logger.info(f"OTP verified successfully for user: {user.email}")
        
        return Response({"message": "Verified"}, status=status.HTTP_200_OK)


class OTPLoginAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        logger.info(f"OTP login attempt for {request.data.get('kind')}: {request.data.get('identifier')}")
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        verify_otp_flow(
            kind=serializer.validated_data["kind"],
            identifier=serializer.validated_data["identifier"],
            otp=serializer.validated_data["otp"],
            purpose="login",
        )

        user = get_user(
            serializer.validated_data["identifier"],
            serializer.validated_data["kind"],
        )

        refresh, access = login_user(user)
        logger.info(f"User logged in via OTP: {user.email}")
        return Response({
            "message": "User logged in successfully",
            "user": UserSerializer(user).data,
            "refresh": str(refresh),
            "access": str(access),},
            status=status.HTTP_200_OK
        )

# -------------------------------
# Forgot Password (OTP-based)
# -------------------------------

class ForgotPasswordRequestAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        logger.info(f"Password reset request for {request.data.get('kind')}: {request.data.get('identifier')}")
        serializer = ForgotPasswordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        request_password_reset(
            kind=serializer.validated_data["kind"],
            identifier=serializer.validated_data["identifier"],
        )
        return Response({"message": "OTP sent"})


class ForgotPasswordVerifyAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        logger.info(f"Password reset OTP verification for {request.data.get('kind')}: {request.data.get('identifier')}")
        serializer = ForgotPasswordVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reset_token = verify_password_reset_otp(**serializer.validated_data)
        return Response({"message": reset_token})


class ForgotPasswordResetAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def put(self, request):
        logger.info("Password reset with token")
        serializer = ForgotPasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reset_password(**serializer.validated_data)
        logger.info("Password reset successfully")
        return Response({"message": "Password updated"})

import logging

from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import render
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .models import Client
from .serializers import (BulkIdsSerializer, ClientDetailSerializerService,
                          ClientSerializer, LoginSerializer,
                          RegisterSerializer, UserPublicSerializer)

# Create your views here.




User = get_user_model()
logger = logging.getLogger(__name__)


def health(request):
    logger.info("Health check called")
    return JsonResponse({"status": "ok", "message": "Account service is healthy."})

class ClientDetailService(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            client = Client.objects.get(id=pk)
            serializer = ClientDetailSerializerService(client)
            logger.info("Client detail found", extra={"client_id": str(pk), "request_user_id": str(request.user.id)})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Client.DoesNotExist:
            logger.warning("Client detail not found", extra={"client_id": str(pk), "request_user_id": str(request.user.id)})
            return Response({"detail": "Client non trouvé."}, status=status.HTTP_404_NOT_FOUND)

class ClientViewSet(ModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = ClientSerializer
    queryset = Client.objects.all()

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info("User registered", extra={"user_id": str(user.id)})

        refresh = RefreshToken.for_user(user)
        data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserPublicSerializer(user).data,
        }
        return Response(data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = User.objects.filter(email__iexact=email).first()
        if user is None or not user.check_password(password):
            logger.warning("Login failed")
            return Response(
                {"detail": "Identifiants invalides."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        logger.info("Login success", extra={"user_id": str(user.id)})
        refresh = RefreshToken.for_user(user)
        data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserPublicSerializer(user).data,
        }
        return Response(data, status=status.HTTP_200_OK)


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        logger.info("Profile requested", extra={"user_id": str(request.user.id)})
        return Response(UserPublicSerializer(request.user).data, status=status.HTTP_200_OK)
    
class UserDetailViewService(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            user = User.objects.get(id=pk)
            logger.info("User detail found", extra={"target_user_id": str(pk), "request_user_id": str(request.user.id)})
            return Response(UserPublicSerializer(user).data, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            logger.warning("User detail not found", extra={"target_user_id": str(pk), "request_user_id": str(request.user.id)})
            return Response({"detail": "Utilisateur non trouvé."}, status=status.HTTP_404_NOT_FOUND)


class UserBulkViewService(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = BulkIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data["ids"]

        users = User.objects.filter(id__in=ids).values("id", "username")
        results = {str(item["id"]): {"id": str(item["id"]), "username": item["username"]} for item in users}
        logger.info("User bulk lookup", extra={"requested_count": len(ids), "found_count": len(results), "request_user_id": str(request.user.id)})
        return Response({"results": results}, status=status.HTTP_200_OK)


class ClientBulkViewService(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = BulkIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data["ids"]

        clients = Client.objects.filter(id__in=ids).values("id", "first_name", "last_name")
        results = {
            str(item["id"]): {
                "id": str(item["id"]),
                "first_name": item["first_name"],
                "last_name": item["last_name"],
            }
            for item in clients
        }
        logger.info("Client bulk lookup", extra={"requested_count": len(ids), "found_count": len(results), "request_user_id": str(request.user.id)})
        return Response({"results": results}, status=status.HTTP_200_OK)


class VerifyTokenView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.data.get("token")
        if not token:
            logger.warning("Token verification failed: missing token")
            return Response({"detail": "token requis."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            parsed = RefreshToken(token).access_token
            logger.info("Token verification success")
            return Response({"valid": True, "claims": parsed.payload}, status=status.HTTP_200_OK)
        except TokenError:
            logger.warning("Token verification failed: invalid token")
            return Response({"valid": False}, status=status.HTTP_401_UNAUTHORIZED)


class RefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            logger.warning("Logout failed: missing refresh token", extra={"user_id": str(request.user.id)})
            return Response(
                {"detail": "refresh token requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh)
            token.blacklist()
            logger.info("Logout success", extra={"user_id": str(request.user.id)})
            return Response({"detail": "Déconnexion réussie."}, status=status.HTTP_200_OK)
        except TokenError:
            logger.warning("Logout failed: invalid refresh token", extra={"user_id": str(request.user.id)})
            return Response(
                {"detail": "refresh token invalide."},
                status=status.HTTP_400_BAD_REQUEST,
            )

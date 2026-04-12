from django.shortcuts import render

# Create your views here.

from django.contrib.auth import get_user_model
from django.http import JsonResponse
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet, ModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.exceptions import TokenError
from .models import Client

from .serializers import RegisterSerializer, LoginSerializer, UserPublicSerializer, ClientSerializer, ClientDetailSerializerService
from .serializers import BulkIdsSerializer


User = get_user_model()


def health(request):
    return JsonResponse({"status": "ok", "message": "Account service is healthy."})

class ClientDetailService(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            client = Client.objects.get(id=pk)
            serializer = ClientDetailSerializerService(client)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Client.DoesNotExist:
            return Response({"detail": "Client non trouvé."}, status=status.HTTP_404_NOT_FOUND)

class ClientViewSet(ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ClientSerializer
    queryset = Client.objects.all()

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

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
            return Response(
                {"detail": "Identifiants invalides."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

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
        return Response(UserPublicSerializer(request.user).data, status=status.HTTP_200_OK)
    
class UserDetailViewService(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            user = User.objects.get(id=pk)
            return Response(UserPublicSerializer(user).data, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"detail": "Utilisateur non trouvé."}, status=status.HTTP_404_NOT_FOUND)


class UserBulkViewService(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = BulkIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data["ids"]

        users = User.objects.filter(id__in=ids).values("id", "username")
        results = {str(item["id"]): {"id": str(item["id"]), "username": item["username"]} for item in users}
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
        return Response({"results": results}, status=status.HTTP_200_OK)


class VerifyTokenView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"detail": "token requis."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            parsed = RefreshToken(token).access_token
            return Response({"valid": True, "claims": parsed.payload}, status=status.HTTP_200_OK)
        except TokenError:
            return Response({"valid": False}, status=status.HTTP_401_UNAUTHORIZED)


class RefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response(
                {"detail": "refresh token requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh)
            token.blacklist()
            return Response({"detail": "Déconnexion réussie."}, status=status.HTTP_200_OK)
        except TokenError:
            return Response(
                {"detail": "refresh token invalide."},
                status=status.HTTP_400_BAD_REQUEST,
            )

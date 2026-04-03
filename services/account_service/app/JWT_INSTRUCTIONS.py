"""
IMPLEMENTATION JWT COMPLETE - ACCOUNT SERVICE
=============================================

OBJECTIF
--------
Ajouter une authentification JWT complete dans account_service avec:
- register
- login (access + refresh)
- refresh
- me (profil courant)
- verify (utile pour gateway/forward-auth)

DESCRIPTION FONCTIONNELLE
-------------------------
account_service devient la source de verite d'authentification:
- il cree les comptes,
- il verifie les identifiants,
- il genere les tokens JWT,
- il expose un endpoint /me pour recuperer l'utilisateur connecte,
- et un endpoint /verify pour valider un token depuis un composant externe.

EXPLICATION DU FLUX JWT
-----------------------
1. Le client envoie email/password a /auth/login/.
2. account_service renvoie un access token (court) et un refresh token (long).
3. Le client envoie Authorization: Bearer <access> sur les autres services.
4. Quand l'access expire, le client appelle /auth/refresh/ pour obtenir un nouveau access.
5. /auth/me/ confirme que le token est valide et renvoie les infos utilisateur.

POURQUOI CETTE STRUCTURE
------------------------
- Separation claire des responsabilites: l'auth est centralisee dans account_service.
- Les autres services deviennent des resource servers (ils valident le token mais ne gerent pas le login).
- Le refresh token reduit les risques en limitant la duree de vie de l'access token.

IMPORTANT
---------
Ce fichier contient des instructions + code a copier dans les fichiers reels.
Il ne doit pas etre importe par Django.

ERREURS FREQUENTES A EVITER
---------------------------
- Oublier set_password() lors de l'inscription: le mot de passe serait stocke en clair.
- Laisser AllowAny globalement en production: toutes les routes deviennent publiques.
- Utiliser des valeurs JWT differentes entre services (issuer/audience/signing key).
- Garder des secrets sensibles en dur dans le code au lieu des variables d'environnement.


1) requirements.txt
-------------------
FICHIER: services/account_service/requirements.txt

AJOUTER:
    djangorestframework-simplejwt>=5.3


2) settings.py
--------------
FICHIER: services/account_service/core/settings.py

A) AJOUTER imports en haut:
    import os
    from datetime import timedelta

B) REMPLACER REST_FRAMEWORK par:

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

C) AJOUTER config JWT en bas du fichier:

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.environ.get("JWT_ACCESS_MINUTES", "30"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.environ.get("JWT_REFRESH_DAYS", "7"))),
    "ALGORITHM": os.environ.get("JWT_ALGORITHM", "HS256"),
    "SIGNING_KEY": os.environ.get("JWT_SIGNING_KEY", SECRET_KEY),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "ISSUER": os.environ.get("JWT_ISSUER", "account-service"),
    "AUDIENCE": os.environ.get("JWT_AUDIENCE", "store-front-services"),
}


3) serializers.py
-----------------
FICHIER: services/account_service/app/serializers.py

COLLER:

from django.contrib.auth import get_user_model
from rest_framework import serializers


User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Cet email existe deja.")
        return value

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Ce username existe deja.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "username", "created_at", "updated_at"]


4) views.py
-----------
FICHIER: services/account_service/app/views.py

COLLER:

from django.contrib.auth import get_user_model
from django.http import JsonResponse
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.exceptions import TokenError

from .serializers import RegisterSerializer, LoginSerializer, UserPublicSerializer


User = get_user_model()


def health(request):
    return JsonResponse({"status": "ok", "message": "Account service is healthy."})


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


5) urls.py
----------
FICHIER: services/account_service/core/urls.py

REMPLACER le contenu par:

from django.urls import path
from app.views import (
    health,
    RegisterView,
    LoginView,
    MeView,
    VerifyTokenView,
    RefreshView,
)

urlpatterns = [
    path("health/", health),
    path("auth/register/", RegisterView.as_view()),
    path("auth/login/", LoginView.as_view()),
    path("auth/refresh/", RefreshView.as_view()),
    path("auth/me/", MeView.as_view()),
    path("auth/verify/", VerifyTokenView.as_view()),
]


6) payloads de test
-------------------
REGISTER:
POST /auth/register/
{
  "email": "alice@example.com",
  "username": "alice",
  "password": "StrongPass123"
}

LOGIN:
POST /auth/login/
{
  "email": "alice@example.com",
  "password": "StrongPass123"
}

ME:
GET /auth/me/
Authorization: Bearer <access>

REFRESH:
POST /auth/refresh/
{
  "refresh": "<refresh_token>"
}

RESULTAT ATTENDU
----------------
- /auth/register/ retourne 201 avec access + refresh + user.
- /auth/login/ retourne 200 avec access + refresh + user.
- /auth/me/ sans token retourne 401.
- /auth/me/ avec token valide retourne 200.
- /auth/refresh/ retourne un nouvel access token valide.
"""

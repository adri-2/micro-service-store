"""
IMPLEMENTATION JWT COMPLETE - PRODUCT SERVICE
=============================================

OBJECTIF
--------
- Proteger categories/suppliers/products avec JWT.
- Garder /health/ en public.

DESCRIPTION FONCTIONNELLE
-------------------------
product_service expose des donnees metier critiques (catalogue, prix, stock).
Il doit donc accepter uniquement des requetes authentifiees pour les routes metier,
tout en laissant un endpoint de sante public pour l'observabilite.

EXPLICATION DU CHOIX TECHNIQUE
------------------------------
Le service utilise un EmptyUser local, donc la verification JWT doit etre stateless.
Cela permet de valider la signature et les claims du token sans necessiter un utilisateur local.

POURQUOI CE MODELE
------------------
- Moins de couplage avec account_service (pas d'appel reseau pour verifier chaque requete).
- Meilleure performance (verification locale du token).
- Politique de securite uniforme pour toutes les routes metier.

POINT CRITIQUE
--------------
product_service utilise EmptyUser local. Il faut valider le JWT sans requete DB utilisateur.
Utiliser JWTStatelessUserAuthentication.

ERREURS FREQUENTES A EVITER
---------------------------
- Oublier IsAuthenticated sur un ViewSet (route exposee publiquement par erreur).
- Oublier AllowAny uniquement sur /health/.
- Incoherence des parametres JWT (issuer/audience/signing key) entre services.


1) requirements.txt
-------------------
FICHIER: services/product_service/requirements.txt

AJOUTER:
    djangorestframework-simplejwt>=5.3


2) settings.py
--------------
FICHIER: services/product_service/core/settings.py

A) AJOUTER import:
import os

B) REMPLACER REST_FRAMEWORK par:

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTStatelessUserAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

C) AJOUTER bloc SIMPLE_JWT:

SIMPLE_JWT = {
    "ALGORITHM": os.environ.get("JWT_ALGORITHM", "HS256"),
    "SIGNING_KEY": os.environ.get("JWT_SIGNING_KEY", SECRET_KEY),
    "VERIFYING_KEY": os.environ.get("JWT_VERIFYING_KEY", ""),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "ISSUER": os.environ.get("JWT_ISSUER", "account-service"),
    "AUDIENCE": os.environ.get("JWT_AUDIENCE", "store-front-services"),
}


3) views.py
-----------
FICHIER: services/product_service/app/views.py

A) AJOUTER import:
from rest_framework import permissions
from rest_framework.decorators import permission_classes

B) RENDRE health public:

@permission_classes([permissions.AllowAny])
def health(request):
    return JsonResponse({"status": "ok", "message": "Product service is healthy."})

C) PROTEGER les ViewSets:

class CategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class SupplierViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer


class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Product.objects.select_related("category").prefetch_related("suppliers")
    serializer_class = ProductSerializer


4) comportement attendu
-----------------------
- GET /health/ sans token -> 200
- GET /products/ sans token -> 401
- GET /products/ avec token valide -> 200

RESULTAT ATTENDU EN SECURITE
----------------------------
- Toute lecture/ecriture metier du catalogue exige un JWT valide.
- Les services clients (order, front, gateway) ont un comportement d'acces coherent.
"""

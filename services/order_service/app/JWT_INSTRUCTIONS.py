"""
IMPLEMENTATION JWT COMPLETE - ORDER SERVICE
===========================================

OBJECTIF
--------
- Proteger toutes les routes metier via JWT.
- Laisser /health/ public.
- Propager le Bearer token vers product_service lors des appels HTTP.

DESCRIPTION FONCTIONNELLE
-------------------------
order_service doit verifier qu'un utilisateur est authentifie avant toute action metier,
mais il ne gere pas le login lui-meme. Il fait confiance au token emis par account_service.

EXPLICATION DU FLUX INTER-SERVICES
----------------------------------
1. Le client appelle /orders/ avec Authorization: Bearer <access>.
2. order_service valide le JWT localement.
3. Pendant la creation d'une commande, order_service appelle product_service pour lire un produit.
4. order_service propage le meme header Authorization vers product_service.
5. product_service valide a son tour le JWT avant de repondre.

POURQUOI LA PROPAGATION EST NECESSAIRE
--------------------------------------
Sans propagation, order_service pourrait etre authentifie mais son appel interne vers product_service
serait considere comme anonyme et donc refuse. La propagation garde un contexte de securite coherent.

POINT CRITIQUE
--------------
order_service utilise EmptyUser local. Il faut verifier le JWT SANS lookup DB utilisateur.
Utiliser JWTStatelessUserAuthentication.

ERREURS FREQUENTES A EVITER
---------------------------
- Utiliser JWTAuthentication avec EmptyUser: risque d'echec de resolution utilisateur.
- Oublier de passer request dans le context serializer (sinon pas d'acces au header Authorization).
- Ecraser le header Authorization lors des appels requests.get/requests.post.
- Oublier de garder /health/ public (utile pour monitoring et orchestration).


1) requirements.txt
-------------------
FICHIER: services/order_service/requirements.txt

AJOUTER:
    djangorestframework-simplejwt>=5.3


2) settings.py
--------------
FICHIER: services/order_service/core/settings.py

A) AJOUTER import:
    from datetime import timedelta

B) REMPLACER REST_FRAMEWORK par:

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTStatelessUserAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

C) AJOUTER config JWT compatible account_service:

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
FICHIER: services/order_service/app/views.py

A) AJOUTER imports:
from rest_framework import permissions

B) AJOUTER permission publique seulement pour health:

def health(request):
    return JsonResponse({"status": "ok", "message": "Order service is healthy."})

class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Order.objects.prefetch_related("items")
    serializer_class = OrderSerializer


4) services.py - propagation du token
-------------------------------------
FICHIER: services/order_service/app/services.py

A) AJOUTER helper:

def _auth_headers(access_token: str | None) -> dict:
    if not access_token:
        return {}
    token = access_token.strip()
    if token.lower().startswith("bearer "):
        return {"Authorization": token}
    return {"Authorization": f"Bearer {token}"}

B) MODIFIER get_product pour accepter un token:

def get_product(product_id: str, access_token: str | None = None) -> dict:
    url = _build_url(f"products/{product_id}/")
    headers = _auth_headers(access_token)
    response = requests.get(url, timeout=5, headers=headers)
    ...

C) MODIFIER get_products pareil:

def get_products(access_token: str | None = None) -> dict:
    url = _build_url("/products/")
    headers = _auth_headers(access_token)
    response = requests.get(url, timeout=5, headers=headers)
    ...


5) serializers.py - passer le token courant
-------------------------------------------
FICHIER: services/order_service/app/serializers.py

DANS create(), avant la boucle items:

request = self.context.get("request")
authorization = None
if request is not None:
    authorization = request.META.get("HTTP_AUTHORIZATION")

DANS la boucle, remplacer:
    product = get_product(product_id)
par:
    product = get_product(product_id, access_token=authorization)


6) comportement attendu
-----------------------
- Appel client sans token sur /orders/ -> 401
- Appel client avec token valide -> 200/201
- Pendant creation de commande, order_service appelle product_service avec le meme token.
- Si token invalide/expire, product_service renvoie 401 et la creation de commande echoue.

RESULTAT ATTENDU EN PRODUCTION
------------------------------
- Les routes metier de orders ne sont plus accessibles anonymement.
- Les erreurs d'auth sont explicites et homogenes (401).
- Les appels inter-services respectent la meme politique de securite.
"""

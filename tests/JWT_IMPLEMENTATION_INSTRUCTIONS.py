"""
CHECKLIST FINALE - JWT END TO END (ACCOUNT + PRODUCT + ORDER)
==============================================================

OBJECTIF
--------
Guider le branchement complet JWT entre les services et fournir les tests manuels.

DESCRIPTION GLOBALE DE L'ARCHITECTURE
-------------------------------------
- account_service: emet les tokens JWT (service d'identite).
- product_service et order_service: valident les tokens JWT (resource services).
- gateway (Traefik): route le trafic; il peut rester passif ou ajouter un controle auth plus tard.

EXPLICATION DU FLUX COMPLET
---------------------------
1. L'utilisateur se connecte sur account_service et recupere access + refresh.
2. Le client appelle product/order avec Bearer access.
3. Les services valident le token localement (signature + claims).
4. order_service propage ce token vers product_service pour les appels internes.
5. Si le token expire, le client utilise refresh pour obtenir un nouvel access.

POURQUOI CETTE APPROCHE EST SOLIDE
----------------------------------
- Centralise l'authentification tout en decentralisant la verification.
- Evite une dependance reseau forte sur account a chaque requete metier.
- Rend les erreurs de securite testables et observables (401 clairs).


1) VARIABLES D'ENV COMMUNES
---------------------------
Dans chaque docker-compose de service, ajouter les memes variables:

JWT_ALGORITHM=HS256
JWT_SIGNING_KEY=change-me-super-secret
JWT_ISSUER=account-service
JWT_AUDIENCE=store-front-services

FICHIERS:
- services/account_service/docker-compose.account.yml
- services/product_service/docker-compose.catalogue.yml
- services/order_service/docker-compose.orders.yml

NOTE:
Pour un premier setup, garder HS256.
En production, migrer vers RS256 (cle privee dans account, cle publique dans les autres).


2) REBUILD ET MIGRATIONS
------------------------
Commande type (dans chaque service):

docker compose -f docker-compose.account.yml up --build -d
docker compose -f docker-compose.catalogue.yml up --build -d
docker compose -f docker-compose.orders.yml up --build -d


3) FLUX DE TEST API (http)
--------------------------
A) Register
POST http://accounts.localhost/auth/register/
Content-Type: application/json

{
  "email": "alice@example.com",
  "username": "alice",
  "password": "StrongPass123"
}

B) Login
POST http://accounts.localhost/auth/login/
Content-Type: application/json

{
  "email": "alice@example.com",
  "password": "StrongPass123"
}

Recuperer access et refresh.

C) Product protege
GET http://catalogue.localhost/products/
Authorization: Bearer <access>

D) Order protege
POST http://orders.localhost/orders/
Authorization: Bearer <access>
Content-Type: application/json

{
  "user_id": "11111111-1111-1111-1111-111111111111",
  "client_id": "22222222-2222-2222-2222-222222222222",
  "items_input": [
    {
      "product_id": "<uuid_produit>",
      "quantity": 1
    }
  ]
}


4) TESTS NEGATIFS OBLIGATOIRES
------------------------------
- Sans token sur /products/ -> 401
- Sans token sur /orders/ -> 401
- Token invalide -> 401
- Token expire -> 401


5) DEPANNAGE RAPIDE
-------------------
Si tout renvoie 401:
- verifier que JWT_SIGNING_KEY est identique dans account/order/product en HS256
- verifier issuer/audience identiques partout
- verifier header Authorization: Bearer <token>

Si order cree mais ne lit pas product:
- verifier propagation du header dans services/order_service/app/services.py

Si erreur User introuvable dans product/order:
- verifier JWTStatelessUserAuthentication (et pas JWTAuthentication)

CHECK DE VALIDATION FINALE
--------------------------
- Toutes les routes metier sans token retournent 401.
- /health/ reste accessible sans token.
- Login + refresh fonctionnent sans erreur.
- La creation de commande echoue proprement si le token est invalide/expire.
- La creation de commande reussit quand token et payload sont valides.
"""

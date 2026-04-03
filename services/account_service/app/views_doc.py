"""
GUIDE — views.py pour account_service
======================================

Ce fichier est un guide d'implémentation.
Une fois implémenté, modifie le fichier existant :
    account_service/app/views.py

Tu peux t'appuyer sur le fichier existant comme référence :
    product_service/app/views.py


ÉTAT ACTUEL DE views.py
------------------------
Le fichier est presque vide :

    from django.shortcuts import render
    # def index(request): ...

Rien d'autre. Aucun endpoint n'existe.


CE QUE TU DOIS IMPLÉMENTER
---------------------------

1. Endpoint /health/          → indispensable pour Consul
2. UserViewSet                → CRUD sur User
3. ClientViewSet              → CRUD sur Client
4. Configuration des URLs     → dans core/urls.py


==============================================================================
ÉTAPE 1 — Ajouter l'endpoint /health/
==============================================================================

Copie cet endpoint depuis product_service/app/views.py.
C'est exactement le même dans tous les services.

    from django.http import JsonResponse

    def health(request):
        return JsonResponse({"status": "ok"})

C'est tout. Pas de logique, juste confirmer que le service répond.
Consul appelle cet endpoint toutes les 10 secondes.


==============================================================================
ÉTAPE 2 — UserViewSet
==============================================================================

Modèle : User (email, username, password)
Serializer : UserSerializer (à créer d'abord depuis serializers_doc.py)

Structure de base :

    from rest_framework import viewsets
    from .models import User
    from .serializers import UserSerializer

    class UserViewSet(viewsets.ModelViewSet):
        queryset = ???       # TODO: récupérer tous les users
        serializer_class = ???   # TODO: quel serializer ?

Optimisation :
Pour User, il n'y a pas de select_related ni prefetch_related à faire
car User n'a pas de ForeignKey ni ManyToManyField.

    queryset = User.objects.all()

Questions à te poser :
- Est-ce qu'on veut exposer tous les users en liste (GET /users/) ?
- Est-ce qu'on veut permettre la suppression d'un user via l'API ?
- Pour l'instant, répondre oui à tout (AllowAny est déjà configuré dans settings.py).
  On ajoutera des permissions plus tard.


==============================================================================
ÉTAPE 3 — ClientViewSet
==============================================================================

Modèle : Client (first_name, last_name, email, phone_number, address)
Serializer : ClientSerializer

Structure de base :

    from .models import Client
    from .serializers import ClientSerializer

    class ClientViewSet(viewsets.ModelViewSet):
        queryset = ???
        serializer_class = ???

Il n'y a pas non plus de relation à optimiser ici.

Question bonus :
Veux-tu pouvoir chercher un client par email ?
    Ex: GET /clients/?email=john@example.com

Si oui, tu devras ajouter un filtre.
DRF fournit DjangoFilterBackend pour ça,
mais ce n'est pas obligatoire pour commencer.


==============================================================================
ÉTAPE 4 — Mettre à jour core/urls.py
==============================================================================

Fichier actuel : account_service/core/urls.py

    from django.urls import path
    from app import views
    urlpatterns = []   # vide

Ce que tu dois mettre :

    from django.urls import path
    from rest_framework.routers import DefaultRouter
    from app.views import health, UserViewSet, ClientViewSet   # TODO: ajouter ces imports

    router = DefaultRouter()
    router.register(r'users', ???)     # TODO: quel ViewSet ?
    router.register(r'clients', ???)   # TODO: quel ViewSet ?

    urlpatterns = [
        path('health/', health),
    ]
    urlpatterns += router.urls

Résultat attendu des URLs générées par le routeur :

    GET    /users/           → liste des users
    POST   /users/           → créer un user
    GET    /users/{id}/      → détail d'un user
    PUT    /users/{id}/      → mettre à jour un user
    PATCH  /users/{id}/      → mise à jour partielle
    DELETE /users/{id}/      → supprimer un user

    GET    /clients/         → liste des clients
    POST   /clients/         → créer un client
    GET    /clients/{id}/    → détail d'un client
    PUT    /clients/{id}/    → mettre à jour un client
    PATCH  /clients/{id}/    → mise à jour partielle
    DELETE /clients/{id}/    → supprimer un client

    GET    /health/          → {"status": "ok"}


==============================================================================
COMMENT TESTER
==============================================================================

Une fois le serveur lancé :

    # Health check
    curl http://localhost:8003/health/

    # Créer un client
    curl -X POST http://localhost:8003/clients/ \\
         -H "Content-Type: application/json" \\
         -d '{"first_name": "Jean", "last_name": "Dupont", "email": "jean@example.com"}'

    # Lister les clients
    curl http://localhost:8003/clients/

    # Créer un user
    curl -X POST http://localhost:8003/users/ \\
         -H "Content-Type: application/json" \\
         -d '{"email": "admin@example.com", "username": "admin", "password": "secret123"}'


==============================================================================
CHECKLIST
==============================================================================

[ ] health() ajouté dans views.py
[ ] UserViewSet implémenté avec queryset et serializer_class
[ ] ClientViewSet implémenté avec queryset et serializer_class
[ ] core/urls.py mis à jour avec le routeur DRF et /health/
[ ] GET /health/ répond {"status": "ok"}
[ ] POST /clients/ crée un client
[ ] GET /clients/ liste les clients
[ ] POST /users/ crée un user avec mot de passe haché


==============================================================================
PROCHAINE ÉTAPE APRÈS LES VIEWS
==============================================================================

→ Étape 7 des next-steps.md :
  Ajouter les labels Traefik dans docker-compose.account.yml
  et créer registry_service/config/account-service.json pour Consul.
"""

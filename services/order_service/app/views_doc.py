"""
GUIDE — views.py pour order_service
=====================================

Ce fichier est un guide d'implémentation.
Une fois implémenté, modifie le fichier existant :
    order_service/app/views.py

Référence utile :
    product_service/app/views.py


ÉTAT ACTUEL DE views.py
------------------------
Le fichier est vide. Aucun endpoint n'existe.


CE QUE TU DOIS IMPLÉMENTER
---------------------------

1. Endpoint /health/        → pour Consul
2. OrderViewSet             → CRUD de commandes
3. Actions spéciales        → confirm, cancel (changements de status)
4. core/urls.py             → router DRF


==============================================================================
ÉTAPE 1 — Endpoint /health/
==============================================================================

Identique à tous les autres services :

    from django.http import JsonResponse

    def health(request):
        return JsonResponse({"status": "ok"})


==============================================================================
ÉTAPE 2 — OrderViewSet (structure de base)
==============================================================================

Imports nécessaires :

    from rest_framework import viewsets, status
    from rest_framework.decorators import action
    from rest_framework.response import Response
    from .models import Order, OrderItem
    from .serializers import OrderSerializer

Structure :

    class OrderViewSet(viewsets.ModelViewSet):

        queryset = ???          # TODO: récupérer toutes les commandes
                                # Conseil : ajouter prefetch_related("items")
                                # pour éviter les requêtes N+1

        serializer_class = ???  # TODO: quel serializer ?

        # IMPORTANT : pour l'instant les actions create/update/delete
        # sont héritées de ModelViewSet.
        # Tu peux les surcharger si tu as besoin de logique spéciale.


# Pourquoi prefetch_related("items") ?
#
# Sans prefetch_related :
#   - GET /orders/ → 1 requête pour les orders
#   - pour chaque order → 1 requête pour ses items
#   → si 20 commandes → 21 requêtes SQL (problème N+1)
#
# Avec prefetch_related("items") :
#   - 1 requête pour les orders
#   - 1 requête pour TOUS les items liés
#   → 2 requêtes au total peu importe le nombre de commandes


==============================================================================
ÉTAPE 3 — Actions spéciales : confirm et cancel
==============================================================================

Plutôt que de permettre à l'API de mettre status=Confirmed directement
via PUT (ce qui est peu sûr), on créée des actions dédiées.

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        \"""
        POST /orders/{id}/confirm/
        Change le status d'une commande à Confirmed.
        \"""
        order = self.get_object()

        # TODO: vérifier que le status actuel est Pending
        # Si le status n'est pas Pending, retourner une erreur 400

        # TODO: changer le status à Confirmed
        # TODO: sauvegarder

        # TODO: retourner la commande mise à jour
        pass

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        \"""
        POST /orders/{id}/cancel/
        Annule une commande si elle est encore en Pending.
        \"""
        order = self.get_object()

        # TODO: vérifier que le status actuel est Pending
        # On ne peut pas annuler une commande déjà Confirmed

        # TODO: changer le status à Cancelled
        # TODO: sauvegarder (et peut-être remettre le stock → via services.py)

        # TODO: retourner la commande mise à jour
        pass


# EXPLICATION du décorateur @action :
#
# @action(detail=True, methods=['post'])
#   - detail=True → l'action s'applique à UN objet (/orders/{id}/confirm/)
#   - detail=False → l'action s'applique à la liste (/orders/confirm/)
#   - methods=['post'] → seul POST est autorisé
#
# Autres exemples d'actions utiles :
#   - GET /orders/{id}/items/   → lister les items d'une commande
#   - POST /orders/{id}/confirm/ → confirmer
#   - POST /orders/{id}/cancel/  → annuler


# EXEMPLE de confirm() complet :
#
#   @action(detail=True, methods=['post'])
#   def confirm(self, request, pk=None):
#       order = self.get_object()
#       if order.status != Order.StatusChoices.PENDING:
#           return Response(
#               {"error": "Seules les commandes en attente peuvent être confirmées."},
#               status=status.HTTP_400_BAD_REQUEST
#           )
#       order.status = Order.StatusChoices.CONFIRMED
#       order.save(update_fields=['status'])
#       serializer = self.get_serializer(order)
#       return Response(serializer.data)


==============================================================================
ÉTAPE 4 — Mettre à jour core/urls.py
==============================================================================

Fichier actuel : order_service/core/urls.py
Contenu actuel : urlpatterns = []  (vide)

Ce que tu dois mettre :

    from django.urls import path
    from rest_framework.routers import DefaultRouter
    from app.views import health, OrderViewSet    # TODO: ajouter les imports

    router = DefaultRouter()
    router.register(r'orders', ???)   # TODO: quel ViewSet ?

    urlpatterns = [
        path('health/', health),
    ]
    urlpatterns += router.urls

URLs générées automatiquement par le routeur :

    GET    /orders/              → liste des commandes
    POST   /orders/              → créer une commande
    GET    /orders/{id}/         → détail d'une commande
    PUT    /orders/{id}/         → modifier une commande
    PATCH  /orders/{id}/         → modification partielle
    DELETE /orders/{id}/         → supprimer une commande

    POST   /orders/{id}/confirm/ → confirmer (action custom)
    POST   /orders/{id}/cancel/  → annuler (action custom)

    GET    /health/              → {"status": "ok"}


==============================================================================
ATTENTION : settings.py doit être corrigé avant de tester
==============================================================================

Actuellement order_service utilise SQLite et n'a pas de PostgreSQL configuré.
Les vues ne fonctionneront correctement qu'une fois l'étape 1 des next-steps
(correction des settings.py) réalisée.

Pour tester rapidement sans PostgreSQL :
    python manage.py migrate
    python manage.py runserver 0.0.0.0:8000
    (SQLite sera utilisé, ce qui est suffisant pour tester les endpoints)


==============================================================================
COMMENT TESTER
==============================================================================

    # Health check
    curl http://localhost:8002/health/

    # Créer une commande (simplifié, sans appel catalogue-service pour l'instant)
    curl -X POST http://localhost:8002/orders/ \\
         -H "Content-Type: application/json" \\
         -d '{
               "user_id": "uuid-du-user",
               "client_id": "uuid-du-client",
               "items_input": [
                   {"product_id": "uuid-du-produit", "quantity": 2}
               ]
             }'

    # Lister les commandes
    curl http://localhost:8002/orders/

    # Confirmer une commande
    curl -X POST http://localhost:8002/orders/{id}/confirm/


==============================================================================
CHECKLIST
==============================================================================

[ ] health() dans views.py
[ ] OrderViewSet avec queryset (prefetch_related items) et serializer_class
[ ] Action confirm() dans OrderViewSet
[ ] Action cancel() dans OrderViewSet
[ ] core/urls.py mis à jour
[ ] GET /health/ répond {"status": "ok"}
[ ] POST /orders/ crée une commande
[ ] POST /orders/{id}/confirm/ change le status


==============================================================================
PROCHAINE ÉTAPE APRÈS LES VIEWS
==============================================================================

→ Implémenter services.py (services_doc.py) pour câbler
  les appels vers catalogue-service lors de la création d'une commande.
"""

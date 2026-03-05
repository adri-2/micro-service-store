"""
ÉTAPE 6 — Exposer l'API (views.py + urls.py)
==============================================

FICHIER À MODIFIER:
    services/order_service/app/views.py
    services/order_service/core/urls.py


CONTEXTE:
---------
Jusqu'ici, la logique est en place:
    - product_service expose decrement-stock
    - order_service a la couche services.py
    - order_service a les serializers prêts

Maintenant on doit exposer les endpoints API pour que les clients puissent créer/consulter des commandes.


STRUCTURE VIEWS.PY:
-------------------

    from django.http import JsonResponse
    from rest_framework import viewsets, status
    from rest_framework.decorators import action
    from rest_framework.response import Response
    
    from .models import Order
    from .serializers import OrderSerializer


    def health(request):
        # Endpoint simple pour Consul / load balancer / monitoring
        # Retourne {"status": "ok"}
        pass


    class OrderViewSet(viewsets.ModelViewSet):
        # DRF génère automatiquement CRUD endpoints
        # GET /orders/ → list
        # POST /orders/ → create
        # GET /orders/{id}/ → retrieve
        # PUT /orders/{id}/ → update
        # PATCH /orders/{id}/ → partial_update
        # DELETE /orders/{id}/ → destroy
        
        queryset = ???  # TODO: prefetch_related("items") pour éviter N+1
        serializer_class = ???
        
        @action(detail=True, methods=["post"])
        def confirm(self, request, pk=None):
            # POST /orders/{id}/confirm/
            # Change status de Pending à Confirmed
            pass
        
        @action(detail=True, methods=["post"])
        def cancel(self, request, pk=None):
            # POST /orders/{id}/cancel/
            # Change status de Pending à Cancelled
            pass


DÉTAIL: queryse

queryset doit utiliser prefetch_related("items"):
    
    Sans prefetch:
        GET /orders/ → 1 requête pour les orders
        Pour chaque order → 1 requête pour ses items
        Si 20 commandes → 21 requêtes SQL ❌ (N+1 problem)
    
    Avec prefetch:
        GET /orders/ → 1 requête pour les orders
        → 1 requête pour tous les items associés
        = 2 requêtes au total ✓

À faire:
    queryset = Order.objects.prefetch_related("items")


DÉTAIL: Actions confirm() et cancel()

@action(detail=True, methods=["post"])
def confirm(self, request, pk=None):
    \"""
    POST /orders/{id}/confirm/
    
    Passe le statut de Pending à Confirmed.
    Ne peut être appelé que si status == Pending.
    \"""
    # Step 1: self.get_object() récupère l'objet Order via pk
    # Step 2: Vérifier que order.status == Order.StatusChoices.PENDING
    # Step 3: Si not Pending, retourner erreur 400
    # Step 4: Changer status à CONFIRMED
    # Step 5: Sauvegarder
    # Step 6: Retourner Response(serializer_data, status=HTTP_200_OK)


Exemple simplifié:

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        order = self.get_object()
        
        if order.status != Order.StatusChoices.PENDING:
            return Response(
                {"detail": "Seules les commandes Pending peuvent être confirmées."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        order.status = Order.StatusChoices.CONFIRMED
        order.save(update_fields=["status", "updated_at"])
        
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)


De même pour cancel(), mais:
    - Vérifier status == PENDING
    - Changer à CANCELLED


STRUCTURE URLS.PY:
-------------------

    from django.urls import path
    from rest_framework.routers import DefaultRouter
    from app.views import health, OrderViewSet


    router = DefaultRouter()
    router.register(r"orders", OrderViewSet)
    # Génère automatiquement:
    #   GET    /orders/
    #   POST   /orders/
    #   GET    /orders/{id}/
    #   PUT    /orders/{id}/
    #   PATCH  /orders/{id}/
    #   DELETE /orders/{id}/
    #   POST   /orders/{id}/confirm/        ← action custom
    #   POST   /orders/{id}/cancel/         ← action custom


    urlpatterns = [
        path("health/", health),
    ]
    urlpatterns += router.urls
    # Combine les patterns du router avec les patterns manuels


ENDPOINTS GÉNÉRÉS:
-------------------

Méthode    URL                           Description
------     ---                           -----------
GET        /health/                      Health check
GET        /orders/                      Lister les commandes
POST       /orders/                      Créer une commande
GET        /orders/{id}/                 Détail d'une commande
PUT        /orders/{id}/                 Modifier complètement
PATCH      /orders/{id}/                 Modifier partiellement
DELETE     /orders/{id}/                 Supprimer
POST       /orders/{id}/confirm/         Confirmer (action)
POST       /orders/{id}/cancel/          Annuler (action)


TESTER MANUELLEMENT:
---------------------

# 1. Health check
curl http://localhost:8002/health/
→ {"status": "ok"}

# 2. Lister les commandes (vide au début)
curl http://localhost:8002/orders/
→ {"count": 0, "results": []}

# 3. Créer une commande
curl -X POST http://localhost:8002/orders/ \\
  -H "Content-Type: application/json" \\
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "client_id": "550e8400-e29b-41d4-a716-446655440001",
    "items_input": [
      {
        "product_id": "UUID-DU-PRODUIT-EXISTANT",
        "quantity": 2
      }
    ]
  }'
→ Retourne la commande créée avec son id

# 4. Récupérer détail
curl http://localhost:8002/orders/{id}/
→ Détail complet avec items imbriqués

# 5. Confirmer
curl -X POST http://localhost:8002/orders/{id}/confirm/
→ Status = Confirmed

# 6. Essayer confirmer encore
curl -X POST http://localhost:8002/orders/{id}/confirm/
→ Erreur 400 (déjà confirmé)

# 7. Annuler (nouvelle commande d'abord)
curl -X POST http://localhost:8002/orders/{id}/cancel/
→ Status = Cancelled


COMPLET VIEWS.PY:

    from django.http import JsonResponse
    from rest_framework import viewsets, status
    from rest_framework.decorators import action
    from rest_framework.response import Response
    
    from .models import Order
    from .serializers import OrderSerializer


    def health(request):
        return JsonResponse({"status": "ok"})


    class OrderViewSet(viewsets.ModelViewSet):
        queryset = Order.objects.prefetch_related("items")
        serializer_class = OrderSerializer
        
        @action(detail=True, methods=["post"])
        def confirm(self, request, pk=None):
            order = self.get_object()
            
            if order.status != Order.StatusChoices.PENDING:
                return Response(
                    {"detail": "Seules les commandes Pending peuvent être confirmées."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            order.status = Order.StatusChoices.CONFIRMED
            order.save(update_fields=["status", "updated_at"])
            
            serializer = self.get_serializer(order)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        @action(detail=True, methods=["post"])
        def cancel(self, request, pk=None):
            order = self.get_object()
            
            if order.status != Order.StatusChoices.PENDING:
                return Response(
                    {"detail": "Seules les commandes Pending peuvent être annulées."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            order.status = Order.StatusChoices.CANCELLED
            order.save(update_fields=["status", "updated_at"])
            
            serializer = self.get_serializer(order)
            return Response(serializer.data, status=status.HTTP_200_OK)


COMPLET URLS.PY:

    from django.urls import path
    from rest_framework.routers import DefaultRouter
    
    from app.views import health, OrderViewSet
    
    
    router = DefaultRouter()
    router.register(r"orders", OrderViewSet)
    
    urlpatterns = [
        path("health/", health),
    ]
    urlpatterns += router.urls


POINTS IMPORTANTS:
-------------------

✓ prefetch_related évite le problème N+1
✓ Actions custom permis par @action
✓ Vérifier status avant de modifier
✓ Retourner des Response cohérentes (data + status)
✓ Utiliser update_fields pour les saves partiels (meilleure performance)


DÉPLOIEMENTS:
--------------

Une fois tout fonctionne en local:
1. Lancer product_service
2. Lancer order_service
3. Tester endpoints via curl ou Postman
4. Vérifier logs pour erreurs
"""

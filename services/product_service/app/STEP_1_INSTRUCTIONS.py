"""
ÉTAPE 1 — Ajouter l'endpoint de décrémentation de stock
==========================================================

FICHIER À MODIFIER:
    services/product_service/app/views.py


CONTEXTE:
---------
order_service appelle product_service pour:
    1. Récupérer les infos du produit (GET /products/{id}/) → DÉJÀ IMPLÉMENTÉ
    2. Décrémenter le stock (POST /products/{id}/decrement-stock/) → À IMPLÉMENTER

C'est l'étape fournisseur.


QUOI IMPLÉMENTER:
------------------
Une action DRF personnalisée sur ProductViewSet qui:
    - Accepte une requête POST
    - Lit la quantité demandée
    - Valide:
        * quantity est un entier
        * quantity > 0
        * product.stock >= quantity
    - Décrémente le stock
    - Retourne le produit mis à jour


IMPORTS À AJOUTER:
-------------------
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

(Certains peuvent déjà être importés, vérifier d'abord)


STRUCTURE DE LA MÉTHODE:
------------------------

@action(detail=True, methods=["post"], url_path="decrement-stock")
def decrement_stock(self, request, pk=None):
    \"""
    POST /products/{id}/decrement-stock/
    
    Body attendu: { "quantity": 5 }
    
    Valide le stock et décrémente.
    Retourne le produit mis à jour ou une erreur 400/404.
    \"""
    # Step 1: Récupérer l'objet produit (fourni par DRF via pk)
    # Step 2: Lire la quantité depuis request.data.get("quantity")
    # Step 3: Convertir en entier (int()) et capturer les erreurs
    # Step 4: Valider que quantity > 0
    # Step 5: Valider que product.stock >= quantity
    # Step 6: Décrémenter product.stock -= quantity
    # Step 7: Sauvegarder avec save(update_fields=[...])
    # Step 8: Retourner Response(data, status=...)
    pass


GESTION DES ERREURS:
---------------------

Erreur 1: Quantité invalide (non-entier ou négatif)
    Retourner: Response({"detail": "..."}, status=HTTP_400_BAD_REQUEST)

Erreur 2: Stock insuffisant
    Retourner: Response(
        {
            "detail": "Stock insuffisant.",
            "available_stock": product.stock,
            "requested_quantity": quantity,
        },
        status=HTTP_400_BAD_REQUEST
    )

Succès: Retourner le produit mis à jour
    Response(serializer_data, status=HTTP_200_OK)


EXEMPLE SIMPLIFIÉ:

    @action(detail=True, methods=["post"], url_path="decrement-stock")
    def decrement_stock(self, request, pk=None):
        product = self.get_object()  # fourni par DRF
        
        quantity = request.data.get("quantity")
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return Response(
                {"detail": "quantity doit être un entier"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        if quantity <= 0:
            return Response(
                {"detail": "quantity doit être > 0"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        if product.stock < quantity:
            return Response(
                {
                    "detail": "Stock insuffisant",
                    "available": product.stock,
                    "requested": quantity,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        product.stock -= quantity
        product.save(update_fields=["stock", "updated_at"])
        
        serializer = self.get_serializer(product)
        return Response(serializer.data, status=status.HTTP_200_OK)


TESTER MANUELLEMENT (une fois déployé):
-----------------------------------------

# Créer un produit
curl -X POST http://localhost:8001/products/ \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Laptop",
    "price": 999.99,
    "stock": 10,
    "category_id": "uuid-du-category"
  }'

# Récupérer l'id du produit créé, puis:

# Tester decrement-stock avec quantité valide
curl -X POST http://localhost:8001/products/{id}/decrement-stock/ \\
  -H "Content-Type: application/json" \\
  -d '{"quantity": 3}'

# Vérifier que stock passe de 10 à 7
curl http://localhost:8001/products/{id}/

# Tester erreur (stock insuffisant)
curl -X POST http://localhost:8001/products/{id}/decrement-stock/ \\
  -H "Content-Type: application/json" \\
  -d '{"quantity": 10}'  # Plus que le stock restant


RAPPEL IMPORTANT:
------------------
Cette action n'est appelée que par order_service lors de la création d'une commande.
Elle doit être FIABLE et VALIDÉE complètement.
"""

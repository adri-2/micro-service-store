"""
GUIDE — Ajouter l'endpoint decrement_stock à catalogue-service
==============================================================

Fichier à modifier :
    product_service/app/views.py

Ce guide couvre la partie SERVEUR de la communication inter-services.
order_service appelle catalogue-service → catalogue-service doit répondre.

Référence côté client :
    order_service/app/services_doc.py


==============================================================================
CE QUI EXISTE DÉJÀ
==============================================================================

product_service/app/views.py contient :

    def health(request): ...

    class CategoryViewSet(viewsets.ModelViewSet): ...
    class SupplierViewSet(viewsets.ModelViewSet): ...
    class ProductViewSet(viewsets.ModelViewSet):
        queryset = Product.objects.select_related("category").prefetch_related("suppliers")
        serializer_class = ProductSerializer

C'est bon. Il faut ajouter UNE action dans ProductViewSet.


==============================================================================
L'ACTION À AJOUTER : decrement_stock
==============================================================================

Quand order_service crée une commande, il appelle :

    POST /products/{id}/decrement-stock/
    Body : { "quantity": 2 }

catalogue-service doit :
  1. Récupérer le produit
  2. Vérifier que le stock >= quantity demandée
  3. Si ok → décrémenter le stock et sauvegarder
  4. Retourner le produit mis à jour (avec le nouveau stock)
  5. Si stock insuffisant → retourner une erreur 400


POURQUOI une action DRF et pas une vue séparée ?
Le produit appartient à ProductViewSet. Une action @action permet
d'ajouter un endpoint lié à un objet existant sans sortir du ViewSet.
C'est le pattern DRF pour les opérations qui ne sont pas du CRUD standard.


IMPORTS À AJOUTER dans views.py :

    from rest_framework.decorators import action
    from rest_framework.response import Response
    from rest_framework import status


STRUCTURE DE L'ACTION :

    class ProductViewSet(viewsets.ModelViewSet):
        queryset = Product.objects.select_related("category").prefetch_related("suppliers")
        serializer_class = ProductSerializer

        # --- AJOUTER CET ENDPOINT ---
        @action(detail=True, methods=['post'], url_path='decrement-stock')
        def decrement_stock(self, request, pk=None):
            \"""
            POST /products/{id}/decrement-stock/
            Décrémente le stock d'un produit.
            Appelé par order_service lors de la création d'une commande.
            \"""
            product = self.get_object()

            # TODO: récupérer 'quantity' depuis request.data
            # TODO: valider que quantity est un entier positif
            # TODO: vérifier que product.stock >= quantity
            #       si non → retourner Response({"error": "..."}, status=400)
            # TODO: décrémenter product.stock de 'quantity'
            # TODO: sauvegarder le produit
            # TODO: retourner le produit mis à jour avec son serializer


# EXPLICATION DES PARAMÈTRES @action :
#
#   detail=True
#     → l'action s'applique à UN produit
#     → génère l'URL : /products/{id}/decrement-stock/
#     → si detail=False → génère : /products/decrement-stock/
#
#   methods=['post']
#     → seul POST est accepté
#     → GET sur cet endpoint retournera 405 Method Not Allowed
#
#   url_path='decrement-stock'
#     → le segment d'URL après l'id
#     → sans cet argument, DRF utiliserait le nom de la méthode : 'decrement_stock'
#       ce qui donnerait /products/{id}/decrement_stock/ (underscore au lieu de tiret)


==============================================================================
EXEMPLE COMPLET DE decrement_stock
==============================================================================

    @action(detail=True, methods=['post'], url_path='decrement-stock')
    def decrement_stock(self, request, pk=None):
        product = self.get_object()

        quantity = request.data.get('quantity')

        # Validation de base
        if quantity is None:
            return Response(
                {"error": "Le champ 'quantity' est requis."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            return Response(
                {"error": "'quantity' doit être un entier."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if quantity <= 0:
            return Response(
                {"error": "'quantity' doit être supérieur à zéro."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Vérification du stock
        if product.stock < quantity:
            return Response(
                {
                    "error": "Stock insuffisant.",
                    "stock_disponible": product.stock,
                    "quantite_demandee": quantity,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Décrémentation
        product.stock -= quantity
        product.save(update_fields=['stock'])   # ← update_fields pour ne modifier QUE stock

        serializer = self.get_serializer(product)
        return Response(serializer.data)

# Pourquoi save(update_fields=['stock']) ?
# → Sans update_fields, Django envoie un UPDATE sur TOUTES les colonnes.
# → Avec update_fields, seule la colonne 'stock' est mise à jour.
# → C'est plus performant et moins risqué (pas d'écrasement accidentel des autres champs).


==============================================================================
TESTER L'ENDPOINT MANUELLEMENT
==============================================================================

Avant de câbler avec order_service, teste l'endpoint directement :

Option 1 — curl :

    # Créer d'abord un produit et noter son UUID
    curl http://catalogue.local/products/

    # Décrémenter le stock
    curl -X POST http://catalogue.local/products/{uuid}/decrement-stock/ \\
         -H "Content-Type: application/json" \\
         -d '{"quantity": 3}'

Option 2 — Dans le fichier product_service/api.http (déjà présent) :
Ajoute une nouvelle requête :

    ### Décrémentation du stock
    POST http://catalogue.local/products/{{product_id}}/decrement-stock/
    Content-Type: application/json

    {
        "quantity": 2
    }

Cas à tester :
  [ ] quantity valide + stock suffisant → 200, stock décrémenté dans la réponse
  [ ] quantity > stock → 400 avec "Stock insuffisant"
  [ ] quantity = 0 → 400 avec message d'erreur
  [ ] quantity négatif → 400
  [ ] product_id inexistant → 404 (géré automatiquement par get_object())


==============================================================================
CONSIDÉRATION : ATOMICITÉ
==============================================================================

Problème potentiel :
Si deux commandes arrivent en même temps pour le même produit,
il peut y avoir une race condition :

    Commande A : lit stock=5, vérifie 5 >= 3 ✓
    Commande B : lit stock=5, vérifie 5 >= 4 ✓
    Commande A : stock = 5 - 3 = 2, sauvegarde
    Commande B : stock = 5 - 4 = 1, sauvegarde  ← stock négatif !

Solution : utiliser select_for_update() pour verrouiller la ligne :

    from django.db import transaction

    @action(detail=True, methods=['post'], url_path='decrement-stock')
    def decrement_stock(self, request, pk=None):
        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=pk)
            # ... reste du code identique

Implémente d'abord la version simple, puis reviens ajouter transaction.atomic()
une fois que l'endpoint fonctionne correctement.


==============================================================================
CHECKLIST
==============================================================================

[ ] Imports ajoutés : action, Response, status
[ ] @action decrement_stock ajouté dans ProductViewSet
[ ] Validation de quantity (None, non-entier, négatif)
[ ] Vérification stock >= quantity
[ ] save(update_fields=['stock'])
[ ] Testé manuellement : cas nominal
[ ] Testé manuellement : stock insuffisant
[ ] Testé manuellement : produit inexistant


==============================================================================
PROCHAINE ÉTAPE
==============================================================================

→ Une fois cet endpoint fonctionnel, implémente :
    order_service/app/services_doc.py → check_and_decrement_stock()
"""

"""
ÉTAPE 5 — Structurer les sérializers avec appels inter-services (serializers.py)
===================================================================================

FICHIER À CRÉER:
    services/order_service/app/serializers.py


CONTEXTE:
---------
C'est la couche où on va:
    1. Valider les données entrantes du client
    2. Appeler product_service (synchrone)
    3. Créer les objets en base de données
    4. Retourner les réponses au client


STRUCTURE DU FICHIER:
---------------------

    import transaction
    from rest_framework import serializers
    from decimal import Decimal
    
    from .models import Order, OrderItem
    from .services import get_product, check_and_decrement_stock


    # Sérializer 1: Validation entré des items
    class OrderItemInputSerializer(serializers.Serializer):
        # Champs minimaux que le client doit envoyer
        # product_id (UUID), quantity (entier positif)
        pass


    # Sérializer 2: Affichage complet d'un item
    class OrderItemSerializer(serializers.ModelSerializer):
        # Champs de lecture en réponse
        pass


    # Sérializer 3: Principal (création + lecture de Commande)
    class OrderSerializer(serializers.ModelSerializer):
        items = OrderItemSerializer(many=True, read_only=True)
        items_input = OrderItemInputSerializer(many=True, write_only=True)
        
        class Meta:
            model = Order
            fields = [...]
            read_only_fields = [...]
        
        @transaction.atomic
        def create(self, validated_data):
            # Le cœur: synchronization avec product_service
            pass


DÉTAIL DE CHAQUE SÉRIALIZER:
-----------------------------

1. OrderItemInputSerializer:
   
   Objectif: Valider les données d'entrée MINIMALES pour chaque item.
   
   Le client envoie:
       {
           "product_id": "f47c3f5a-xxxx",
           "quantity": 5
       }
   
   À implémenter:
       - product_id: serializers.UUIDField()
       - quantity: serializers.IntegerField(min_value=1)
   
   Pas de Meta class (ce n'est pas un ModelSerializer).


2. OrderItemSerializer:
   
   Objectif: Affichage complet d'un OrderItem en réponse API.
   
   Champs à exposer (read_only):
       - id
       - product_id
       - product_name
       - unit_price
       - quantity
       - subtotal
       - created_at
       - updated_at
   
   read_only_fields:
       - id (généré par Django)
       - subtotal (calculé par OrderItem.save())
       - created_at, updated_at (auto_now)
   
   C'est un simple ModelSerializer.


3. OrderSerializer:
   
   Objectif: Gérer la création complète d'une Commande avec ses items.
   
   Champs en lecture:
       - id, user_id, client_id, status
       - total_amount (calculé)
       - items (nested read, via OrderItemSerializer)
       - created_at, updated_at
   
   Champs en écriture:
       - user_id (UUID)
       - client_id (UUID)
       - items_input (nom explicite pour bien séparer entrée/sortie)
   
   read_only_fields:
       - id, status (jamais modifié directement par l'API)
       - total_amount (calculé par update_total())
       - created_at, updated_at
   
   Imbrication items_input:
       items_input = OrderItemInputSerializer(many=True, write_only=True)
   
   Le create() doit:
       a) Extraire items_input avec .pop("items_input", [])
       b) Vérifier qu'il y a au moins un item
       c) Créer Order(**validated_data)
       d) Pour chaque item dans items_input:
           - product_id = str(item["product_id"])
           - quantity = item["quantity"]
           - product = get_product(product_id)   ← APPEL 1 : Récupération
           - update = check_and_decrement_stock(product_id, quantity)  ← APPEL 2 : Réservation
           - Créer OrderItem avec snapshot (product_name, unit_price)
       e) Refresher et retourner la commande


STRUCTURE COMPLÈTE TELLE QU'ATTENDUE:

    from decimal import Decimal
    from django.db import transaction
    from rest_framework import serializers
    
    from .models import Order, OrderItem
    from .services import get_product, check_and_decrement_stock


    class OrderItemInputSerializer(serializers.Serializer):
        # TODO: product_id = ?
        # TODO: quantity = ?
        pass


    class OrderItemSerializer(serializers.ModelSerializer):
        class Meta:
            model = OrderItem
            fields = [
                "id",
                "product_id",
                "product_name",
                "unit_price",
                "quantity",
                "subtotal",
                "created_at",
                "updated_at",
            ]
            read_only_fields = [...]  # TODO


    class OrderSerializer(serializers.ModelSerializer):
        # TODO: items = OrderItemSerializer(...)
        # TODO: items_input = OrderItemInputSerializer(...)
        
        class Meta:
            # TODO: model, fields, read_only_fields


CRÉATION DE COMMANDE EN DÉTAIL:

    @transaction.atomic
    def create(self, validated_data):
        # Step 1: Extraire items_input (will be empty list if not provided)
        items_data = validated_data.pop("items_input", [])
        
        # Step 2: Valider que c'est pas vide
        if not items_data:
            raise serializers.ValidationError(
                {"items_input": "Au moins un item obligatoire."}
            )
        
        # Step 3: Créer l'ordre
        order = Order.objects.create(**validated_data)
        
        # Step 4: Boucle sur chaque item
        for item in items_data:
            product_id = str(item["product_id"])
            quantity = item["quantity"]
            
            # Step 5a: APPEL SYNCHRONE 1 — Récupérer infos produit
            product = get_product(product_id)
            # Si ça lève une exception, le serializer la capture
            # et la retourne au client sous forme d'erreur 400/404
            
            # Step 5b: APPEL SYNCHRONE 2 — Réserver le stock
            check_and_decrement_stock(product_id, quantity)
            # Si stock insuffisant, levera ValidationError
            
            # Step 6: Créer l'item avec snapshot
            OrderItem.objects.create(
                order=order,
                product_id=product_id,
                product_name=product.get("name", "Inconnu"),
                unit_price=Decimal(str(product.get("price", "0"))),
                quantity=quantity,
                subtotal=Decimal("0"),  # sera recalculé dans OrderItem.save()
            )
            # OrderItem.save() appelle order.update_total() automatiquement
        
        # Step 7: Refresh la commande pour récupérer total_amount mis à jour
        order.refresh_from_db()
        
        # Step 8: Retourner
        return order


POINTS IMPORTANTS:
-------------------

🔴 TRANSACTION ATOMIQUE:
    @transaction.atomic garantit que:
    - SI un OrderItem échoue → TOUT est rollback
    - Pas de commande "orpheline" en base

🔴 APPELS SYNCHRONES:
    Les appels à get_product() et check_and_decrement_stock():
    - BLOQUENT jusqu'à la réponse
    - LÈVENT une exception si erreur
    - La transaction ROLLBACK si exception

🔴 SNAPSHOT (product_name, unit_price):
    Ces deux champs sont copiés au moment de la création.
    Si le prix change dans product_service après, l'ordre garde l'ancien prix.
    C'est intentionnel (évite les litiges).

🔴 DECIMAL:
    Toujours utiliser Decimal pour les prix (pas float).
    float peut avoir des erreurs d'arrondi.

🔴 CONVERSION UUID -> str:
    product_id est UUID en base mais doit être passé en str à get_product().
    Faire: product_id = str(item["product_id"])


TESTS MANUELS (dans le shell):
-------------------------------

    python manage.py shell
    from app.serializers import OrderSerializer
    from uuid import uuid4
    
    # Créer une commande valide
    data = {
        "user_id": uuid4(),
        "client_id": uuid4(),
        "items_input": [
            {"product_id": "uuid-du-produit-existant", "quantity": 2}
        ]
    }
    serializer = OrderSerializer(data=data)
    if serializer.is_valid():
        order = serializer.save()
        print(f"Commande créée: {order.id}")
    else:
        print(serializer.errors)  # Afficher les erreurs


ERREURS COURANTES À ÉVITER:
----------------------------

❌ Ne pas faire:
    order = Order.objects.create(
        **validated_data,
        items_input=items_data  # MAUVAIS! items_input n'est pas un champ Django
    )

✅ Faire:
    items_data = validated_data.pop("items_input")
    order = Order.objects.create(**validated_data)
    # Ensuite créer les items manuellement

❌ Ne pas faire:
    response.json().get("price")  # risque KeyError

✅ Faire:
    response.json().get("price", "0")  # default value sûr

❌ Ne pas faire:
    product["price"]  # risque KeyError si clé manquante

✅ Faire:
    product.get("price", "0")
"""

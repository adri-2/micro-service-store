"""
GUIDE — serializers.py pour order_service
==========================================

Ce fichier est un guide d'implémentation.
Une fois implémenté, crée le vrai fichier :
    order_service/app/serializers.py


CONTEXTE IMPORTANT
------------------
order_service est le plus complexe à sérialiser parce que :

1. OrderItem est lié à Order (ForeignKey interne)
2. OrderItem référence un produit via product_id (UUID) — PAS de ForeignKey
3. Les champs product_name et unit_price sont des SNAPSHOTS
   → ils doivent être fournis au moment de la création depuis catalogue-service
   → le client API ne doit pas les fournir directement
4. total_amount dans Order est calculé automatiquement via update_total()
   → il doit être read_only dans l'API

Modèles concernés (order_service/app/models.py) :

    class Order
        id           = UUIDField (primary_key)
        user_id      = UUIDField  (référence account_service)
        client_id    = UUIDField  (référence account_service)
        status       = CharField (TextChoices: Pending/Confirmed/Cancelled)
        total_amount = DecimalField (calculé automatiquement)

    class OrderItem
        order        = ForeignKey(Order)        ← relation INTERNE
        product_id   = UUIDField                ← référence catalogue-service (pas de FK)
        product_name = CharField (snapshot)
        unit_price   = DecimalField (snapshot)
        quantity     = PositiveIntegerField
        subtotal     = DecimalField (calculé : unit_price * quantity)


==============================================================================
SERIALIZER 1 : OrderItemSerializer
==============================================================================

Pourquoi commencer par OrderItem et pas Order ?
→ OrderSerializer va imbriquer OrderItemSerializer.
  Il faut créer l'enfant avant le parent (comme pour les modèles).

Structure à implémenter :

    class OrderItemSerializer(serializers.ModelSerializer):

        class Meta:
            model = OrderItem
            fields = [
                'id',
                'product_id',
                'product_name',   # snapshot : lu depuis l'API, mais idéalement
                'unit_price',     # renseigné via services.py (catalogue-service)
                'quantity',
                'subtotal',       # calculé automatiquement dans le model.save()
            ]
            read_only_fields = ???
            # TODO: quels champs sont calculés automatiquement et ne doivent
            #       pas être fournis par le client API ?
            # Réponse : 'id', 'subtotal', 'product_name', 'unit_price'
            # (ces deux derniers seront remplis par services.py, pas par l'utilisateur)


# EXPLICATION : pourquoi product_name et unit_price sont read_only ICI ?
#
# Quand un utilisateur passe une commande, il envoie :
#   { "product_id": "uuid...", "quantity": 2 }
#
# C'est order_service (via services.py) qui doit :
#   1. Appeler catalogue-service avec product_id
#   2. Récupérer name et price
#   3. Remplir product_name et unit_price AVANT de sauvegarder
#
# Donc dans le serializer d'entrée (création), ces champs sont write_only.
# Dans le serializer de sortie (lecture), ces champs sont retournés.
#
# Solution : utiliser deux serializers séparés (un pour l'écriture, un pour la lecture)
# OU utiliser un seul avec des méthodes to_representation / to_internal_value.
#
# Pour commencer, utilise UN seul serializer et reviens sur ce point une fois
# que la communication inter-services sera implémentée.


==============================================================================
SERIALIZER 2 : OrderSerializer
==============================================================================

C'est le serializer principal. Il doit :
- Afficher les items imbriqués en lecture (nested read)
- Accepter une liste d'items en écriture (nested write)
- Rendre total_amount en lecture seule (calculé par update_total())

Structure à implémenter :

    class OrderSerializer(serializers.ModelSerializer):

        # Lecture imbriquée : afficher les items complets dans la réponse GET
        items = OrderItemSerializer(many=True, read_only=True)

        # Écriture imbriquée : accepter une liste d'items dans POST
        # Pourquoi un champ séparé ?
        # Parce que DRF ne gère pas automatiquement la création d'objets imbriqués.
        # On déclare un champ write_only pour recevoir les données,
        # puis on les traite manuellement dans create().
        items_input = serializers.ListField(
            child=serializers.DictField(),   # chaque item est un dict
            write_only=True,
        )

        class Meta:
            model = Order
            fields = [
                'id',
                'user_id',
                'client_id',
                'status',
                'total_amount',  # read_only
                'items',         # read_only (lecture imbriquée)
                'items_input',   # write_only (écriture)
                'created_at',
            ]
            read_only_fields = ['id', 'total_amount', 'created_at', 'status']
            # Pourquoi status en read_only ici ?
            # Il vaut mieux gérer le changement de status via une action dédiée
            # (ex: POST /orders/{id}/confirm/) plutôt que de laisser l'API
            # accepter n'importe quel status à la création.

        def create(self, validated_data):
            # TODO: Extraire items_input de validated_data avec .pop()
            # TODO: Créer l'objet Order sans les items
            # TODO: Pour chaque item dans items_input :
            #         - À ce stade, l'item contient { product_id, quantity }
            #         - Appeler services.get_product(product_id) pour obtenir name et price
            #           (cette étape sera implémentée dans services.py)
            #         - Créer l'objet OrderItem avec toutes les données
            # TODO: Retourner la commande
            pass


# EXEMPLE de structure de create() :
#
#   def create(self, validated_data):
#       items_data = validated_data.pop('items_input')
#       order = Order.objects.create(**validated_data)
#       for item_data in items_data:
#           product_id = item_data['product_id']
#           quantity = item_data['quantity']
#           # TODO: récupérer le produit depuis catalogue-service
#           # product = CatalogueServiceClient.get_product(product_id)
#           OrderItem.objects.create(
#               order=order,
#               product_id=product_id,
#               product_name=????,   # TODO: depuis le produit récupéré
#               unit_price=????,     # TODO: depuis le produit récupéré
#               quantity=quantity,
#               subtotal=0,          # sera recalculé dans OrderItem.save()
#           )
#       return order


==============================================================================
CAS PARTICULIER : Nested Write en DRF
==============================================================================

DRF ne gère pas la création imbriquée automatiquement.
Si tu envoies :

    POST /orders/
    {
        "user_id": "uuid...",
        "client_id": "uuid...",
        "items_input": [
            { "product_id": "uuid...", "quantity": 2 }
        ]
    }

DRF va valider les données, mais c'est À TOI d'implémenter create()
pour créer les OrderItem associés.

C'est pourquoi la méthode create() est obligatoire ici
(contrairement à CategorySerializer qui utilisait le create() par défaut).


==============================================================================
QUESTION : Un ou deux serializers pour Order ?
==============================================================================

Bonne pratique : séparer le serializer de lecture et d'écriture.

    class OrderReadSerializer(serializers.ModelSerializer):
        items = OrderItemSerializer(many=True, read_only=True)
        ...

    class OrderWriteSerializer(serializers.ModelSerializer):
        items_input = serializers.ListField(...)
        def create(self, validated_data): ...

Dans les views, tu utilises alors :
- OrderReadSerializer pour GET
- OrderWriteSerializer pour POST

Pour commencer, utilise un seul serializer.
Sépare-les quand tu verras que ça devient trop complexe à maintenir.


==============================================================================
CHECKLIST AVANT DE PASSER AUX VIEWS
==============================================================================

[ ] order_service/app/serializers.py créé
[ ] OrderItemSerializer avec les bons read_only_fields
[ ] OrderSerializer avec items (read) et items_input (write)
[ ] total_amount en read_only
[ ] Méthode create() dans OrderSerializer (même vide pour l'instant)
[ ] Testé dans le shell Django :
      from app.serializers import OrderSerializer


==============================================================================
PROCHAINE ÉTAPE
==============================================================================

→ Ouvre order_service/app/services_doc.py
  pour implémenter la communication avec catalogue-service.
  C'est ce qui va nourrir product_name et unit_price lors du create().
"""

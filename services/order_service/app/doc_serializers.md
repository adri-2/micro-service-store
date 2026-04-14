# doc_serializers.md

Documentation détaillée pour [serializers.py](serializers.py).

## Rôle du fichier

Ce fichier transforme les modèles `Order` et `OrderItem` en données JSON, et inversement, pour l'API REST du service de commandes.

Le point important ici est que la création d'une commande ne se limite pas à enregistrer des champs. Le serializer orchestre aussi la récupération des données externes nécessaires pour construire un snapshot fiable de la commande.

## Flux global

1. Le client envoie une commande avec `user_id`, `client_id` et `items_input`.
2. `OrderSerializer.create()` récupère le token d'authentification depuis la requête.
3. Le serializer valide que la liste d'items n'est pas vide.
4. Il appelle les services externes pour récupérer l'utilisateur, le client et les produits.
5. Il crée l'objet `Order` avec les noms figés au moment de la commande.
6. Il crée chaque `OrderItem` avec un snapshot du produit.
7. Le total est recalculé automatiquement via `Order.update_total()`.

## `OrderItemSerializer`

Ce serializer est utilisé pour la lecture des items associés à une commande.

```python
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
        read_only_fields = fields
```

### Explication

- Tous les champs sont en lecture seule.
- `product_name` et `unit_price` sont des snapshots, donc ils ne doivent pas être modifiés par le client.
- `subtotal` est calculé par le modèle.
- `created_at` et `updated_at` sont gérés automatiquement.

## `OrderItemInputSerializer`

Ce serializer sert à valider les données minimales envoyées par le client lors de la création.

```python
class OrderItemInputSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)

    class Meta:
        model = OrderItem
        fields = ["product_id", "quantity"]
```

### Explication

- Le client n'envoie que `product_id` et `quantity`.
- `quantity` est contrainte à une valeur minimale de `1`.
- Les champs calculés ou enrichis par le backend restent absents de l'entrée.

## `OrderSerializer`

Ce serializer pilote la création et la lecture d'une commande complète.

```python
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    items_input = OrderItemInputSerializer(many=True, write_only=True)
```

### Explication

- `items` est utilisé pour la lecture.
- `items_input` est utilisé pour l'écriture.
- Cette séparation évite de mélanger les données de sortie et d'entrée.

### Champs exposés

```python
class Meta:
    model = Order
    fields = [
        "id",
        "user_id",
        "client_id",
        "user_name",
        "client_name",
        "total_amount",
        "items",
        "items_input",
        "created_at",
        "status",
        "updated_at",
    ]
```

### Explication

- `id`, `total_amount`, `created_at`, `updated_at`, `user_name` et `client_name` sont en lecture seule.
- `status` est aussi protégé pour éviter qu'un client force un état arbitraire au moment de la création.
- Le changement de statut doit passer par une action métier dédiée, par exemple `confirm` dans les views.

## Méthode `create()`

```python
@transaction.atomic
def create(self, validated_data):
    items_data = validated_data.pop("items_input", [])
    request = self.context.get("request")

    access_token = None
    if request:
        access_token = request.META.get("HTTP_AUTHORIZATION")

    if not items_data:
        raise ValidationError({"items_input": "Au moins un item obligatoire."})

    try:
        user = get_user(str(validated_data["user_id"]), access_token)
    except Exception:
        raise ValidationError({"user_id": "User introuvable."})

    try:
        customer = get_customer(str(validated_data["client_id"]), access_token)
    except Exception:
        raise ValidationError({"client_id": "Client introuvable."})

    order = Order.objects.create(
        user_id=validated_data["user_id"],
        user_name=user.get("username", "Inconnu"),
        client_id=validated_data["client_id"],
        client_name=f"{customer.get('first_name','')} {customer.get('last_name','')}".strip(),
        status=Order.StatusChoices.DRAFT,
    )

    product_ids = [str(item["product_id"]) for item in items_data]

    try:
        product_map = get_products_bulk(product_ids, access_token)
    except Exception:
        raise ValidationError("Erreur recuperation produits")

    for item in items_data:
        product = product_map.get(str(item["product_id"]))
        if not product:
            raise ValidationError({"items_input": f"Produit {item['product_id']} introuvable"})

        unit_price = Decimal(str(product["price"]))

        OrderItem.objects.create(
            order=order,
            product_id=item["product_id"],
            product_name=product["name"],
            unit_price=unit_price,
            quantity=item["quantity"],
            subtotal=unit_price * item["quantity"],
        )

    order.update_total()
    return order
```

### Explication ligne par ligne

- `transaction.atomic` garantit que toute la création est annulée si une étape échoue.
- `items_input` est retiré de `validated_data` car il sert à construire des objets liés.
- Le token est lu depuis `HTTP_AUTHORIZATION` pour transmettre le contexte d'authentification aux services externes.
- Si `items_input` est vide, la commande est rejetée immédiatement.
- `get_user()` et `get_customer()` permettent de figer les noms au moment de la commande.
- `Order.objects.create()` enregistre une commande avec statut `DRAFT`.
- `get_products_bulk()` évite un appel réseau par produit et récupère les produits en lot.
- Chaque `OrderItem` reçoit son snapshot: nom, prix unitaire, quantité et sous-total.
- `order.update_total()` recalcule le total global à partir des sous-totaux.

## Points d'attention

- Le serializer suppose que les fonctions `get_user`, `get_customer` et `get_products_bulk` existent dans `app.services`.
- Si ces helpers changent de contrat JSON, le serializer doit être adapté.
- Le `except Exception` est fonctionnel mais large; il peut être affiné plus tard pour mieux distinguer les erreurs réseau, 404 et validation métier.

## Résultat attendu

Avec ce serializer, une requête `POST /orders/` peut créer une commande complète et cohérente, sans dépendre du client pour fournir des valeurs sensibles comme le nom du produit ou le prix.

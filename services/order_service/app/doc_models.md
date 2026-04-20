# doc_models.md

Documentation détaillée pour [models.py](models.py).

## Rôle du fichier

Ce fichier définit la structure des données du service de commandes.

Il contient:

1. une base commune avec les timestamps,
2. le modèle `Order`,
3. le modèle `OrderItem`.

## `BaseModel`

```python
class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

### Explication

- `created_at` est rempli à la création.
- `updated_at` est mis à jour à chaque sauvegarde.
- La classe est abstraite pour réutiliser les champs sans créer de table séparée.

## `Order`

```python
class Order(BaseModel):
    class StatusChoices(models.TextChoices):
        DRAFT = 'Draft', 'Draft'
        PENDING = 'Pending', 'Pending'
        CONFIRMED = 'Confirmed', 'Confirmed'
        CANCELLED = 'Cancelled', 'Cancelled'
```

### Explication

- Les statuts sont centralisés dans `TextChoices`.
- Cela évite les chaînes magiques dispersées dans le code.

```python
id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
user_id = models.UUIDField()
user_name = models.CharField(max_length=150)
client_id = models.UUIDField()
client_name = models.CharField(max_length=150)
status = models.CharField(max_length=10, choices=StatusChoices.choices, default=StatusChoices.DRAFT)
total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
```

### Explication

- `user_id` et `client_id` sont des références logiques vers d'autres services, pas des ForeignKey Django.
- `user_name` et `client_name` sont des snapshots d'affichage.
- `total_amount` est calculé à partir des `OrderItem`.

### `update_total()`

```python
def update_total(self):
    total = self.items.aggregate(total=models.Sum("subtotal"))["total"] or 0
    self.total_amount = total
    self.save(update_fields=["total_amount"])
```

### Explication

- Le total est recalculé depuis les lignes de commande.
- Cela évite les divergences entre la commande et ses items.

### Métadonnées

```python
class Meta:
    ordering = ["-created_at"]
```

### Explication

- Les commandes les plus récentes apparaissent d'abord.

## `OrderItem`

```python
class OrderItem(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product_id = models.UUIDField()
    product_name = models.CharField(max_length=150)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
```

### Explication

- `order` relie l'item à sa commande.
- `product_id` référence le catalogue produit.
- `product_name` et `unit_price` sont stockés comme snapshot.
- `subtotal` représente le total de la ligne.

### `clean()`

```python
def clean(self):
    if self.quantity <= 0:
        raise ValidationError("Quantité invalide.")
```

### Explication

- La quantité doit toujours être strictement positive.

### `save()`

```python
def save(self, *args, **kwargs):
    self.subtotal = self.unit_price * self.quantity
    super().save(*args, **kwargs)
    self.order.update_total()
```

### Explication

- Le sous-total est recalculé automatiquement.
- Après sauvegarde, le total de la commande est aussi recalculé.

### `delete()`

```python
def delete(self, *args, **kwargs):
    order = self.order
    super().delete(*args, **kwargs)
    order.update_total()
```

### Explication

- Quand une ligne est supprimée, le total de la commande doit être mis à jour.

## Résultat attendu

Ces modèles garantissent que les commandes conservent un historique cohérent, même si les produits ou les utilisateurs changent dans les autres microservices.

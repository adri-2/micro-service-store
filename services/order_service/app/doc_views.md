# doc_views.md

Documentation détaillée pour [views.py](views.py).

## Rôle du fichier

Ce fichier expose les endpoints HTTP du service de commandes et contient la logique de contrôle autour du serializer et du cache.

Les responsabilités principales sont:

1. exposer un endpoint de santé,
2. fournir un endpoint de diagnostic cache,
3. gérer le `ViewSet` des commandes,
4. invalider le cache quand les données changent,
5. proposer une action métier dédiée pour confirmer une commande.

## `health()`

```python
def health(request):
    return JsonResponse({"status": "ok", "message": "Order service is healthy."})
```

### Explication

- Endpoint simple pour les checks d'infrastructure.
- Il ne dépend ni de la base de données ni des services externes.

## `cache_probe()`

```python
@permission_classes([permissions.AllowAny])
def cache_probe(request):
    cache_key = "api-cache:debug:order"
    ttl_seconds = 30

    cached_payload = cache.get(cache_key)
    if cached_payload is not None:
        return JsonResponse({"cache": "HIT", "key": cache_key, "ttl_seconds": ttl_seconds, "payload": cached_payload})

    payload = {
        "generated_at": timezone.now().isoformat(),
        "message": "Payload genere sur MISS puis stocke dans Redis.",
    }
    cache.set(cache_key, payload, ttl_seconds)
    return JsonResponse({"cache": "MISS", "key": cache_key, "ttl_seconds": ttl_seconds, "payload": payload})
```

### Explication

- Cet endpoint sert à vérifier rapidement que Redis fonctionne.
- Il renvoie `HIT` si la réponse est déjà en cache.
- Il renvoie `MISS` puis stocke une nouvelle payload sinon.

## Helpers de cache

### `_build_cache_key()`

```python
def _build_cache_key(prefix, request):
    path_hash = hashlib.md5(request.get_full_path().encode("utf-8")).hexdigest()
    return f"api-cache:{prefix}:{path_hash}"
```

### Explication

- La clé de cache dépend du chemin complet de la requête.
- Deux URLs différentes produisent deux clés différentes.

### `_invalidate_api_cache()`

```python
def _invalidate_api_cache():
    if hasattr(cache, "delete_pattern"):
        cache.delete_pattern("api-cache:*")
    else:
        cache.clear()
```

### Explication

- Après une création, modification ou suppression, le cache liste doit être invalidé.
- `delete_pattern()` est utilisé si le backend de cache le supporte.

## `OrderViewSet`

```python
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.prefetch_related("items")
    permission_classes = [permissions.IsAuthenticated]
```

### Explication

- Le `prefetch_related("items")` limite les requêtes SQL supplémentaires.
- L'authentification est obligatoire pour accéder aux commandes.

## Méthode `list()`

```python
def list(self, request, *args, **kwargs):
    cache_key = _build_cache_key("orders:list", request)
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return Response(cached_data)

    response = super().list(request, *args, **kwargs)
    if response.status_code == status.HTTP_200_OK:
        cache.set(cache_key, response.data, CACHE_TTL_SECONDS)

    return response
```

### Explication

- La liste des commandes est mise en cache pour réduire la charge.
- Si la réponse est déjà présente, elle est renvoyée directement.
- Le cache est stocké seulement pour les réponses `200 OK`.

## Méthode `get_serializer_class()`

```python
def get_serializer_class(self):
    if self.action in ['create', 'update', 'partial_update']:
        return OrderSerializer
    elif self.action == 'list':
        return OrderListSerializer
    return OrderDetailSerializer
```

### Explication

- Le serializer dépend de l'action DRF en cours.
- La liste, le détail et l'écriture n'ont pas exactement les mêmes besoins.

## `perform_create()`, `perform_update()`, `perform_destroy()`

```python
def perform_create(self, serializer):
    serializer.save()
    _invalidate_api_cache()

def perform_update(self, serializer):
    serializer.save()
    _invalidate_api_cache()

def perform_destroy(self, instance):
    instance.delete()
    _invalidate_api_cache()
```

### Explication

- Chaque mutation invalide le cache des listes.
- Cela évite de renvoyer des données obsolètes.

## `get_queryset()`

```python
def get_queryset(self):
    qs = Order.objects.prefetch_related("items")
    status_filter = self.request.query_params.get("status")
    if status_filter:
        qs = qs.filter(status=status_filter)
    return qs
```

### Explication

- Le filtre `status` permet d'interroger uniquement un sous-ensemble de commandes.
- La prélecture des items reste active même avec filtre.

## Action `confirm()`

```python
@action(detail=True, methods=['post'], url_path='confirm')
def confirm(self, request, pk=None):
    order = self.get_object()
    if order.status != Order.StatusChoices.PENDING:
        return Response({"detail": "Seules les commandes Pending peuvent être confirmées."}, status=status.HTTP_400_BAD_REQUEST)

    order.status = Order.StatusChoices.CONFIRMED
    order.save(update_fields=["status", "updated_at"])
    serializer = self.get_serializer(order)
    return Response(serializer.data, status=status.HTTP_200_OK)
```

### Explication

- Cette action isole une règle métier précise: seule une commande `Pending` peut devenir `Confirmed`.
- Le changement de statut n'est pas exposé comme un simple champ modifiable dans le serializer.

## Résultat attendu

Ce fichier structure les endpoints publics du service de commandes, gère le cache de lecture et conserve les règles métiers hors des serializers.

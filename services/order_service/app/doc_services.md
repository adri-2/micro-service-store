# doc_services.md

Documentation détaillée pour le package de services réseau de `order_service`.

## Rôle du package

Le package `app/services/` centralise les appels HTTP vers les autres microservices.

Cette couche évite de disperser les détails réseau dans les serializers et les views. Elle contient la logique pour:

1. construire les URL,
2. gérer le token d'authentification,
3. appeler les endpoints distants,
4. convertir les erreurs HTTP en exceptions DRF exploitables,
5. mettre en cache certaines réponses.

## Fichier `app/services/__init__.py`

```python
from .product_service import get_product, get_products, get_products_bulk
from .user_service import get_user, get_customer, get_users_bulk, get_customers_bulk
```

### Explication

- Ce fichier expose une API simple au reste de l'application.
- Le serializer peut importer directement `get_user`, `get_customer` ou `get_products_bulk` sans connaître le fichier interne qui les implémente.

## Fichier `app/services/product_service.py`

### Helpers internes

```python
def _build_url(path: str) -> str:
    base = settings.CATALOGUE_SERVICE_URL.rstrip("/")
    clean_path = path.lstrip("/")
    return f"{base}/{clean_path}"
```

### Explication

- L'URL de base vient des settings.
- `rstrip` et `lstrip` évitent les doubles slash.

```python
def _auth_headers(access_token: str | None) -> dict:
    if not access_token:
        return {}
    token = access_token.strip()
    if token.lower().startswith("bearer "):
        return {"Authorization": token}
    return {"Authorization": f"Bearer {token}"}
```

### Explication

- Cette fonction normalise le header `Authorization`.
- Elle accepte un token brut ou déjà préfixé par `Bearer `.

```python
def _cache_key(prefix: str, suffix: str, access_token: str | None = None) -> str:
    scope = _token_scope(access_token)
    return f"ext-catalogue:{prefix}:{suffix}:{scope}"
```

### Explication

- Le cache est isolé par token pour éviter de mélanger des résultats autorisés différemment.

### `get_product()`

```python
def get_product(product_id: str, access_token: str | None = None) -> dict:
    cache_key = _cache_key("product", str(product_id), access_token)

    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data

    url = _build_url(f"products/{product_id}/")
    headers = _auth_headers(access_token)

    try:
        response = requests.get(url, timeout=5, headers=headers)
        if response.status_code == 404:
            raise NotFound(f"Produit {product_id} introuvable.")
        if response.status_code != 200:
            raise ValidationError("Erreur du service catalogue.")

        product_data = response.json()
        cache.set(cache_key, product_data, timeout=PRODUCT_CACHE_TTL)
        return product_data

    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        raise ValidationError("Le service catalogue est injoignable ou trop lent.") from e
```

### Explication

- Le cache évite de refaire un appel réseau pour le même produit.
- Les erreurs de connexion et de timeout sont transformées en `ValidationError`.
- Un `404` devient `NotFound`.

### `get_products_bulk()`

```python
def get_products_bulk(product_ids, access_token=None):
    results = {}
    missing_ids = []
    unique_product_ids = sorted({str(pid) for pid in product_ids})

    for pid in unique_product_ids:
        cache_key = _cache_key("product", pid, access_token)
        cached = cache.get(cache_key)
        if cached is not None:
            results[pid] = cached
        else:
            missing_ids.append(pid)

    if missing_ids:
        url = _build_url("products/bulk/")
        headers = _auth_headers(access_token)

        try:
            response = requests.post(
                url,
                json={"ids": missing_ids},
                timeout=5,
                headers=headers
            )
        except requests.exceptions.ConnectionError as e:
            raise ValidationError("catalogue-service est inaccessible.") from e
        except requests.exceptions.Timeout as e:
            raise ValidationError("catalogue-service n'a pas répondu à temps.") from e

        if response.status_code != 200:
            raise ValidationError("Erreur récupération produits")

        data = response.json().get("results", {})

        for pid, product in data.items():
            cache.set(_cache_key("product", str(pid), access_token), product, timeout=PRODUCT_CACHE_TTL)
            results[pid] = product

    return results
```

### Explication

- Les IDs sont dédupliqués avant l'appel réseau.
- Les éléments déjà en cache ne repassent pas par le service externe.
- Les réponses reçues sont aussi stockées en cache.

## Fichier `app/services/user_service.py`

### `get_user()`

```python
def get_user(user_id: str, access_token: str | None = None) -> dict:
    url = _build_url(f"user/me/{user_id}/")
    headers = _auth_headers(access_token)
    try:
        response = requests.get(url, timeout=5, headers=headers)
    except requests.exceptions.ConnectionError as e:
        raise ValidationError("account-service est inaccessible.") from e
    except requests.exceptions.Timeout as e:
        raise ValidationError("account-service n'a pas répondu à temps.") from e

    if response.status_code == status.HTTP_404_NOT_FOUND:
        raise NotFound("L'utilisateur n'existe pas.")
    if response.status_code != status.HTTP_200_OK:
        raise ValidationError("Une erreur est survenue lors de la récupération de l'utilisateur.")
    return response.json()
```

### Explication

- Cette fonction interroge `account_service`.
- Elle convertit les réponses HTTP en exceptions DRF adaptées à l'API.

### `get_customer()`

Le même schéma est utilisé pour récupérer un client, avec une URL différente et des messages d'erreur adaptés.

### Fonctions bulk

`get_users_bulk()` et `get_customers_bulk()` envoient une liste d'IDs vers les endpoints batch du service compte, puis renvoient le dictionnaire `results`.

## Comment ces fonctions sont utilisées

Dans `OrderSerializer.create()`:

```python
user = get_user(str(validated_data["user_id"]), access_token)
customer = get_customer(str(validated_data["client_id"]), access_token)
product_map = get_products_bulk(product_ids, access_token)
```

### Explication

- Le serializer utilise le package de services comme une passerelle unique.
- La logique métier reste dans le serializer.
- La communication réseau reste dans `app/services/`.

## Point d'attention

- Le fichier `app/services.py` n'existe pas dans ce projet. L'architecture réelle utilise le package `app/services/`.
- Si tu ajoutes de nouveaux appels réseau, crée-les dans ce package plutôt que directement dans les views.

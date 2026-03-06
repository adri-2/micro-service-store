# Parcours Debutant: Microservices Django (Communication Synchrone)

## Pour qui est ce guide

Ce guide est pour toi si:

- tu debutes en Django REST Framework
- tu apprends encore les APIs
- tu veux avancer pas a pas, sans theorie compliquee

## Objectif simple

Faire marcher ce flux:

1. Le client envoie `POST /orders/` a `order_service`.
2. `order_service` appelle `product_service` pour lire le produit.
3. `order_service` appelle `product_service` pour baisser le stock.
4. `order_service` cree la commande et renvoie la reponse.

## Ce que tu vas faire (version facile)

1. Ajouter un endpoint `health` sur les 2 services.
2. Ajouter un endpoint metier dans `product_service`:
   `POST /products/{id}/decrement-stock/`.
3. Creer `order_service/app/services.py` pour les appels HTTP.
4. Creer `order_service/app/serializers.py` pour creer la commande.
5. Ajouter `OrderViewSet` + routes dans `order_service`.
6. Tester avec `curl`.

## Regle d or (important)

- Toujours mettre `timeout=5` sur les appels HTTP inter-services.

## Etape 0: verifier la base

- Fichiers utiles:
  - `services/product_service/app/views.py`
  - `services/order_service/app/views.py`
  - `services/order_service/core/urls.py`
- Test rapide:

```bash
curl http://localhost:8001/health/
curl http://localhost:8002/health/
```

## Etape 1: product_service (fournisseur)

Objectif: permettre a `order_service` de reserver le stock.

Fichier:

- `services/product_service/app/views.py`

Ajouts:

- action DRF custom `decrement_stock`
- validations:
  - quantity entier
  - quantity > 0
  - stock suffisant

Resultat attendu:

- URL active: `POST /products/{id}/decrement-stock/`

## Etape 2: order_service (couche HTTP)

Objectif: isoler les appels reseau dans un seul fichier.

Fichier a creer:

- `services/order_service/app/services.py`

Fonctions a faire:

- `_build_url(path)`
- `get_product(product_id)`
- `check_and_decrement_stock(product_id, quantity)`

## Etape 3: configuration URL

Fichier:

- `services/order_service/core/settings.py`

Ajouter:

- `CATALOGUE_SERVICE_URL = os.environ.get("CATALOGUE_SERVICE_URL", "http://localhost:8001")`

## Etape 4: serializers

Fichier a creer:

- `services/order_service/app/serializers.py`

A faire:

- serializer input item (`product_id`, `quantity`)
- serializer item sortie
- serializer order avec `create()`:
  - get product
  - decrement stock
  - create order item

## Etape 5: views + routes

Fichiers:

- `services/order_service/app/views.py`
- `services/order_service/core/urls.py`

A faire:

- `health`
- `OrderViewSet`
- actions `confirm` et `cancel`
- routeur DRF `orders`

## Etape 6: tests minimum

1. `GET /health/` sur les 2 services
2. creer un produit
3. tester `decrement-stock`
4. creer une commande
5. verifier que le stock diminue

## Si tu bloques

Lis les fichiers de detail deja presents:

- `services/product_service/app/STEP_1_INSTRUCTIONS.py`
- `services/order_service/app/STEP_2_INSTRUCTIONS.py`
- `services/order_service/app/STEP_5_INSTRUCTIONS.py`
- `services/order_service/app/STEP_6_INSTRUCTIONS.py`

Ce parcours est volontairement simple. Tu peux ignorer la partie "architecture avancee" pour le moment.

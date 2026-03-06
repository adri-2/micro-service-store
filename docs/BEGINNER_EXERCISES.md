# Exercices Debutant (Pratique)

## Exercice 1 - Health checks

Objectif: verifier que tes services repondent.

A faire:

1. ajouter `health` dans `product_service` si besoin
2. ajouter `health` dans `order_service`
3. tester:

```bash
curl http://localhost:8001/health/
curl http://localhost:8002/health/
```

Succes si:

- tu reçois `{"status": "ok"}` sur les 2 URLs

## Exercice 2 - Endpoint decrement stock

Objectif: creer l endpoint metier cote produit.

A faire:

1. dans `services/product_service/app/views.py`, ajouter une action `decrement_stock`
2. valider `quantity`
3. decrementer `product.stock`

Test:

```bash
curl -X POST http://localhost:8001/products/{id}/decrement-stock/ \
  -H "Content-Type: application/json" \
  -d '{"quantity": 2}'
```

Succes si:

- stock diminue
- erreur 400 quand stock insuffisant

## Exercice 3 - Appel HTTP depuis order_service

Objectif: faire parler un service a un autre.

A faire:

1. creer `services/order_service/app/services.py`
2. coder `get_product()`
3. coder `check_and_decrement_stock()`
4. mettre `timeout=5`

Succes si:

- `get_product()` renvoie un JSON produit valide

## Exercice 4 - Creation de commande synchrone

Objectif: creer la commande avec appels inter-services.

A faire:

1. creer `services/order_service/app/serializers.py`
2. dans `OrderSerializer.create()`:
   - lire `items_input`
   - appeler `get_product()`
   - appeler `check_and_decrement_stock()`
   - creer `OrderItem`

Succes si:

- `POST /orders/` cree la commande
- le stock du produit baisse

## Exercice 5 - Routes et actions

Objectif: exposer les endpoints utiles.

A faire:

1. dans `services/order_service/app/views.py`, ajouter `OrderViewSet`
2. ajouter actions `confirm` et `cancel`
3. dans `services/order_service/core/urls.py`, enregistrer le routeur

Succes si:

- `POST /orders/{id}/confirm/` fonctionne
- `POST /orders/{id}/cancel/` fonctionne

## Verification finale

Tu as termine si:

- health OK sur les 2 services
- decrement stock OK
- creation commande OK
- stock mis a jour
- confirm/cancel OK

## Conseil apprentissage

Si une etape casse:

1. tester endpoint par endpoint
2. lire logs serveur
3. corriger une erreur a la fois
4. retester tout de suite

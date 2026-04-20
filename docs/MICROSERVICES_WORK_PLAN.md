# Plan de Travail Détaillé : Communication Synchrone Microservices

## 📋 Vue d'Ensemble

Tu vas implémenter une **communication HTTP synchrone** entre deux services Django:

- **product_service** = fournisseur (expose les produits)
- **order_service** = consommateur (crée les commandes)

**Quand une commande est créée:**

1. order_service appelle product_service (GET)
2. order_service appelle product_service (POST pour réserver le stock)
3. Si tout OK → commande sauvegardée
4. Réponse retournée au client

---

## 🎯 Étapes À Faire (dans cet ordre)

### ✅ ÉTAPE 1: Endpoint de décrémentation (product_service/views.py)

**Fichier à modifier**: `services/product_service/app/views.py`

**Instructions détaillées**: `services/product_service/app/STEP_1_INSTRUCTIONS.py`

**Résumé**:

- Ajouter une action DRF `@action` sur `ProductViewSet`
- Endpoint: `POST /products/{id}/decrement-stock/`
- Body: `{"quantity": 5}`
- Valider et décrémenter le stock
- Retourner le produit ou erreur 400/404

**Imports à ajouter**:

```python
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
```

---

### ✅ ÉTAPE 2: Couche de communication HTTP (order_service/app/services.py)

**Fichier à créer**: `services/order_service/app/services.py`

**Instructions détaillées**: `services/order_service/app/STEP_2_INSTRUCTIONS.py`

**Résumé**:

- Fonction `_build_url()`: construire les URLs
- Fonction `get_product()`: récupérer les infos du produit
- Fonction `check_and_decrement_stock()`: réserver le stock
- Toujours utiliser `timeout=5`
- Traduire les erreurs réseau en exceptions DRF

**À retenir**:

- Pas de `requests` directement dans les vues
- Centralisé dans `services.py`
- Gestion cohérente des erreurs

---

### ✅ ÉTAPE 3: Configuration URL du service distant (order_service/core/settings.py)

**Fichier à modifier**: `services/order_service/core/settings.py`

**Instructions détaillées**: `services/order_service/core/STEP_3_INSTRUCTIONS.py`

**Résumé**:

- Ajouter `import os`
- Ajouter `CATALOGUE_SERVICE_URL = os.environ.get(...)`
- Valeur par défaut: `http://localhost:8001`
- Read entire file and add at the bottom after REST_FRAMEWORK

---

### ✅ ÉTAPE 4: Dépendance HTTP (order_service/requirements.txt)

**Fichier à modifier**: `services/order_service/requirements.txt`

**Instructions détaillées**: `services/order_service/core/STEP_4_INSTRUCTIONS.py`

**Résumé**:

- Ajouter `requests>=2.31`
- Ensuite: `pip install -r requirements.txt`

---

### ✅ ÉTAPE 5: Sérializers avec orchestration (order_service/app/serializers.py)

**Fichier à créer**: `services/order_service/app/serializers.py`

**Instructions détaillées**: `services/order_service/app/STEP_5_INSTRUCTIONS.py`

**Résumé**:

- `OrderItemInputSerializer`: validation minimaledes items
- `OrderItemSerializer`: affichage complet
- `OrderSerializer`: le principal avec `create()` complexe
- `create()` doit:
  - Extraire `items_input`
  - Appeler `get_product()` (synchrone)
  - Appeler `check_and_decrement_stock()` (synchrone)
  - Créer les OrderItem avec snapshots
  - Utiliser `@transaction.atomic`

---

### ✅ ÉTAPE 6: API endpoints (order_service/app/views.py + core/urls.py)

**Fichiers à modifier**:

- `services/order_service/app/views.py`
- `services/order_service/core/urls.py`

**Instructions détaillées**: `services/order_service/app/STEP_6_INSTRUCTIONS.py`

**Résumé views.py**:

- Fonction `health()`: retourne `{"status": "ok"}`
- `OrderViewSet`: CRUD complet
- Action `confirm()`: Pending → Confirmed
- Action `cancel()`: Pending → Cancelled

**Résumé urls.py**:

- Routeur DRF pour OrderViewSet
- Route `health/`
- Génère automatiquement les 8 endpoints

---

## 📂 Structure des Fichiers

```
services/
  product_service/
    app/
      views.py                      ← MODIFIER (étape 1)
      STEP_1_INSTRUCTIONS.py        ← LIRE

  order_service/
    app/
      services.py                   ← CRÉER (étape 2)
      serializers.py                ← CRÉER (étape 5)
      views.py                      ← MODIFIER (étape 6)
      STEP_2_INSTRUCTIONS.py        ← LIRE
      STEP_5_INSTRUCTIONS.py        ← LIRE
      STEP_6_INSTRUCTIONS.py        ← LIRE
    
    core/
      settings.py                   ← MODIFIER (étape 3)
      urls.py                       ← MODIFIER (étape 6)
      STEP_3_INSTRUCTIONS.py        ← LIRE
      STEP_4_INSTRUCTIONS.py        ← LIRE
    
    requirements.txt                ← MODIFIER (étape 4)

docs/
  MICROSERVICES_SYNC_GUIDE.md      ← ARCHITECTURE
  MICROSERVICES_WORK_PLAN.md       ← CE FICHIER
```

---

## 🧪 Plan de Test

### Test 1: Health check

```bash
curl http://localhost:8001/health/
curl http://localhost:8002/health/
```

Attendre: `{"status": "ok"}`

### Test 2: Créer un produit de test

```bash
curl -X POST http://localhost:8001/products/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Product",
    "price": "99.99",
    "stock": 10,
    "category_id": "UUID-DU-CATEGORY"
  }'
```

Noter le `product_id` retourné.

### Test 3: Tester decrement-stock seul

```bash
curl -X POST http://localhost:8001/products/{product_id}/decrement-stock/ \
  -H "Content-Type: application/json" \
  -d '{"quantity": 2}'
```

Vérifier: stock diminue de 10 à 8.

### Test 4: Créer une commande (flux complet)

```bash
curl -X POST http://localhost:8002/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "client_id": "550e8400-e29b-41d4-a716-446655440001",
    "items_input": [
      {"product_id": "{product_id}", "quantity": 3}
    ]
  }'
```

Vérifier:

- Order créée avec status Pending
- OrderItem a product_name et unit_price
- Product.stock diminue (de 8 à 5)

### Test 5: Erreur stock insuffisant

```bash
curl -X POST http://localhost:8002/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "client_id": "550e8400-e29b-41d4-a716-446655440001",
    "items_input": [
      {"product_id": "{product_id}", "quantity": 1000}
    ]
  }'
```

Attendre: Erreur 400 avec message `Stock insuffisant`

### Test 6: Erreur produit inexistant

```bash
curl -X POST http://localhost:8002/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "client_id": "550e8400-e29b-41d4-a716-446655440001",
    "items_input": [
      {"product_id": "invalid-uuid-123", "quantity": 1}
    ]
  }'
```

Attendre: Erreur 404 NotFound

### Test 7: Confirmer une commande

```bash
curl -X POST http://localhost:8002/orders/{order_id}/confirm/
```

Vérifier: Status = Confirmed

### Test 8: Annuler une commande

Créer une nouvelle commande, puis:

```bash
curl -X POST http://localhost:8002/orders/{order_id}/cancel/
```

Vérifier: Status = Cancelled

---

## ✅ Checklist Finale

**Étape 1 (product_service)**:

- [ ] decrement_stock action ajoutée à ProductViewSet
- [ ] Validations (quantity > 0, stock suffisant)
- [ ] Endpoint répond 200 OK avec produit mis à jour
- [ ] Endpoint répond 400 si stock insuffisant
- [ ] Test 3 passe

**Étape 2 (order_service services.py)**:

- [ ] Fichier créé
- [ ] _build_url() implémentée
- [ ] get_product() implémentée avec timeout
- [ ] check_and_decrement_stock() implémentée avec timeout
- [ ] Exceptions traduites en DRF (NotFound, ValidationError)

**Étape 3 (order_service settings.py)**:

- [ ] CATALOGUE_SERVICE_URL ajoutée
- [ ] Valeur par défaut: <http://localhost:8001>
- [ ] os.environ.get() utilisé

**Étape 4 (order_service requirements.txt)**:

- [ ] requests>=2.31 ajouté
- [ ] pip install -r requirements.txt exécuté

**Étape 5 (order_service serializers.py)**:

- [ ] Fichier créé
- [ ] OrderItemInputSerializer validant product_id et quantity
- [ ] OrderItemSerializer avec ModelSerializer
- [ ] OrderSerializer avec items et items_input
- [ ] create() implémenté avec appels synchrones
- [ ] @transaction.atomic présent

**Étape 6 (order_service views.py + urls.py)**:

- [ ] health() endpoint ajouté
- [ ] OrderViewSet implémenté avec prefetch_related
- [ ] confirm() action ajoutée
- [ ] cancel() action ajoutée
- [ ] Routeur DRF enregistrant OrderViewSet
- [ ] urlpatterns complete

**Tests**:

- [ ] Test 1: Health OK
- [ ] Test 2: Produit créé
- [ ] Test 3: decrement-stock fonctionne
- [ ] Test 4: Commande créée avec synchronisations
- [ ] Test 5: Stock insuffisant → erreur 400
- [ ] Test 6: Produit inexistant → erreur 404
- [ ] Test 7: confirm() change status
- [ ] Test 8: cancel() change status

---

## 📚 Concepts Clés

### Synchrone vs Asynchrone

- **Synchrone** (ce cours): order_service ATTEND la réponse de product_service
- **Asynchrone** (plus tard): order_service publie un événement, donne pas attendre (RabbitMQ)

### Timeout obligatoire

Sans timeout, si product_service ne répond pas, order_service gèle indéfiniment.

### Snapshot de données

product_name et unit_price sont copiés au moment de la création.
Si le prix change après, l'ordre garde l'ancien prix (c'est voulu).

### Transaction atomique

Si quelque chose échoue pendant la création, TOUT est annulé (pas de commande orpheline).

### Responsabilités séparées

- product_service = gestion des produits + stock
- order_service = gestion des commandes + orchestration

---

## 🐛 Erreurs Courantes

❌ **Ne pas faire**: requests directement dans le serializer
✅ **Faire**: couche services.py dédiée

❌ **Ne pas faire**: pas de timeout
✅ **Faire**: `timeout=5` sur chaque requête

❌ **Ne pas faire**: URL hardcodée
✅ **Faire**: `os.environ.get()` + settings.py

❌ **Ne pas faire**: `response.json()["price"]` (risque KeyError)
✅ **Faire**: `response.json().get("price", "0")`

---

## 📖 Ressources

- **Architecture globale**: `docs/MICROSERVICES_SYNC_GUIDE.md`
- **Instructions détaillées** pour chaque étape dans `STEP_X_INSTRUCTIONS.py`
- **Models** déjà implémentés dans `app/models.py`
- **Tests manuels** voir section "Plan de Test" ci-dessus

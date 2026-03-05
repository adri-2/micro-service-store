# Guide Pédagogique : Communication Synchrone entre Microservices Django

## Objectif Global

Créer une **communication HTTP synchrone** entre deux services Django:

- **product_service** (fournisseur): expose les produits
- **order_service** (consommateur): crée des commandes en appelant product_service

**Flux**: Client → order_service → product_service → retour à order_service → Client

---

## Structure Phased

### Phase 1 : API Fournisseur (product_service)

**Fichier à modifier**: `services/product_service/app/views.py`

**Pourquoi?** On ne peut pas appeler product_service si celui-ci n'expose pas d'endpoint de "décrémentation de stock".

**Ce que tu dois ajouter**:

1. Importer les éléments DRF pour actions custom
2. Créer une méthode dans `ProductViewSet` avec le décorateur `@action`
3. Cette méthode doit:
   - Récupérer la `quantity` depuis le body HTTP
   - Valider qu'elle est positive et un entier
   - Vérifier que le stock est suffisant
   - Décrémenter et sauvegarder en base
   - Retourner le produit mis à jour (ou une erreur claire)

**Endpoint généré**: `POST /products/{id}/decrement-stock/`

Instructions détaillées → voir `services/product_service/app/STEP_1_INSTRUCTIONS.py`

---

### Phase 2 : Couche Services (order_service/app/services.py)

**Fichier à créer**: `services/order_service/app/services.py`

**Pourquoi?** Isoler tous les appels HTTP dans une couche dédiée (pas de requests() dans les vues).

**Ce que tu dois implémenter**:

1. Une fonction `_build_url(path)` utilitaire
2. Une fonction `get_product(product_id)` qui:
   - Appelle `GET /products/{product_id}/` sur product_service
   - Retourne le dict du produit
   - Gère les erreurs (404 → NotFound, timeout → ValidationError, etc.)
3. Une fonction `check_and_decrement_stock(product_id, quantity)` qui:
   - Appelle `POST /products/{product_id}/decrement-stock/` avec qty en JSON
   - Retourne la réponse ou lève une exception
   - **Toujours utiliser timeout=5**

Instructions détaillées → voir `services/order_service/app/STEP_2_INSTRUCTIONS.py`

---

### Phase 3 : Configuration (order_service/core/settings.py)

**Fichier à modifier**: `services/order_service/core/settings.py`

**Ce que tu dois ajouter**:

1. Importer `os`
2. Ajouter `CATALOGUE_SERVICE_URL = os.environ.get(...)`
3. Cette URL doit pointer vers product_service:
   - En local: `http://localhost:8001`
   - En Docker: `http://product-service:8000`

Instructions détaillées → voir `services/order_service/core/STEP_3_INSTRUCTIONS.py`

---

### Phase 4 : Dépendances

**Fichier à modifier**: `services/order_service/requirements.txt`

**Ce que tu dois ajouter**:

- `requests>=2.31` (pour les appels HTTP synchrones)

---

### Phase 5 : Sérializers (order_service/app/serializers.py)

**Fichier à créer**: `services/order_service/app/serializers.py`

**Ce que tu dois implémenter**:

1. `OrderItemInputSerializer`: validation des items d'entrée (product_id, quantity)
2. `OrderItemSerializer`: sérialisation complète d'un item (lecture/écriture)
3. `OrderSerializer`: le principal
   - Imbrication complète des items en lecture
   - Accepter `items_input` en écriture
   - Implémenter `create()` qui:
     - appelle `get_product()` pour chaque item
     - appelle `check_and_decrement_stock()` pour bloquer/réserver
     - crée l'objet `OrderItem` avec snapshot (`product_name`, `unit_price`)
   - Envelopper dans une transaction atomique

Instructions détaillées → voir `services/order_service/app/STEP_5_INSTRUCTIONS.py`

---

### Phase 6 : API (order_service/app/views.py + core/urls.py)

**Fichiers à modifier**:

- `services/order_service/app/views.py`
- `services/order_service/core/urls.py`

**Ce que tu dois implémenter**:

1. Endpoint `/health/` (fonction simple JSON)
2. `OrderViewSet` avec ModelViewSet
3. Actions custom:
   - `@action(detail=True, methods=['post'])` pour `confirm(order_id)`
   - `@action(detail=True, methods=['post'])` pour `cancel(order_id)`
4. Routeur DRF enregistrant OrderViewSet

Instructions détaillées → voir `services/order_service/app/STEP_6_INSTRUCTIONS.py`

---

## Ordre d'Implémentation Recommandé

1. **Étape 1** → product_service (fournisseur)
2. **Étape 2** → order_service services.py (couche réseau)
3. **Étape 3** → order_service settings.py (config)
4. **Étape 4** → order_service requirements.txt (dépendances)
5. **Étape 5** → order_service serializers.py (métier + sync calls)
6. **Étape 6** → order_service views.py + urls.py (exposition API)

---

## Plan de Test

Une fois tout implémenté:

### Test 1: Health

```bash
curl http://localhost:8001/health/
curl http://localhost:8002/health/
```

Attendre: `{"status": "ok"}`

### Test 2: Créer un produit

```bash
curl -X POST http://localhost:8001/products/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Laptop","price":999.99,"stock":10,"category":"uuid-category-id"}'
```

Noter le `product_id` retourné.

### Test 3: Tester decrement-stock directement

```bash
curl -X POST http://localhost:8001/products/{product_id}/decrement-stock/ \
  -H "Content-Type: application/json" \
  -d '{"quantity":2}'
```

Vérifier: stock passe de 10 à 8.

### Test 4: Créer une commande (API synchrone complète)

```bash
curl -X POST http://localhost:8002/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id":"uuid-user",
    "client_id":"uuid-client",
    "items_input":[
      {"product_id":"{{product_id}}","quantity":3}
    ]
  }'
```

Vérifier:

- Commande créée
- OrderItem avec snapshot (product_name, unit_price)
- Stock de producto diminue

### Test 5: Cas d'erreur (stock insuffisant)

Créer une commande avec quantity > stock actuel.
Attendre: erreur 400 avec message clair.

### Test 6: Cas d'erreur (produit inexistant)

Créer une commande avec product_id invalide.
Attendre: erreur 404 NotFound.

---

## Checklist Finale

- [ ] Phase 1: decrement_stock implémenté et testé
- [ ] Phase 2: services.py créé et timeout configuré
- [ ] Phase 3: CATALOGUE_SERVICE_URL dans settings.py
- [ ] Phase 4: requests ajouté à requirements.txt
- [ ] Phase 5: serializers.py avec transaction.atomic
- [ ] Phase 6: OrderViewSet + endpoints + urls.py
- [ ] Test 1-6 passent sans erreur
- [ ] Messages d'erreur sont clairs et exploitables

---

## Points d'Architecture à Comprendre

**1. Synchrone vs Asynchrone**

- Ici: synchrone (HTTP, order_service ATTEND la réponse)
- Plus tard: asynchrone avec RabbitMQ (order_service publie un événement, ne attend pas)

**2. Timeout obligatoire**

- Sans `timeout=5`, si product_service ne répond pas, order_service gèle indéfiniment
- Toujours mettre un timeout sur chaque appel réseau

**3. Snapshot de données**

- `product_name` et `unit_price` sont copiés au moment de la création de l'item
- Si le prix change dans product_service, l'ordre garde l'ancien prix (c'est voulu)

**4. Transaction atomique**

- Si OrderItem.create() échoue après la création d'Order, on rollback tout
- Évite des commandes "orphelines" en base de données

**5. Séparation des responsabilités**

- product_service = logique de produit + stock
- order_service = logique de commande + orchestration
- Chacun est indépendant et peut être déployé seul

---

## Erreurs Courantes à Éviter

❌ **Ne pas faire**:

```python
# MAUVAIS: requests directement dans le serializer
def create(self, validated_data):
    response = requests.get("http://product-service:8000/products/")
```

✅ **Faire**:

```python
# BON: couche services.py dédiée
from app.services import get_product
def create(self, validated_data):
    product = get_product(product_id)
```

❌ **Ne pas faire**:

```python
# MAUVAIS: pas de timeout
response = requests.get(url)
```

✅ **Faire**:

```python
# BON: timeout explicite
response = requests.get(url, timeout=5)
```

❌ **Ne pas faire**:

```python
# MAUVAIS: URL hardcodée
url = "http://192.168.1.100:8000/products/"
```

✅ **Faire**:

```python
# BON: URL depuis settings
CATALOGUE_SERVICE_URL = os.environ.get("CATALOGUE_SERVICE_URL")
url = f"{CATALOGUE_SERVICE_URL}/products/"
```

---

## Ressources Complémentaires

- `docs/architecture.md` → vue d'ensemble du projet
- `services/product_service/app/STEP_1_INSTRUCTIONS.py` → instructions product_service
- `services/order_service/app/STEP_2_INSTRUCTIONS.py` → instructions services.py
- `services/order_service/app/STEP_5_INSTRUCTIONS.py` → instructions serializers.py
- `services/order_service/app/STEP_6_INSTRUCTIONS.py` → instructions views.py

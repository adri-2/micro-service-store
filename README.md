# 🏗️ Store Front Microservices Platform

> Une plateforme d'e-commerce basée sur une **architecture microservices moderne** avec **Django & Django REST Framework**, incluant l'authentification JWT, la communication inter-services HTTP, et une gestion complète des commandes et du catalogue produits.

---

## 📋 Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Architecture](#architecture)
- [Services](#services)
- [Installation & Démarrage](#installation--démarrage)
- [Tests & Validation](#tests--validation)
- [Structure du projet](#structure-du-projet)
- [Workflow JWT](#workflow-jwt)
- [Communication inter-services](#communication-inter-services)
- [Documentation](#documentation)

---

## 🎯 Vue d'ensemble

Cette plateforme implémente un **système e-commerce distribué** avec :

- ✅ **Authentification centralisée** : JWT via `account-service`
- ✅ **Protection des endpoints** : Validation stateless des tokens dans chaque service
- ✅ **Communication synchrone** : Requêtes HTTP avec propagation du Bearer token
- ✅ **Isolation des données** : Chaque service avec sa propre base PostgreSQL
- ✅ **Conteneurisation** : Docker Compose pour déploiement local
- ✅ **Cache distribué** : Redis pour session et performance
- ✅ **Gestion des commandes** : Création, confirmation, et traçabilité

**Stack technique** :

- Django 5.2 + Django REST Framework 3.14+
- PostgreSQL 16 (x3 instances)
- Redis 7
- JWT (djangorestframework-simplejwt)
- Docker & Docker Compose

---

## 🏛️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Client / Tests                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     v
        ┌────────────────────────┐
        │   API Gateway          │
        │   (via Docker host)    │
        └────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        v            v            v
   ┌──────────┐ ┌──────────┐ ┌──────────┐
   │ Account  │ │ Product  │ │ Order    │
   │ Service  │ │ Service  │ │ Service  │
   │ :8003    │ │ :8001    │ │ :8002    │
   └────┬─────┘ └────┬─────┘ └────┬─────┘
        │            │            │
        v            v            v
   ┌──────────┐ ┌──────────┐ ┌──────────┐
   │ Account  │ │ Catalogue│ │ Orders   │
   │ PostgreSQL│ │ PostgreSQL│ │ PostgreSQL│
   │ :5433    │ │ :5432    │ │ :5434    │
   └──────────┘ └──────────┘ └──────────┘
        │            │            │
        └────────────┼────────────┘
                     │
                  Redis :6379
```

### Flux complet (exemple)

```
1. Client → POST /auth/login (account-service:8003)
   ├─ Retour: {"access": "eyJ...", "refresh": "...", "user": {...}}
   
2. Client → POST /orders/ (order-service:8002)
   ├─ Header: Authorization: Bearer eyJ...
   ├─ Body: {"user_id": "...", "items_input": [...]}
   │
   ├─→ Order-Service valide JWT (claims, issuer, audience)
   │
   ├─→ Order-Service → GET /products/{id}/ (product-service:8001)
   │   ├─ Propage: Authorization: Bearer eyJ...
   │   ├─ Product-Service valide & retourne {"id": "...", "price": 499.99}
   │   └─ Retour: product data
   │
   ├─→ Order-Service crée OrderItem + met à jour total
   │
   └─ Retour: {"id": "...", "status": "PENDING", "items": [...]}
   
3. Client → POST /orders/{id}/confirm/ (order-service:8002)
   └─ Retour: Order status = CONFIRMED
```

---

## 📦 Services

### 1. **account-service** (Authentification)

| Aspect | Détail |
|--------|--------|
| **Port** | `8003` (local) → `8000` (Docker) |
| **Endpoints** | `/auth/register/`, `/auth/login/`, `/auth/me/`, `/auth/refresh/` |
| **DB** | PostgreSQL `:5433` |
| **Rôle** | Émetteur de tokens JWT |
| **Auth Config** | `JWTAuthentication` |

**Endpoints** :

```http
POST   /auth/register/     # Créer un compte (AllowAny)
POST   /auth/login/        # Obtenir tokens (AllowAny)
GET    /auth/me/           # Profil utilisateur (IsAuthenticated)
POST   /auth/verify/       # Vérifier token (AllowAny)
POST   /auth/refresh/      # Rafraîchir access token (AllowAny)
GET    /health/            # Health check (AllowAny)
```

---

### 2. **product-service** (Catalogue)

| Aspect | Détail |
|--------|--------|
| **Port** | `8001` (local) → `8000` (Docker) |
| **Endpoints** | `/categories/`, `/suppliers/`, `/products/` |
| **DB** | PostgreSQL `:5432` |
| **Rôle** | Gestion des produits, catégories, fournisseurs |
| **Auth Config** | `JWTStatelessUserAuthentication` (valide tokens account-service) |

**Endpoints** :

```http
GET    /categories/                    # Lister catégories (IsAuthenticated)
POST   /categories/                    # Créer catégorie (IsAuthenticated)
GET    /suppliers/                     # Lister fournisseurs (IsAuthenticated)
POST   /suppliers/                     # Créer fournisseur (IsAuthenticated)
GET    /products/                      # Lister produits (IsAuthenticated)
POST   /products/                      # Créer produit (IsAuthenticated)
GET    /products/{id}/                 # Détail produit (IsAuthenticated)
POST   /products/{id}/decrement-stock/ # Décrémenter stock (IsAuthenticated)
GET    /health/                        # Health check (AllowAny)
```

---

### 3. **order-service** (Commandes)

| Aspect | Détail |
|--------|--------|
| **Port** | `8002` (local) → `8000` (Docker) |
| **Endpoints** | `/orders/` |
| **DB** | PostgreSQL `:5434` |
| **Rôle** | Gestion des commandes, appels inter-services |
| **Auth Config** | `JWTStatelessUserAuthentication` (valide tokens account-service) |

**Endpoints** :

```http
GET    /orders/                    # Lister commandes (IsAuthenticated)
POST   /orders/                    # Créer commande (IsAuthenticated)
GET    /orders/{id}/               # Détail commande (IsAuthenticated)
POST   /orders/{id}/confirm/       # Confirmer commande (IsAuthenticated)
GET    /health/                    # Health check (AllowAny)
```

**Logique création** :

- Validation JWT entrant
- Extraction du token depuis Authorization header
- Appel → `product-service` pour valider chaque produit
- Propagation du token dans la requête en aval
- Création d'OrderItems avec `unit_price` du produit

---

## 🚀 Installation & Démarrage

### Prérequis

- **Docker & Docker Compose** (ou Python 3.11+, PostgreSQL 16, Redis 7 local)
- **Git**
- Optionnel: **REST Client** (VS Code extension) pour tester

### Option 1 : Docker Compose (Recommandé)

#### Démarrer tous les services

```bash
# Accession au répertoire project
cd "c:\Users\wwwad\PycharmProjects\PROJECT-PERSO\django sans bd"

# Démarrer account-service
cd services/account_service
docker-compose -f docker-compose.account.yml up -d

# Démarrer product-service (dans un nouveau terminal)
cd services/product_service
docker-compose -f docker-compose.catalogue.yml up -d

# Démarrer order-service (dans un nouveau terminal)
cd services/order_service
docker-compose -f docker-compose.orders.yml up -d

# Optionnel: message-service
cd services/message_service
docker-compose -f docker-compose.message.yml up -d
```

#### Vérifier la santé

```bash
curl http://localhost:8003/health/   # account-service
curl http://localhost:8001/health/   # product-service
curl http://localhost:8002/health/   # order-service
```

#### Arrêter tous les services

```bash
# Dans chaque dossier service/
docker-compose -f docker-compose.*.yml down -v
```

---

### Option 2 : Développement local (Sans Docker)

#### Configuration

```bash
# 1. Créer un venv pour chaque service
cd services/account_service
python -m venv venv
venv\Scripts\activate

# 2. Installer dépendances
pip install -r requirements.txt

# 3. Migrations DB
python manage.py migrate

# 4. Démarrer le serveur
python manage.py runserver 8000
```

⚠️ **En local, adapter** :

- `DB_HOST` : remplacer `service-name` par `localhost`
- `CATALOGUE_SERVICE_URL` : remplacer `http://catalogue-service:8000` par `http://localhost:8001`

---

## 🧪 Tests & Validation

### Via REST Client (VS Code)

Ouvre le fichier [tests/api.http](tests/api.http) et exécute les requêtes dans cet ordre :

```http
### 1. Register (copier/coller)
POST http://localhost:8003/auth/register/ HTTP/1.1
Content-Type: application/json

{
  "email": "admin@gmail.com",
  "username": "admin",
  "password": "admin1234"
}

### 2. Login (récupère token automatiquement avec @name login)
# @name login
POST http://localhost:8003/auth/login/ HTTP/1.1
Content-Type: application/json

{
  "email": "admin@gmail.com",
  "password": "admin1234"
}

### 3. Verify (utilise automatiquement le token capturé)
GET http://localhost:8003/auth/me/ HTTP/1.1
Authorization: Bearer {{login.response.body.$.access}}

### 4. List Products (avec token)
GET http://localhost:8001/products/ HTTP/1.1
Authorization: Bearer {{login.response.body.$.access}}

### 5. Create Order (avec propagation automatique du token)
POST http://localhost:8002/orders/ HTTP/1.1
Content-Type: application/json
Authorization: Bearer {{login.response.body.$.access}}

{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "client_id": "550e8400-e29b-41d4-a716-446655440001",
  "items_input": [
    {
      "product_id": "550e8400-e29b-41d4-a716-446655440002",
      "quantity": 2
    }
  ]
}
```

### Via cURL

```bash
# 1. Get token
TOKEN=$(curl -s -X POST http://localhost:8003/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@gmail.com","password":"admin1234"}' \
  | jq -r '.access')

# 2. List products
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8001/products/

# 3. Create order
curl -X POST http://localhost:8002/orders/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "client_id": "550e8400-e29b-41d4-a716-446655440001",
    "items_input": [{"product_id": "550e8400-e29b-41d4-a716-446655440002", "quantity": 2}]
  }'
```

---

## 📂 Structure du projet

```
django-sans-bd/
│
├── README.md                          ← 🔴 (Vous êtes ici)
│
├── docs/                              # Documentation pédagogique
│   ├── architecture.md                # Vue globale
│   ├── QUICK_START.md                 # Pour débutants
│   ├── BEGINNER_MICROSERVICES_GUIDE.md
│   ├── MICROSERVICES_SYNC_GUIDE.md
│   ├── project-audit.md
│   ├── next-steps.md
│   └── ...
│
├── infrastructure/                    # Configs infra (gateway, messaging, etc.)
│   ├── gateway/
│   │   └── docker-compose.yaml
│   └── messaging/
│       └── docker-compose.yml
│
├── services/                          # 🔥 Microservices Django
│   │
│   ├── account_service/               # Authentification & JWT
│   │   ├── Dockerfile
│   │   ├── docker-compose.account.yml
│   │   ├── requirements.txt
│   │   ├── manage.py
│   │   ├── core/                      # Django config
│   │   │   ├── settings.py            # JWT, DB, REST Framework config
│   │   │   ├── urls.py
│   │   │   ├── wsgi.py
│   │   │   └── asgi.py
│   │   └── app/                       # Application Django
│   │       ├── models.py              # User model
│   │       ├── views.py               # RegisterView, LoginView, MeView, RefreshView
│   │       ├── serializers.py
│   │       ├── tests.py
│   │       └── migrations/
│   │
│   ├── product_service/               # Catalogue produits
│   │   ├── Dockerfile
│   │   ├── docker-compose.catalogue.yml
│   │   ├── requirements.txt
│   │   ├── manage.py
│   │   ├── core/
│   │   │   ├── settings.py            # JWTStatelessUserAuthentication
│   │   │   ├── urls.py
│   │   │   └── ...
│   │   └── app/
│   │       ├── models.py              # Category, Supplier, Product
│   │       ├── views.py               # CategoryViewSet, ProductViewSet
│   │       ├── serializers.py
│   │       ├── services.py
│   │       └── migrations/
│   │
│   ├── order_service/                 # Gestion commandes
│   │   ├── Dockerfile
│   │   ├── docker-compose.orders.yml
│   │   ├── requirements.txt
│   │   ├── manage.py
│   │   ├── core/
│   │   │   ├── settings.py            # JWT auth + CATALOGUE_SERVICE_URL
│   │   │   ├── urls.py
│   │   │   └── ...
│   │   └── app/
│   │       ├── models.py              # Order, OrderItem
│   │       ├── views.py               # OrderViewSet
│   │       ├── serializers.py         # Intègre get_product()
│   │       ├── services.py            # ⭐ Communication inter-services
│   │       └── migrations/
│   │
│   └── message_service/               # Service de messaging (message/email)
│       ├── Dockerfile
│       ├── requirements.txt
│       └── ...
│
├── shared/                            # Code partagé entre services
│   ├── clients/
│   │   └── service_client.py          # Base HTTP client
│   ├── config/
│   │   └── settings_base.py           # Configs communes
│   └── utils/
│       └── exceptions.py              # Exceptions métier
│
├── tests/                             # Tests e2e
│   ├── api.http                       # ⭐ REST Client pour tester
│   └── ...
│
└── .git/                              # Git history
```

---

## 🔐 Workflow JWT

### Configuration

Tous les services partagent la **même clé JWT** pour validation :

```python
# account_service/core/settings.py (ÉMETTEUR)
SIMPLE_JWT = {
    "SIGNING_KEY": os.environ.get("JWT_SIGNING_KEY", SECRET_KEY),  # Signe ici
    "ISSUER": "account-service",
    "AUDIENCE": "store-front-services",
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=300),
}

# product_service/core/settings.py (VALIDATEUR)
SIMPLE_JWT = {
    "SIGNING_KEY": os.environ.get("JWT_SIGNING_KEY", SECRET_KEY),  # Même clé
    "VERIFYING_KEY": os.environ.get("JWT_VERIFYING_KEY", ""),      # Optionnel
    "ISSUER": "account-service",  # Même émetteur attendu
    "AUDIENCE": "store-front-services",
}

# order_service/core/settings.py (VALIDATEUR)
# Même config que product_service
```

### Flux complet

```
1️⃣ Login (account-service)
   └─ Émet JWT:
      {
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "admin@gmail.com",
        "iat": 1712138400,
        "exp": 1712138400 + 300*60,
        "iss": "account-service",
        "aud": "store-front-services"
      }

2️⃣ Client envoie Bearer token
   Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

3️⃣ Product-Service valide
   ✓ Signature valide (même SECRET_KEY)
   ✓ Pas expiré (exp > maintenant)
   ✓ Issuer = "account-service"
   ✓ Audience = "store-front-services"
   → Crée AnonymousUser avec claims en contexte

4️⃣ Order-Service fait appel à Product-Service
   ├─ Récupère Authorization header de la requête entrante
   ├─ Propage dans la requête aval
   └─ Product-Service valide à nouveau
```

### Clés de configuration

| Variable | Défaut | Rôle |
|----------|--------|------|
| `JWT_SIGNING_KEY` | `SECRET_KEY` | Signe les tokens (account-service) |
| `JWT_VERIFYING_KEY` | `""` | Vérifie les tokens (optionnel, sinon = SIGNING_KEY) |
| `JWT_ALGORITHM` | `HS256` | Algorithme (HMAC-SHA256) |
| `JWT_ISSUER` | `account-service` | Émetteur attendu |
| `JWT_AUDIENCE` | `store-front-services` | Public cible |
| `JWT_ACCESS_MINUTES` | `300` | Durée access token (5 heures) |
| `JWT_REFRESH_DAYS` | `7` | Durée refresh token |

---

## 🔗 Communication inter-services

### Pattern : Order → Product

**ordre-service/app/services.py** regroupe tous les appels HTTP :

```python
import requests
from django.conf import settings
from rest_framework.exceptions import ValidationError, NotFound

def _build_url(path: str) -> str:
    """Construit l'URL vers product-service."""
    base = settings.CATALOGUE_SERVICE_URL.rstrip("/")
    clean_path = path.lstrip("/")
    return f"{base}/{clean_path}"

def _auth_headers(access_token: str | None) -> dict:
    """Propage le Bearer token dans les en-têtes."""
    if not access_token:
        return {}
    token = access_token.strip()
    if token.lower().startswith("bearer "):
        return {"Authorization": token}
    return {"Authorization": f"Bearer {token}"}

def get_product(product_id: str, access_token: str | None = None) -> dict:
    """Récupère un produit depuis product-service."""
    url = _build_url(f"products/{product_id}/")
    headers = _auth_headers(access_token)
    try:
        response = requests.get(url, timeout=5, headers=headers)
    except requests.exceptions.ConnectionError:
        raise ValidationError("Catalogue inaccessible")
    except requests.exceptions.Timeout:
        raise ValidationError("Catalogue timeout")
    
    if response.status_code == 404:
        raise NotFound("Produit non trouvé")
    if response.status_code != 200:
        raise ValidationError("Erreur catalogu")
    
    return response.json()
```

**order-service/app/serializers.py** utilise la couche services :

```python
class OrderSerializer(serializers.ModelSerializer):
    items_input = OrderItemInputSerializer(many=True, write_only=True)
    
    def create(self, validated_data):
        items_data = validated_data.pop("items_input", [])
        request = self.context.get("request")
        access_token = request.META.get("HTTP_AUTHORIZATION") if request else None
        
        order = Order.objects.create(**validated_data)
        
        for item in items_data:
            # Appel à product-service avec propagation du token
            product = get_product(str(item["product_id"]), access_token=access_token)
            
            OrderItem.objects.create(
                order=order,
                product_id=item["product_id"],
                product_name=product["name"],
                unit_price=Decimal(str(product["price"])),
                quantity=item["quantity"],
                subtotal=Decimal(str(product["price"])) * item["quantity"]
            )
        
        order.update_total()
        return order
```

### Erreurs courantes

| Erreur | Cause | Solution |
|--------|-------|----------|
| `401 Unauthorized` | Token invalide/expiré | Vérifier token, rafraîchir si expiré |
| `403 Forbidden` | Token valide mais permission refusée | Vérifier IsAuthenticated permission |
| `503 Service Unavailable` | Service aval down | Vérifier CATALOGUE_SERVICE_URL |
| `timeout` | Requête trop lente | Augmenter timeout (actuellement 5s) |
| `JSON parse error` | Extra data dans HTTP body | Vérifier syntax REST Client |

---

## 📖 Documentation

### Fichiers clés

| Fichier | Contenu |
|---------|---------|
| [docs/QUICK_START.md](docs/QUICK_START.md) | Guide pour débutants |
| [docs/architecture.md](docs/architecture.md) | Vue globale architecture |
| [docs/BEGINNER_MICROSERVICES_GUIDE.md](docs/BEGINNER_MICROSERVICES_GUIDE.md) | Concepts fondamentaux |
| [docs/MICROSERVICES_SYNC_GUIDE.md](docs/MICROSERVICES_SYNC_GUIDE.md) | Communication HTTP synchrone |
| [docs/BEGINNER_EXERCISES.md](docs/BEGINNER_EXERCISES.md) | Exercices pratiques |
| [tests/api.http](tests/api.http) | Tests e2e (REST Client) |

### Instructions step-by-step

Chaque service contient des fichiers `STEP_X_INSTRUCTIONS.py` :

```
services/product_service/app/STEP_1_INSTRUCTIONS.py     # Implémenter decrement-stock
services/order_service/app/STEP_2_INSTRUCTIONS.py       # Implémenter get_product()
services/order_service/core/STEP_3_INSTRUCTIONS.py      # Configurer CATALOGUE_SERVICE_URL
...
```

---

## 🛠️ Troubleshooting

### Les services ne communiquent pas

```bash
# 1. Vérifier que les services tournent
docker ps | grep -E "(account|catalogue|orders)"-service

# 2. Tester la connectivité directe
curl http://localhost:8001/health/

# 3. Vérifier CATALOGUE_SERVICE_URL
docker exec orders-service env | grep CATALOGUE_SERVICE_URL
```

### Token invalide / expiré

```bash
# 1. Vérifier l'expiration
curl -X POST http://localhost:8003/auth/verify/ \
  -H "Content-Type: application/json" \
  -d '{"token": "eyJ..."}'

# 2. Rafraîchir le token
curl -X POST http://localhost:8003/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "..."}'
```

### Base de données locked/corrupted

```bash
# Réinitialiser une DB
docker-compose -f services/order_service/docker-compose.orders.yml down -v
docker-compose -f services/order_service/docker-compose.orders.yml up -d
```

---

## 🎓 Concepts clés

### Microservices vs Monolithe

**Monolithe** : 1 grande app, 1 DB → difficile à scaler
**Microservices** : N petits services, N BDs → chacun scal indépendamment

### Stateless Authentication (JWT)

❌ Store session en DB (stateful)
✅ Token auto-contenu (stateless) → chaque service peut valider sans appel DB

### Propagation de token

Quand Service A appelle Service B :

```
Client → Service A (auth JWT)
         ↓ (relaie Authorization)
         → Service B (valide JWT)
```

**Pourquoi** ? Chaque service respecte l'identité utilisateur original

---

## 📝 Prochaines étapes

- [ ] Ajouter RabbitMQ pour communication asynchrone
- [ ] Impliciter les migrations en CI/CD
- [ ] Ajouter monitoring (Prometheus + Grafana)
- [ ] Authentification OAuth2 externe
- [ ] Rate limiting & throttling
- [ ] Tests unitaires complets
- [ ] API Gateway (Traefik)

---

## 📄 License

MIT (Projet personnel)

---

## 👤 Auteur : [SANI ADRIEN](https://github.com/adri-2/)

Créé comme projet d'apprentissage microservices Django.

---

**Questions ou problèmes ?**
→ Consultez [docs/QUICK_START.md](docs/QUICK_START.md) ou [tests/api.http](tests/api.http)

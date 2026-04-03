# Audit de l'architecture microservices

Date : 2026-03-05

---

## 1. Vue d'ensemble du projet

Le projet est composé de **3 services Django** + **3 services d'infrastructure** :

| Service          | Dossier            | Port hôte | Base de données |
|------------------|--------------------|-----------|-----------------|
| Catalogue        | `product_service/` | 8001      | PostgreSQL 5432 |
| Orders           | `order_service/`   | 8002      | PostgreSQL 5434 |
| Account          | `account_service/` | 8003      | PostgreSQL 5433 |
| Traefik          | `gateway-service/` | 80/443    | —               |
| Consul           | `registry_service/`| 8500      | —               |
| RabbitMQ         | `rabbitmq_service/`| 15672     | —               |

Réseau Docker partagé : `store_front_network` (réseau externe à créer manuellement).

---

## 2. Ce qui est correct

### Architecture

- **UUIDs comme clés primaires** sur tous les modèles (`id = models.UUIDField(...)`).
  Cela est indispensable pour des services qui ne partagent pas de base de données.

- **Absence de ForeignKey cross-service** dans `OrderItem`.
  Le modèle stocke `product_id` (UUID), `product_name` et `unit_price` en snapshot.
  C'est le pattern correct pour l'isolation des services.

- **Références par UUID** dans `Order` : `user_id` et `client_id` sont des UUIDs simples,
  pas des ForeignKey vers d'autres services.

- **Base de données séparée** par service (PostgreSQL dédié pour chacun).
  Chaque service a ses propres credentials et son propre volume Docker.

- **Réseau Docker partagé** (`store_front_network`) pour permettre la communication
  inter-services sans exposer les ports inutilement.

- **Traefik configuré** comme reverse proxy avec découverte Docker automatique
  et intégration Consul.

- **Consul configuré** pour le registre de services avec health check.

- **pika installé** dans tous les requirements (client RabbitMQ Python).

- **Endpoint `/health/`** présent dans `product_service` et enregistré dans Consul.

- **`select_related` et `prefetch_related`** utilisés dans `ProductViewSet`
  pour optimiser les requêtes N+1.

- **`BaseModel` abstrait** avec `created_at` / `updated_at` dans les trois services.

- **Validation dans les modèles** : `clean()` présent sur `Product`, `Client`, `OrderItem`.

- **Calcul automatique du sous-total** dans `OrderItem.save()` et mise à jour
  du total de la commande via `order.update_total()`.

- **`python-decouple` installé** dans tous les requirements (même si pas encore utilisé).

### Catalogue Service (product_service)

- Modèles `Category`, `Supplier`, `Product` bien séparés et cohérents.
- Serializers avec lecture imbriquée (nested read) et écriture par ID (write_only).
- ViewSet avec `ModelViewSet` pour un CRUD complet.
- Routeur DRF configuré dans `urls.py`.

### Order Service (order_service)

- `OrderItem` ne connaît pas `Product` : pas de ForeignKey cross-service. ✓
- Statuts de commande définis avec `TextChoices`.

---

## 3. Problèmes détectés

### CRITIQUE — Base de données

**Problème :**
Les trois `settings.py` utilisent SQLite comme base de données :

```python
# Actuel dans les 3 services
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
```

Pourtant, les fichiers `docker-compose` injectent des variables d'environnement PostgreSQL
(`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`) qui ne sont jamais lues.

**Impact :** Les conteneurs utilisent SQLite (fichier local dans le conteneur),
pas PostgreSQL. Les données sont perdues à chaque redémarrage.

**Fichiers concernés :**

- `product_service/core/settings.py`
- `order_service/core/settings.py`
- `account_service/core/settings.py`

---

### CRITIQUE — Secret key identique dans tous les services

**Problème :**

```python
SECRET_KEY = "django-insecure-ga(rs0r%)ph$xqeu*u()psjt7nf6o-cu$jn&4ep7^%erk_l**6"
```

La même clé est présente dans les 3 services. Elle est aussi préfixée `django-insecure-`
ce qui indique qu'elle n'a jamais été changée depuis la génération automatique.

**Impact :** Compromission d'un service = compromission de tous les services.
De plus, la clé est committée dans le dépôt git.

---

### IMPORTANT — Variables d'environnement non lues dans settings.py

**Problème :**
`python-decouple` est installé mais n'est pas utilisé. Les fichiers `settings.py`
ignorent les variables d'environnement injectées par Docker.

**Fichiers concernés :** les 3 `settings.py`

---

### IMPORTANT — Serveur de développement en production

**Problème :**

```yaml
command: python manage.py runserver 0.0.0.0:8000
```

`runserver` est le serveur de développement Django. Il n'est pas conçu pour la production.

Gunicorn est installé dans les requirements mais commenté :

```
# gunicorn>=21.2
```

**Impact :** Pas de concurrence, pas de gestion des erreurs robuste, pas de performance.

---

### IMPORTANT — Aucune API dans account_service et order_service

**Problème :**
Les deux services ont des `views.py` vides et des `urlpatterns = []`.
Les modèles sont définis mais aucun endpoint REST n'existe.

**Impact :** Ces services ne sont pas utilisables.

**Fichiers concernés :**

- `account_service/app/views.py`
- `account_service/core/urls.py`
- `order_service/app/views.py`
- `order_service/core/urls.py`

---

### IMPORTANT — Pas de sérialiseurs dans account_service et order_service

**Problème :**
Il n'y a pas de fichier `serializers.py` dans `account_service/app/`
ni dans `order_service/app/`.

Sans sérialiseurs, il n'est pas possible de construire des APIs REST.

---

### IMPORTANT — Incohérence de nomenclature

**Problème :**
Le dossier s'appelle `account_service` mais l'architecture cible parle de "Customer Service".
Le dossier s'appelle `product_service` mais le conteneur s'appelle `catalogue-service`.

Cela crée une confusion entre le nom du dossier Python, le nom du conteneur Docker,
le nom dans Consul, et le nom dans les labels Traefik.

**Recommandation :** Choisir une convention et la tenir partout.
Exemple : `catalogue-service` partout (dossier, conteneur, Consul, Traefik).

---

### IMPORTANT — Seul le catalogue-service est enregistré dans Traefik et Consul

**Problème :**

- `order_service` et `account_service` n'ont pas de labels Traefik dans leurs `docker-compose`.
- Il n'y a qu'une seule définition Consul (`registry_service/config/django-service.json`)
  pour `catalogue-service`.
- Il n'y a pas de endpoint `/health/` dans `account_service` ni `order_service`.

**Impact :** `order_service` et `account_service` ne sont pas accessibles via Traefik
et ne sont pas monitorés par Consul.

---

### IMPORTANT — Versions Django incohérentes

**Problème :**

```
# product_service/requirements.txt
Django>=5.2

# account_service/requirements.txt et order_service/requirements.txt
Django>=4.2,<5.0
```

Un service utilise Django 5.2, les deux autres sont bloqués sur Django 4.x.
Cette incohérence complique la maintenance.

---

### MODÉRÉ — ALLOWED_HOSTS incohérent

**Problème :**

```python
# account_service et order_service
ALLOWED_HOSTS = []   # aucun hôte autorisé (cassé en production)

# product_service
ALLOWED_HOSTS = ["*"]  # tous les hôtes autorisés (non sécurisé)
```

`ALLOWED_HOSTS = []` avec `DEBUG = False` bloquera toutes les requêtes.
`ALLOWED_HOSTS = ["*"]` est un risque de sécurité.

---

### MODÉRÉ — Pas de fichiers .env, secrets exposés

**Problème :**
Les mots de passe de base de données et les credentials RabbitMQ sont en clair
dans les fichiers `docker-compose` :

```yaml
POSTGRES_PASSWORD: account_pass
RABBITMQ_DEFAULT_PASS: admin
```

Ces fichiers sont dans le dépôt git.

---

### MODÉRÉ — account_service garde le stack Django admin complet

**Problème :**
Pour un service API-only, `account_service` garde inutilement :

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    ...
]
```

Les middlewares `SessionMiddleware`, `MessageMiddleware` n'ont pas de sens
pour un service REST sans interface HTML.

---

### MODÉRÉ — Communication inter-services non implémentée

**Problème :**
`order_service` stocke `product_id` mais n'appelle jamais le catalogue-service pour :

- vérifier que le produit existe
- récupérer le prix
- décrémenter le stock

Il n'y a aucun fichier `services.py` ou client HTTP dans `order_service`.

---

### MODÉRÉ — RabbitMQ configuré mais non utilisé dans le code

**Problème :**
`pika` est dans les requirements et l'URL RabbitMQ est dans les variables d'environnement
des compose, mais il n'y a aucun publisher ni consumer dans le code.

---

### MINEUR — RABBITMQ_URL dans les compose mais pas dans settings.py

**Problème :**
`order_service` et `catalogue_service` reçoivent `RABBITMQ_URL` mais aucun `settings.py`
ne définit cette variable.

---

### MINEUR — BaseModel dupliqué dans les 3 services

**Contexte :**
En microservices, dupliquer `BaseModel` est **acceptable** car les services sont indépendants.
Mais il faut en être conscient : toute modification doit être faite dans les 3 services.

---

### MINEUR — Dockerfile sans EXPOSE ni ENTRYPOINT

**Problème :**

```dockerfile
FROM python:3.11-slim
ENV PYTHONUNBUFFERED 1
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt
COPY . /app
```

Pas de `EXPOSE 8000`, pas d'`ENTRYPOINT` ni de `CMD`. Le lancement est délégué
entièrement au `command:` du docker-compose.

---

## 4. Résumé des problèmes par priorité

| Priorité | Problème |
|----------|----------|
| CRITIQUE | SQLite au lieu de PostgreSQL dans tous les settings.py |
| CRITIQUE | Secret key identique et hardcodée dans tous les services |
| IMPORTANT | Variables d'environnement non lues (postgres, secret key) |
| IMPORTANT | Serveur de développement (`runserver`) utilisé partout |
| IMPORTANT | Aucune API (views + urls) dans account_service et order_service |
| IMPORTANT | Pas de serializers dans account_service et order_service |
| IMPORTANT | Incohérence de nomenclature (account vs customer, product vs catalogue) |
| IMPORTANT | order_service et account_service absents de Traefik et Consul |
| IMPORTANT | Versions Django incohérentes (4.x vs 5.x) |
| MODÉRÉ | ALLOWED_HOSTS mal configuré |
| MODÉRÉ | Secrets en clair dans les docker-compose |
| MODÉRÉ | Communication inter-services non implémentée |
| MODÉRÉ | RabbitMQ configuré mais non utilisé dans le code |
| MINEUR | RABBITMQ_URL non définie dans settings.py |
| MINEUR | BaseModel dupliqué (acceptable en microservices) |
| MINEUR | Dockerfile sans EXPOSE ni CMD |

# Plan d'amélioration — Prochaines étapes

Date : 2026-03-05

---

## Ordre recommandé

Les étapes sont organisées du plus bloquant au plus avancé.
Ne pas sauter une étape : chaque étape repose sur la précédente.

---

## Étape 1 — Corriger la configuration des settings.py (CRITIQUE)

**Pourquoi en premier :**
Actuellement les services utilisent SQLite. Sans PostgreSQL,
aucune donnée n'est persistée correctement.

**À faire dans chaque `settings.py` :**

1. Lire les variables d'environnement avec `python-decouple` :
   - `SECRET_KEY`
   - `DEBUG`
   - `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
   - `ALLOWED_HOSTS`

2. Remplacer le bloc DATABASES SQLite par un bloc PostgreSQL
   qui lit ces variables d'environnement.

3. Générer des secret keys différentes pour chaque service.

4. Corriger `ALLOWED_HOSTS` pour chaque service
   (ex. `catalogue.local` pour le catalogue-service).

**Fichiers à modifier :**

- `product_service/core/settings.py`
- `order_service/core/settings.py`
- `account_service/core/settings.py`

---

## Étape 2 — Créer les fichiers .env (CRITIQUE)

**Pourquoi :**
Les secrets ne doivent pas être hardcodés dans les `docker-compose`.

**À faire :**

1. Créer un fichier `.env` dans chaque dossier de service :
   - `product_service/.env`
   - `order_service/.env`
   - `account_service/.env`

2. Ajouter `.env` dans `.gitignore` à la racine du projet.

3. Créer des fichiers `.env.example` (sans valeurs réelles)
   pour documenter les variables nécessaires.

4. Modifier les `docker-compose` pour référencer les `.env`
   avec `env_file:` au lieu de `environment:` inline.

**Variables à définir (exemple pour catalogue-service) :**

```
SECRET_KEY=...
DEBUG=True
ALLOWED_HOSTS=catalogue.local,localhost
DB_NAME=catalogue_db
DB_USER=catalogue_user
DB_PASSWORD=...
DB_HOST=catalogue-db
DB_PORT=5432
RABBITMQ_URL=amqp://admin:admin@rabbitmq:5672/
```

---

## Étape 3 — Aligner les versions Django

**Pourquoi :**
`product_service` est sur Django 5.2, les deux autres sur Django 4.x.
Choisir une version et l'appliquer partout.

**Recommandation :** Monter tout le monde à Django 5.x (la plus récente stable).

**Fichiers à modifier :**

- `account_service/requirements.txt`
- `order_service/requirements.txt`

---

## Étape 4 — Nettoyer les settings.py des services API-only

**Pourquoi :**
`order_service` et `account_service` n'ont pas d'interface HTML.
Garder le stack admin/sessions/messages alourdit inutilement le service.

**À faire dans `order_service/core/settings.py` et `account_service/core/settings.py` :**

Garder uniquement :

```python
INSTALLED_APPS = [
    "django.contrib.contenttypes",  # nécessaire pour les ForeignKey
    "django.contrib.staticfiles",
    "rest_framework",
    "app",
]
```

Middleware minimal :

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]
```

**Note pour `account_service` :**
`django.contrib.auth` est nécessaire si vous utilisez `AbstractBaseUser`.
`django.contrib.admin` ne l'est pas pour un service REST.

---

## Étape 5 — Ajouter les serializers manquants

**Pourquoi :**
Sans serializers, impossible de construire les endpoints REST.

**À créer :**

`account_service/app/serializers.py` — pour `User` et `Client`

`order_service/app/serializers.py` — pour `Order` et `OrderItem`

**À faire :**
Créer ces deux fichiers en s'inspirant du modèle existant dans
`product_service/app/serializers.py`.

---

## Étape 6 — Ajouter les views et les URLs manquantes

**Pourquoi :**
Les endpoints REST existent deja, mais il faut maintenant les fiabiliser pour l hebergement.

**À faire :**

Pour chaque service :

1. Verifier que les `ViewSet` et les permissions sont coherents avec le role du service.
2. Verifier les routeurs DRF et eviter les redirects inutiles (preflight CORS).
3. Conserver un endpoint `/health/` exploitable par les healthchecks Docker.

**Fichiers à modifier :**

- `account_service/app/views.py`
- `account_service/core/urls.py`
- `order_service/app/views.py`
- `order_service/core/urls.py`

---

## Étape 7 — Finaliser le routage Traefik et la readiness

**Pourquoi :**
La stack globale expose deja les services via Traefik, mais la readiness applicative
et la robustesse de demarrage restent a renforcer.

**À faire :**

1. Verifier les labels Traefik dans le compose global (routers + services + network).

   ```yaml
   labels:
     - "traefik.enable=true"
     - "traefik.http.routers.account-service.rule=Host(`account.local`)"
     - "traefik.http.services.account-service.loadbalancer.server.port=8000"
     - "traefik.docker.network=store_front_network"
     - "traefik.http.routers.account-service.entrypoints=web"
   ```

2. Ajouter des `healthcheck` sur account-service, catalogue-service et orders-service.
3. Passer les `depends_on` critiques en forme longue avec `condition: service_healthy`.
4. Ajouter des retries/timeouts cote appels inter-services.

---

## Étape 8 — Implémenter la communication inter-services

**Pourquoi :**
`order_service` doit appeler `catalogue-service` pour valider le stock
et récupérer les informations produit au moment de la commande.

**À faire :**

1. Créer `order_service/app/services.py` avec un client HTTP
   qui appelle `catalogue-service` via son nom DNS Docker
   (ex. `http://catalogue-service:8000/products/{id}/`).

2. Ajouter dans `product_service` un endpoint dédié pour la décrémentation du stock
   (ex. `POST /products/{id}/decrement-stock/`).

3. Câbler `services.py` dans la vue de création de commande.

**Outils recommandés :** `httpx` (asynchrone, recommandé) ou `requests` (synchrone).

---

## Étape 9 — Connecter RabbitMQ (communication asynchrone)

**Pourquoi :**
Certains événements (commande confirmée, stock épuisé) n'ont pas besoin
d'une réponse synchrone. RabbitMQ est déjà configuré dans l'infrastructure.

**À faire :**

1. Définir les événements à publier :
   - `order.created` (publié par order_service)
   - `stock.decremented` (publié par catalogue-service)

2. Créer les publishers et consumers dans chaque service concerné.

3. Ajouter `RABBITMQ_URL` dans les `settings.py` en lisant la variable d'environnement.

---

## Étape 10 — Remplacer runserver par Gunicorn

**Pourquoi :**
`runserver` est le serveur de développement Django. Il ne doit pas tourner
en environnement Docker de type production ou staging.

**À faire dans chaque `docker-compose` :**

```yaml
command: >
  sh -c "python manage.py migrate &&
         gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 2"
```

**Et dans chaque `requirements.txt` :**
Décommenter la ligne `# gunicorn>=21.2`.

---

## Étape 11 — Améliorer les Dockerfiles

**À faire :**
Ajouter dans chaque `Dockerfile` :

```dockerfile
EXPOSE 8000
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]
```

---

## Récapitulatif des priorités

| # | Étape | Priorité |
|---|-------|----------|
| 1 | Corriger settings.py (PostgreSQL + env vars) | CRITIQUE |
| 2 | Créer les fichiers .env | CRITIQUE |
| 3 | Aligner les versions Django | IMPORTANT |
| 4 | Nettoyer settings.py des services API-only | IMPORTANT |
| 5 | Ajouter les serializers | IMPORTANT |
| 6 | Ajouter views et URLs | IMPORTANT |
| 7 | Routage Traefik + readiness Docker | IMPORTANT |
| 8 | Communication inter-services (HTTP sync) | IMPORTANT |
| 9 | Connecter RabbitMQ | MODÉRÉ |
| 10 | Remplacer runserver par Gunicorn | MODÉRÉ |
| 11 | Améliorer les Dockerfiles | MINEUR |

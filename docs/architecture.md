# Architecture actuelle du projet

Ce document decrit l etat reel de la plateforme dans le repository.

## 1) Vue globale

```text
Client
  |
  v
Traefik (80/443)
  |
  +--> account-service (Django, 8003->8000)
  +--> catalogue-service (Django, 8001->8000)
  +--> orders-service (Django, 8002->8000)
  +--> message-service (FastAPI, 8004->8000)

Infra partagee:
  - global-redis (6379)
  - rabbitmq (5672, ui 15672)
  - flower (5555)

Bases dediees:
  - account-db (PostgreSQL, host 5433)
  - catalogue-db (PostgreSQL, host 5432)
  - orders-db (PostgreSQL, host 5434)
```

## 2) Orchestration

La stack est pilotee par un compose unique a la racine:

- docker-compose.yml

Demarrage:

```bash
docker compose up -d --build
```

Arret:

```bash
docker compose down -v
```

## 3) Services applicatifs

### account-service

- Role: authentification JWT, profils utilisateur, endpoints de support inter-service
- Health: GET /health/
- Endpoints principaux: /auth/register/, /auth/login/, /auth/refresh/, /auth/me/, /auth/verify/

### catalogue-service

- Role: CRUD categories/fournisseurs/produits
- Health: GET /health/
- Endpoints principaux: /categories/, /suppliers/, /products/

### orders-service

- Role: gestion des commandes + orchestration metier
- Health: GET /health/
- Endpoints principaux: /orders/, /orders/{id}/confirm/
- Dependances logiques: catalogue-service, account-service, redis, orders-db

### message-service

- Role: API de notification (FastAPI) pour planifier l envoi d email
- Endpoints principaux: GET /, POST /send-email

## 4) Communication inter-services

- Synchrone HTTP: orders-service -> catalogue-service et account-service
- Asynchrone: Celery (orders-worker) + Redis broker/result backend
- Messagerie event-driven disponible via RabbitMQ (infrastructure presente)

## 5) Reseau et noms de service

Tous les conteneurs partagent le reseau Docker:

- store_front_network

Les appels inter-services utilisent les noms Docker DNS:

- <http://catalogue-service:8000>
- <http://account-service:8000>

## 6) Note importante sur depends_on

depends_on (forme courte) garantit surtout l ordre de demarrage des conteneurs.
Cela ne garantit pas que l application distante est deja prete a repondre.

Pour renforcer:

1. Ajouter des healthchecks applicatifs
2. Utiliser depends_on en forme longue avec condition service_healthy
3. Garder des retries/timeouts cote client

## 7) Hors scope actuel

Cette base n utilise pas Consul pour le service discovery.
Si Consul est introduit plus tard, il faudra ajouter une section dediee et mettre a jour le compose global.

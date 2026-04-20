# Audit de l architecture microservices

Date: 2026-04-20

## 1) Etat actuel verifie

Le projet est compose de 4 services applicatifs et de services d infrastructure:

| Service | Dossier | Port hote | Notes |
| --- | --- | --- | --- |
| account-service | services/account_service | 8003 | Django + JWT |
| catalogue-service | services/product_service | 8001 | Django catalogue |
| orders-service | services/order_service | 8002 | Django commandes |
| message-service | services/message_service | 8004 | FastAPI email |
| traefik | infrastructure/gateway (et compose global) | 80/443/8080 | reverse proxy |
| rabbitmq | infrastructure/messaging (et compose global) | 5672/15672 | broker |
| global-redis | infrastructure/redis (et compose global) | 6379 | cache + celery broker/result |
| flower | infrastructure/flower (et compose global) | 5555 | monitoring celery |

Orchestration actuelle recommandee: docker compose global racine (docker-compose.yml).

## 2) Points corrects

1. APIs account, catalogue, orders exposees et routees.
2. Endpoints health presents sur les 3 services Django.
3. Communication inter-services configuree via URLs Docker DNS.
4. Redis et Celery integres sur orders-service + orders-worker.
5. RabbitMQ et message-service presents dans la stack globale.
6. Traefik labels presents sur account, catalogue, orders, message.

## 3) Risques et ecarts prioritaires

### Critique

1. Secrets hardcodes dans les settings Django
   - SECRET_KEY est statique dans les settings des services.
   - Impact: risque securite eleve en hebergement.

2. Mode debug actif par defaut
   - DEBUG=True dans les settings actuels.
   - Impact: exposition d informations sensibles.

### Important

1. Serveur Django de dev utilise dans les conteneurs
   - Commande actuelle: python manage.py runserver
   - Impact: performances et robustesse insuffisantes pour production.

2. depends_on en forme courte uniquement
   - Exemples: orders-service depend de catalogue-service/account-service.
   - Limite: ordre de demarrage seulement, pas de readiness HTTP.

3. Incoherence de versions Django declarees
   - requirements des 3 services encore en Django>=4.2,<5.0.
   - Certains docs mentionnent Django 5.2.
   - Impact: confusion technique et maintenance.

4. Documentation heterogene
   - Plusieurs guides decrivent encore Consul ou des structures non presentes.
   - Impact: onboarding plus lent, erreurs de manipulation.

## 4) Plan de correction recommande

1. Production runtime
   - passer runserver -> gunicorn (Django) et conserver uvicorn cote FastAPI
   - ajouter restart policy stricte + logging

2. Readiness
   - ajouter healthchecks applicatifs
   - utiliser depends_on condition: service_healthy sur les services critiques

3. Securite configuration
   - externaliser SECRET_KEY, DEBUG, ALLOWED_HOSTS via .env
   - fournir .env.example complet et sans secrets reels

4. Normalisation docs
   - garder une architecture source of truth: docs/architecture.md
   - lier QUICK_START vers le compose global unique

## 5) Resume executif

La base applicative est fonctionnelle et mieux structuree qu au debut du projet.
Le principal effort restant concerne le passage en mode hebergement robuste:
securite des settings, readiness/healthchecks, et serveur WSGI/ASGI de production.

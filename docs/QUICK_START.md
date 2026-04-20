# QUICK START (DEBUTANT)

Ce guide te permet de lancer toute la plateforme rapidement avec le compose global.

## 1) Prerequis

1. Docker Desktop demarre
2. Docker Compose disponible (`docker compose version`)

## 2) Demarrer la plateforme complete

Depuis la racine du projet backend:

```bash
copy .env.example .env
docker compose up -d --build
```

## 3) Ports utiles

1. account-service: <http://localhost:8003>
2. catalogue-service: <http://localhost:8001>
3. orders-service: <http://localhost:8002>
4. message-service: <http://localhost:8004>
5. flower: <http://localhost:5555>
6. rabbitmq ui: <http://localhost:15672>
7. traefik dashboard: <http://localhost:8080>

## 4) Tests rapides

```bash
curl http://localhost:8003/health/
curl http://localhost:8001/health/
curl http://localhost:8002/health/
```

Tu dois obtenir un JSON avec `status: ok`.

## 5) Regle importante (inter-services)

Sur chaque appel HTTP inter-service, garde toujours un timeout explicite (exemple: `timeout=5`).

## 6) Comprendre `depends_on`

`depends_on` impose surtout un ordre de demarrage, pas une garantie que l API distante est prete.
Pour une dependance forte, ajoute des `healthcheck` + `condition: service_healthy`.

## 7) Arreter proprement

```bash
docker compose down -v
```

## 8) Pour continuer l apprentissage

1. docs/BEGINNER_MICROSERVICES_GUIDE.md
2. docs/BEGINNER_EXERCISES.md

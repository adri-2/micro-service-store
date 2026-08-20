billing-service/
│
├── app/
│ ├── main.py
│ │
│ ├── core/
│ │ └── config.py
│ │
│ ├── api/
│ │ └── invoices.py
│ │
│ ├── models/
│ │ └── invoice.py
│ │
│ ├── schemas/
│ │ └── invoice.py
│ │
│ ├── services/
│ │ └── invoice_service.py
│ │
│ └── messaging/
│ ├── connection.py
│ ├── publisher.py
│ └── consumer.py
│
├── requirements.txt
├── Dockerfile
└── .env
Oui. Pour ta démo PyCon, on va construire le **Billing Service progressivement**, sans créer trop de complexité.

## Plan de construction

### Étape 1 — Base du Billing Service

Objectif : avoir un FastAPI fonctionnel dans Docker.

```text
billing_service/
├── app/
│   ├── __init__.py
│   └── main.py
├── requirements.txt
├── Dockerfile
└── .env
```

On vérifie :

```text
Browser
   ↓
Traefik
   ↓
billing-service
   ↓
FastAPI
```

---

### Étape 2 — PostgreSQL + SQLAlchemy

On ajoute :

```text
billing-service
       ↓
 billing-db
```

Avec un modèle `Invoice`.

---

### Étape 3 — RabbitMQ

On ajoute :

```text
orders-service
      ↓
  RabbitMQ
      ↓
billing-service
```

avec l'événement :

```text
order.accounted
```

---

### Étape 4 — Consumer RabbitMQ

Le Billing Service écoute RabbitMQ :

```text
RabbitMQ
   ↓
Consumer
   ↓
InvoiceService
   ↓
Invoice
```

---

### Étape 5 — Création de facture

Quand :

```text
order.accounted
```

arrive, on crée :

```text
Invoice
├── invoice_number
├── order_id
├── client_id
├── client_name
├── total_amount
├── status
└── created_at
```

---

### Étape 6 — API des factures

On ajoute :

```http
GET /invoices
GET /invoices/{id}
```

---

### Étape 7 — PDF

Seulement à la fin :

```text
GET /invoices/{id}/pdf
```

avec ReportLab.

---

# Étape 1 — Création du Billing Service

Commence par créer :

```text
services/
└── billing_service/
    ├── Dockerfile
    ├── requirements.txt
    └── app/
        ├── __init__.py
        └── main.py
```

### `requirements.txt`

Mets :

```txt
fastapi
uvicorn[standard]
```

Pour l'instant **rien d'autre**.

On n'ajoute pas encore SQLAlchemy, RabbitMQ, Alembic, etc. L'idée est de vérifier que le service démarre correctement avant d'empiler les dépendances.

---

### `app/main.py`

Commence avec une API minimale :

```python
from fastapi import FastAPI

app = FastAPI(
    title="Billing Service",
    description="Service de facturation",
    version="1.0.0",
)


@app.get("/")
def root():
    return {
        "service": "billing-service",
        "status": "ok",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }
```

---

### `Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

# Étape 1.1 — Modifier ton `docker-compose.yml`

Ton service est déjà presque bon.

Garde :

```yaml
billing-service:
  build:
    context: ./services/billing_service
    dockerfile: Dockerfile

  container_name: billing-service

  command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

  restart: unless-stopped

  ports:
    - "8004:8000"

  labels:
    - traefik.enable=true
    - traefik.http.routers.billing.rule=(Host(`api.localhost`) || Host(`localhost`) || Host(`127.0.0.1`)) && PathPrefix(`/api/v1/billing`)
    - traefik.http.routers.billing.entrypoints=web
    - traefik.http.services.billing.loadbalancer.server.port=8000
    - traefik.docker.network=store_front_network

  volumes:
    - ./services/billing_service:/app

  networks:
    - store_front_network
```

Pour cette première étape, **supprime temporairement les variables `MAIL_*`**.

---

# Étape 1.2 — Construire

Depuis le dossier où se trouve ton `docker-compose.yml` :

```bash
docker compose build billing-service
```

Puis :

```bash
docker compose up billing-service
```

Tu dois obtenir quelque chose ressemblant à :

```text
billing-service  | INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

# Étape 1.3 — Tester directement

Comme tu exposes :

```yaml
"8004:8000"
```

teste :

```text
http://localhost:8004/
```

Tu dois recevoir :

```json
{
  "service": "billing-service",
  "status": "ok"
}
```

Puis :

```text
http://localhost:8004/health
```

Résultat :

```json
{
  "status": "healthy"
}
```

---

# Étape 1.4 — Tester FastAPI

FastAPI te donne automatiquement Swagger :

```text
http://localhost:8004/docs
```

Tu devrais voir :

```text
Billing Service

GET /
GET /health
```

---

## Ensuite : test avec Traefik

Ton router actuel utilise :

```yaml
Host(`billing.localhost`)
```

Donc tu pourras tester :

```text
http://billing.localhost/
```

et :

```text
http://billing.localhost/docs
```

Si `billing.localhost` ne fonctionne pas sur ta machine, on vérifiera ensuite le routing Traefik.

### À ce stade, ne touche pas encore à RabbitMQ.

Quand tu confirmes que **`localhost:8004/docs` fonctionne**, on passe à **l'étape 2 : PostgreSQL + SQLAlchemy + modèle `Invoice`**.

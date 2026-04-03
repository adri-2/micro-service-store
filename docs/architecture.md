Voici **une structure professionnelle d’un projet microservices avec Django et Django REST Framework**, incluant :

* **API Gateway** → Traefik
* **Service discovery** → Consul
* **Communication inter-services HTTP propre**
* **Conteneurisation** → Docker

Cette architecture est **proche de ce qui est utilisé en production**.

---

# 1️⃣ Architecture globale

```text
Client
   |
   v
API Gateway (Traefik)
   |
   v
-------------------------------
|        |        |           |
Auth     Product   Order     User
Service  Service   Service   Service
-------------------------------
      |          |
   PostgreSQL   Redis
      |
   Consul (service discovery)
```

Rôle :

| Composant       | Rôle                         |
| --------------- | ---------------------------- |
| API Gateway     | point d’entrée unique        |
| Consul          | registre des services        |
| Services Django | logique métier               |
| HTTP interne    | communication entre services |

---

# 2️⃣ Structure professionnelle du repository

```text
microservices-platform/

docker-compose.yml
.env
README.md

infrastructure/
│
├── gateway/
│
│
├── consul/
│   └── config/
│       
│
├── monitoring/
│   └── prometheus.yml

services/
│
├── account_service/
│
├── user_service/
│
├── product_service/
│
└── order_service/

shared/
│
├── clients/
│   └── service_client.py
│
├── utils/
│   └── exceptions.py
│
└── config/
    └── settings_base.py
```

---

# 3️⃣ Structure interne d’un microservice Django

Exemple **product-service**

```text
product-service/

Dockerfile
requirements.txt
entrypoint.sh
manage.py

config/
│
├── __init__.py
├── settings.py
├── urls.py
├── asgi.py
└── wsgi.py

apps/
│
└── products/
    │
    ├── migrations/
    │
    ├── models.py
    ├── serializers.py
    ├── views.py
    ├── urls.py
    ├── services.py
    ├── selectors.py
    └── tests.py
```

Rôle des couches :

| fichier     | rôle           |
| ----------- | -------------- |
| models      | structure DB   |
| serializers | validation API |
| views       | endpoints      |
| services    | logique métier |
| selectors   | requêtes DB    |

---

# 4️⃣ Communication inter-services propre

On évite d’appeler directement `requests` partout.

On crée **un client partagé**.

### shared/clients/service_client.py

```python
import requests

class ServiceClient:

    def __init__(self, service_url):
        self.service_url = service_url

    def get(self, path):
        response = requests.get(f"{self.service_url}/{path}")

        if response.status_code >= 400:
            raise Exception("Service error")

        return response.json()
```

---

# 5️⃣ Client pour appeler Product Service

Dans `order-service`.

```text
order-service/apps/orders/clients/product_client.py
```

```python
from shared.clients.service_client import ServiceClient

product_client = ServiceClient(
    "http://product-service:8000/api"
)

def get_product(product_id):
    return product_client.get(f"products/{product_id}")
```

---

# 6️⃣ Utilisation dans la logique métier

```python
from .clients.product_client import get_product

def create_order(product_id, quantity):

    product = get_product(product_id)

    total = product["price"] * quantity

    return {
        "product": product["name"],
        "total": total
    }
```

---

# 7️⃣ Service discovery avec Consul

Chaque service s’enregistre dans **Consul**.

Exemple config :

```json
{
  "service": {
    "name": "product-service",
    "port": 8000
  }
}
```

Ensuite les services peuvent appeler :

```
http://product-service.service.consul
```

---

# 8️⃣ API Gateway configuration

Avec **Traefik** :

```yaml
http:
  routers:

    product-router:
      rule: "PathPrefix(`/products`)"
      service: product-service

  services:

    product-service:
      loadBalancer:
        servers:
          - url: "http://product-service:8000"
```

---

# 9️⃣ docker-compose simplifié

```yaml
version: "3.9"

services:

  gateway:
    image: traefik:v3
    ports:
      - "80:80"

  consul:
    image: consul:1.15

  product-service:
    build: ./services/product-service

  order-service:
    build: ./services/order-service

  postgres:
    image: postgres:16
```

---

# 🔟 Flux complet d’une requête

```text
Client
   |
   v
Traefik (API Gateway)
   |
   v
Order Service
   |
   v
Product Service
   |
   v
Database
```

---

# 1️⃣1️⃣ Bonnes pratiques microservices Django

Toujours séparer :

| couche      | rôle                  |
| ----------- | --------------------- |
| selectors   | lecture DB            |
| services    | logique métier        |
| clients     | appel autres services |
| serializers | validation API        |

---

# 1️⃣2️⃣ Architecture complète finale

```text
microservices-platform/

infrastructure/
   gateway/
   consul/

services/
   auth-service/
   user-service/
   product-service/
   order-service/

shared/
   clients/
   utils/
```

---

💡 **Conseil important pour ton apprentissage**

Pour maîtriser les microservices avec **Django**, apprends dans cet ordre :

1. **Docker**
2. **API Gateway**
3. **communication inter-services HTTP**
4. **Service discovery (Consul)**
5. **message broker (RabbitMQ)**
6. **tasks async (Celery)**

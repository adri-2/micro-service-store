"""
GUIDE — Communication inter-services
======================================

Vue d'ensemble de TOUS les flux de communication entre les 3 services.


==============================================================================
DEUX TYPES DE COMMUNICATION
==============================================================================

Type 1 — HTTP synchrone (requête/réponse)
    order_service appelle catalogue-service et ATTEND la réponse
    avant de continuer. Si catalogue-service ne répond pas, order_service échoue.

    Cas d'usage : création de commande
    (besoin immédiat du prix et du stock pour valider la commande)

Type 2 — Messages asynchrones via RabbitMQ (événements)
    order_service publie un message dans RabbitMQ et CONTINUE sans attendre.
    catalogue-service lit ce message quand il est prêt.

    Cas d'usage : notification de stock, emails de confirmation
    (pas besoin d'une réponse immédiate)

Ce guide couvre les DEUX types.


==============================================================================
VUE D'ENSEMBLE DES FLUX
==============================================================================

                    ┌────────────────────┐
                    │   account-service  │
                    │  /users/           │
                    │  /clients/         │
                    └────────────────────┘
                             ▲
                    (futur)  │ HTTP GET vérifier client
                             │
    ┌────────────────────────┴────────────────────────────┐
    │                   order-service                     │
    │  /orders/                                           │
    │  /orders/{id}/confirm/                              │
    └──────────────────────────┬──────────────────────────┘
                               │
           ┌───────────────────┼─────────────────────┐
           │                   │                     │
      HTTP GET            HTTP POST            RabbitMQ
    get_product()   decrement_stock()      order.created
           │                   │            (futur)  │
           ▼                   ▼                     ▼
    ┌────────────────────────────────┐    ┌──────────────────┐
    │       catalogue-service        │    │    RabbitMQ       │
    │  /products/                    │    │  (message broker) │
    │  /products/{id}/               │    └──────────────────┘
    │  /products/{id}/decrement-stock│              │
    └────────────────────────────────┘              │
                                               (futur)
                                        catalogue-service
                                        consomme le message


==============================================================================
FLUX 1 — Création d'une commande (HTTP synchrone)
==============================================================================

Scénario : un client passe une commande de 2 unités du produit X.

Étapes dans l'ordre :

    Client API
      │
      │  POST /orders/
      │  { user_id, client_id, items_input: [{product_id, quantity}] }
      │
      ▼
    order-service (OrderSerializer.create)
      │
      │  1. Valide les données de base (user_id, client_id présents)
      │
      │  2. HTTP GET → catalogue-service
      │     GET /products/{product_id}/
      │     → récupère name, price, stock courant
      │
      │  3. Vérifie localement : stock >= quantity
      │     (défense en profondeur avant l'appel de décrémentation)
      │
      │  4. HTTP POST → catalogue-service
      │     POST /products/{product_id}/decrement-stock/
      │     { "quantity": 2 }
      │     → catalogue-service décrémente le stock
      │     → retourne 400 si stock insuffisant (race condition couverte)
      │
      │  5. Crée Order en base
      │
      │  6. Crée OrderItem avec le snapshot (product_name, unit_price)
      │
      ▼
    Réponse 201 Created avec la commande complète


Fichiers impliqués :

    order_service/app/serializers.py → OrderSerializer.create()
    order_service/app/services.py    → get_product(), check_and_decrement_stock()
    product_service/app/views.py     → ProductViewSet.decrement_stock()
    product_service/app/models.py    → Product.stock


Guides à suivre dans l'ordre :

    1. product_service/app/views_doc.py
       → ajouter decrement_stock dans ProductViewSet

    2. order_service/app/services_doc.py
       → implémenter get_product() et check_and_decrement_stock()

    3. order_service/app/serializers_doc.py
       → câbler les appels dans OrderSerializer.create()


==============================================================================
FLUX 2 — RabbitMQ (communication asynchrone)
==============================================================================

RabbitMQ est déjà dans l'infrastructure (rabbitmq_service/docker-compose.yml).
pika est installé dans les requirements.
L'URL est dans les variables d'environnement des docker-compose.

Mais rien n'est implémenté dans le code.

Voici ce que tu dois ajouter.

---

CONCEPT DE BASE DE RABBITMQ
----------------------------

    Publisher  →  [Exchange]  →  [Queue]  →  Consumer
    (publie)                     (stocke)     (consomme)

Un service PUBLIE un événement → RabbitMQ le stocke → un autre service le CONSOMME.
Le publisher ne sait pas qui consomme. Le consumer ne sait pas qui a publié.
C'est le principe du découplage.

---

QUAND UTILISER RABBITMQ PLUTÔT QU'HTTP ?
-----------------------------------------

HTTP synchrone → quand tu as BESOIN de la réponse pour continuer
    Exemple : récupérer le prix d'un produit avant de créer la commande

RabbitMQ asynchrone → quand tu n'as PAS besoin de la réponse immédiatement
    Exemple : après la création d'une commande, notifier d'autres services

---

ÉVÉNEMENTS À IMPLÉMENTER
--------------------------

Événement 1 : order.created
    Publisher  : order-service (après création réussie d'une commande)
    Consumer   : catalogue-service (pour mettre à jour ses statistiques)
                 account-service (pour envoyer un email de confirmation — futur)

    Message :
    {
        "event": "order.created",
        "order_id": "uuid",
        "client_id": "uuid",
        "items": [
            {"product_id": "uuid", "quantity": 2, "unit_price": "19.99"}
        ],
        "total_amount": "39.98",
        "created_at": "2026-03-05T10:00:00Z"
    }

Événement 2 : stock.low (optionnel, pour une alerte)
    Publisher  : catalogue-service (quand stock < seuil)
    Consumer   : à définir (logique d'alerte)

---

STRUCTURE D'UN PUBLISHER
--------------------------

Crée le fichier : order_service/app/publishers.py

    import pika
    import json
    from django.conf import settings

    def publish_order_created(order):
        \"""
        Publie l'événement order.created dans RabbitMQ.
        Appelé dans OrderSerializer.create() après la création réussie.
        \"""
        connection = None
        try:
            connection = pika.BlockingConnection(
                pika.URLParameters(settings.RABBITMQ_URL)
            )
            channel = connection.channel()

            # Déclarer la queue (crée si elle n'existe pas)
            channel.queue_declare(queue='order.created', durable=True)
            #                                 ↑            ↑
            #                             nom de queue   persistée sur disque

            message = {
                "event": "order.created",
                "order_id": str(order.id),
                "client_id": str(order.client_id),
                "total_amount": str(order.total_amount),
            }

            channel.basic_publish(
                exchange='',                       # exchange par défaut
                routing_key='order.created',       # nom de la queue cible
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,               # 2 = message persisté sur disque
                )
            )
        except Exception as e:
            # Ne pas faire planter la commande si RabbitMQ est indisponible
            # Loguer l'erreur mais laisser la commande passer
            print(f"[RabbitMQ] Impossible de publier order.created: {e}")
        finally:
            if connection and not connection.is_closed:
                connection.close()


    # TODO: appeler publish_order_created(order) dans OrderSerializer.create()
    # après la création de la commande et des items.


---

STRUCTURE D'UN CONSUMER
-------------------------

Crée le fichier : product_service/app/consumers.py

    import pika
    import json
    from django.conf import settings

    def consume_order_created():
        \"""
        Consomme les messages order.created depuis RabbitMQ.
        Ce consumer doit tourner en continu dans un processus séparé.
        \"""
        connection = pika.BlockingConnection(
            pika.URLParameters(settings.RABBITMQ_URL)
        )
        channel = connection.channel()

        # Déclarer la même queue que le publisher
        channel.queue_declare(queue='order.created', durable=True)

        # Une seule tâche à la fois (si un worker est occupé, RabbitMQ envoie au suivant)
        channel.basic_qos(prefetch_count=1)

        def callback(ch, method, properties, body):
            try:
                message = json.loads(body)
                print(f"[Consumer] Commande reçue: {message['order_id']}")

                # TODO: traiter le message
                # Exemple : mettre à jour des statistiques de vente
                # Exemple : enregistrer dans un log d'audit

                # Acquitter le message (dire à RabbitMQ qu'il est traité)
                ch.basic_ack(delivery_tag=method.delivery_tag)

            except Exception as e:
                print(f"[Consumer] Erreur: {e}")
                # Rejeter le message et le remettre dans la queue
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        channel.basic_consume(queue='order.created', on_message_callback=callback)
        print("[Consumer] En attente des messages order.created...")
        channel.start_consuming()   # bloque ici indéfiniment


---

COMMENT LANCER LE CONSUMER ?
------------------------------

Le consumer doit tourner en continu dans un processus séparé de Django.
Il y a deux façons de le lancer :

Option A — Commande Django personnalisée (recommandée) :

    Crée le fichier :
    product_service/app/management/commands/consume_orders.py

        from django.core.management.base import BaseCommand
        from app.consumers import consume_order_created

        class Command(BaseCommand):
            help = 'Démarre le consumer RabbitMQ pour les événements order.created'

            def handle(self, *args, **options):
                self.stdout.write("Démarrage du consumer...")
                consume_order_created()

    Lance avec :
        python manage.py consume_orders

    Dans le docker-compose, ajoute un service dédié :

        catalogue-consumer:
            build: .
            command: python manage.py consume_orders
            environment: ...  # même que catalogue-service
            networks:
                - store_front_network
            depends_on:
                - catalogue-db
                - rabbitmq

Option B — Thread en arrière-plan (plus simple mais moins robuste) :

    Dans product_service/app/apps.py :

        from django.apps import AppConfig
        import threading

        class AppConfig(AppConfig):
            name = 'app'

            def ready(self):
                from app.consumers import consume_order_created
                t = threading.Thread(target=consume_order_created, daemon=True)
                t.start()

    À éviter en production, mais utile pour tester rapidement.


==============================================================================
CONFIGURATION RABBITMQ_URL dans settings.py
==============================================================================

Ajouter dans les settings.py de order_service et product_service :

    RABBITMQ_URL = config('RABBITMQ_URL', default='amqp://guest:guest@localhost:5672/')

Dans les .env :
    RABBITMQ_URL=amqp://admin:admin@rabbitmq:5672/

Dans les docker-compose (déjà présent, juste à vérifier) :
    RABBITMQ_URL: amqp://admin:admin@rabbitmq:5672/


==============================================================================
ORDRE D'IMPLÉMENTATION RECOMMANDÉ
==============================================================================

Phase 1 — HTTP synchrone (à faire en premier)
    1. product_service : ajouter ProductViewSet.decrement_stock()
    2. order_service : implémenter services.py (get_product, check_and_decrement_stock)
    3. order_service : cåbler dans OrderSerializer.create()
    4. Tester le flux complet : POST /orders/ → vérifie le stock dans catalogue

Phase 2 — RabbitMQ asynchrone (après que Phase 1 fonctionne)
    5. order_service : créer publishers.py avec publish_order_created()
    6. Appeler publish_order_created(order) dans OrderSerializer.create()
    7. Tester que l'événement apparaît dans l'interface RabbitMQ (localhost:15672)
    8. product_service : créer consumers.py avec consume_order_created()
    9. Créer la commande Django manage.py consume_orders
    10. Lancer le consumer et vérifier qu'il reçoit les événements


==============================================================================
TESTER RABBITMQ MANUELLEMENT
==============================================================================

L'interface web RabbitMQ est accessible sur :
    http://localhost:15672
    login : admin / admin

Dans l'interface tu peux :
    - Voir les queues créées (onglet Queues)
    - Voir les messages en attente
    - Publier un message de test manuellement (sans code)
    - Lire un message depuis une queue pour vérifier son contenu

Utilise cela pour déboguer avant de câbler les consumers.


==============================================================================
CHECKLIST GLOBALE
==============================================================================

HTTP synchrone :
[ ] product_service/app/views.py : decrement_stock ajouté et testé
[ ] order_service/requirements.txt : requests ajouté
[ ] order_service/core/settings.py : CATALOGUE_SERVICE_URL ajouté
[ ] order_service/app/services.py : get_product() implémenté
[ ] order_service/app/services.py : check_and_decrement_stock() implémenté
[ ] order_service/app/serializers.py : appels dans create()
[ ] Test complet : créer une commande → vérifier que le stock diminue

RabbitMQ :
[ ] RABBITMQ_URL dans les settings.py des 2 services
[ ] order_service/app/publishers.py : publish_order_created() créé
[ ] publish_order_created() appelé dans OrderSerializer.create()
[ ] Message visible dans l'interface RabbitMQ (localhost:15672)
[ ] product_service/app/consumers.py : consume_order_created() créé
[ ] product_service/app/management/commands/consume_orders.py créé
[ ] Consumer lancé et reçoit les messages
"""

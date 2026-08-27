import asyncio
import json
import os

import aio_pika
from aio_pika import ExchangeType

from .billing import handle_order_accounted

RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL",
    "amqp://admin:admin@rabbitmq:5672/"
)


async def connect_rabbitmq():

    retry_delay = float(os.getenv("RABBITMQ_RETRY_DELAY", "2"))
    max_retry_delay = float(os.getenv("RABBITMQ_MAX_RETRY_DELAY", "10"))

    while True:
        print(">>> Connexion à RabbitMQ...")

        try:
            connection = await aio_pika.connect_robust(
                RABBITMQ_URL
            )
            break
        except (ConnectionRefusedError, aio_pika.exceptions.AMQPConnectionError) as exc:
            print(
                f">>> RabbitMQ indisponible ({exc}); "
                f"nouvelle tentative dans {retry_delay:g}s"
            )
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_retry_delay)

    print(">>> Connexion RabbitMQ OK")

    channel = await connection.channel()

    print(">>> Channel créé")

    exchange = await channel.declare_exchange(
        "orders.events",
        ExchangeType.TOPIC,
        durable=True
    )

    print(">>> Exchange orders.events OK")

    queue = await channel.declare_queue(
        "billing.orders",
        durable=True
    )

    print(">>> Queue billing.orders OK")

    await queue.bind(
        exchange,
        routing_key="order.accounted"
    )

    print(">>> Binding order.accounted OK")

    return connection, channel, queue


async def consume_orders(queue):

    print(">>> CONSUMER BILLING DÉMARRÉ")

    async with queue.iterator() as queue_iter:

        async for message in queue_iter:

            print(">>> NOUVEAU MESSAGE")

            async with message.process():

                print(
                    "EVENT REÇU :",
                    message.routing_key
                )

                body = message.body.decode()
                event = json.loads(body)

                print("EVENT DATA :",event)

                if message.routing_key == "order.accounted":
                    await handle_order_accounted(event)
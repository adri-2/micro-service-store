import aio_pika
import os
from aio_pika import ExchangeType
import logging
RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL",
    "amqp://admin:admin@rabbitmq:5672/"
)
async def connect_rabbitmq():

    print(">>> Connexion à RabbitMQ...")

    connection = await aio_pika.connect_robust(
        RABBITMQ_URL
    )

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

                print(
                    "BODY :",
                    message.body.decode()
                )
import pika
import os
import json
RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL",
    "amqp://admin:admin@rabbitmq:5672"
)
def publish_event(routing_key:str, payload:dict):
    parameters = pika.URLParameters(RABBITMQ_URL)

    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    exchamge = "orders.events"
    channel.exchange_declare(
        exchange=exchamge,
        exchange_type="topic",
        durable=True,
    )
    channel.basic_publish(
        exchange=exchamge,
        routing_key=routing_key,
        body=json.dumps(payload),
        properties=pika.BasicProperties(
            content_type="application/json",
            delivery_mode=2
        )

    )
    print(" [x] Sent 'Hello, RabbitMQ!'")
    connection.close()


def publish_order_accounted():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq"))
    channel = connection.channel()

    channel.queue_declare(queue="billing.orders")

    channel.basic_publish(
        exchange="orders.events",
        routing_key="orders.events",
        body={
    "event": "orders.accounted",
    "order_id": "...",
    "client_id": "...",
    "client_name": "Amine Diallo",
    "total_amount": "2975.19"
}
    )
    print(" [x] Sent 'Hello, RabbitMQ!'")
    connection.close()
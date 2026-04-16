import json

import pika
from django.conf import settings


class RabbitMQProducer:
    def __init__(self, host:str, port:int):
        self.host = settings.RABBITMQ_HOST
        self.port = settings.RABBITMQ_PORT
        self.user = settings.RABBITMQ_USER
        self.password = settings.RABBITMQ_PASSWORD
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=self.host)
        )
        self.channel = self.connection.channel()
        self.channel_declare(
            exchange='product_events',
            exchange_type='topic',
            durable=True
        )
        self.channel.queue_declare(queue='product_created', durable=True)
    def publish(self, message:str,routing_key:str):
        self.channel.basic_publish(
            exchange='product_events',
            routing_key=routing_key,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
            )
        )
    
    def close(self):
        self.connection.close()
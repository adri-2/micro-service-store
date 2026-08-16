from decimal import Decimal
from django.db import transaction

from app.models import Order, OrderItem
from . import (
    get_customer,
    get_products_bulk,
    get_user,
)

def order_processing_service(order_id: str, access_token: str | None = None):

    order = Order.objects.prefetch_related("items").get(id=order_id)

    user = get_user(str(order.user_id), access_token)
    customer = get_customer(str(order.client_id), access_token)

    items = list(order.items.all())

    product_ids = [str(i.product_id) for i in items]

    product_map = get_products_bulk(product_ids, access_token)

    with transaction.atomic():

        order.user_name = user.get("username", "Inconnu")

        order.client_name = (
            f"{customer.get('first_name', '')} "
            f"{customer.get('last_name', '')}"
        ).strip() or "Inconnu"

        for item in items:

            product = product_map.get(str(item.product_id))

            if not product:
                raise ValueError(
                    f"Produit introuvable : {item.product_id}"
                )

            item.product_name = product["name"]
            item.unit_price = Decimal(str(product["price"]))
            item.subtotal = item.unit_price * item.quantity

        OrderItem.objects.bulk_update(
            items,
            ["product_name", "unit_price", "subtotal"]
        )

        order.update_total()

        order.status = Order.StatusChoices.PENDING

        order.save(update_fields=[
            "user_name",
            "client_name",
            "status",
            "updated_at",
        ])

    return {
        "order_id": str(order.id),
        "status": "processed",
    }

def order_processing_service(order_id: str, access_token: str | None = None):

    order = Order.objects.prefetch_related("items").get(id=order_id)

    user = get_user(str(order.user_id), access_token)
    customer = get_customer(str(order.client_id), access_token)

    items = list(order.items.all())

    product_ids = [str(i.product_id) for i in items]

    product_map = get_products_bulk(product_ids, access_token)

    with transaction.atomic():

        order.user_name = user.get("username", "Inconnu")

        order.client_name = (
            f"{customer.get('first_name', '')} "
            f"{customer.get('last_name', '')}"
        ).strip() or "Inconnu"

        for item in items:

            product = product_map.get(str(item.product_id))

            if not product:
                raise ValueError(
                    f"Produit introuvable : {item.product_id}"
                )

            item.product_name = product["name"]
            item.unit_price = Decimal(str(product["price"]))
            item.subtotal = item.unit_price * item.quantity

        OrderItem.objects.bulk_update(
            items,
            ["product_name", "unit_price", "subtotal"]
        )

        order.update_total()

        order.status = Order.StatusChoices.PENDING

        order.save(update_fields=[
            "user_name",
            "client_name",
            "status",
            "updated_at",
        ])

    return {
        "order_id": str(order.id),
        "status": "processed",
    }
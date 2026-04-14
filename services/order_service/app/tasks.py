from decimal import Decimal

from celery import shared_task
from django.db import transaction

from .models import Order
from .services import get_customer, get_products_bulk, get_user


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def process_order_creation(self, order_id: str, access_token: str | None = None):
    try:
        order = Order.objects.prefetch_related("items").get(id=order_id)
    except Order.DoesNotExist:
        return {"order_id": order_id, "status": "not_found"}

    try:
        user = get_user(str(order.user_id), access_token)
        customer = get_customer(str(order.client_id), access_token)
    except Exception as exc:
        raise self.retry(exc=exc)

    items = list(order.items.all())
    product_ids = [str(item.product_id) for item in items]

    try:
        product_map = get_products_bulk(product_ids, access_token)
    except Exception as exc:
        raise self.retry(exc=exc)

    with transaction.atomic():
        order.user_name = user.get("username", "Inconnu")
        order.client_name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()

        for item in items:
            product = product_map.get(str(item.product_id))
            if not product:
                raise ValueError(f"Produit introuvable: {item.product_id}")

            item.product_name = product["name"]
            item.unit_price = Decimal(str(product["price"]))
            item.subtotal = item.unit_price * item.quantity
            item.save(update_fields=["product_name", "unit_price", "subtotal", "updated_at"])

        order.update_total()
        if order.status == Order.StatusChoices.DRAFT:
            order.status = Order.StatusChoices.PENDING
        order.save(update_fields=["user_name", "client_name", "status", "updated_at"])

    return {"order_id": str(order.id), "status": "processed"}
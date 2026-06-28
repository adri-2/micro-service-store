from decimal import Decimal

from celery import shared_task
from django.db import transaction

from .models import Order, OrderItem
from .services import (
    get_customer,
    get_products_bulk,
    get_user,
    release_stock
)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def process_order_creation(
    self,
    order_id: str,
    items_data: list[dict] | None = None,
    access_token: str | None = None,
):
    items_data = items_data or []

    try:
        order = Order.objects.prefetch_related("items").get(id=order_id)
    except Order.DoesNotExist:
        return {"order_id": order_id, "status": "not_found"}

    try:
        user = get_user(str(order.user_id), access_token)
        customer = get_customer(str(order.client_id), access_token)

        items = list(order.items.all())
        if items_data:
            product_ids = [str(item["product_id"]) for item in items_data]
        else:
            product_ids = [str(item.product_id) for item in items]

        product_map = get_products_bulk(product_ids, access_token)

        with transaction.atomic():
            order.user_name = user.get("username", "Inconnu")
            order.client_name = (
                f"{customer.get('first_name', '')} {customer.get('last_name', '')}"
            ).strip() or "Inconnu"

            if items_data and not items:
                for item_data in items_data:
                    product_id = str(item_data["product_id"])
                    product = product_map.get(product_id)
                    if not product:
                        raise ValueError(f"Produit introuvable : {product_id}")

                    OrderItem.objects.create(
                        order=order,
                        product_id=product_id,
                        product_name=product["name"],
                        unit_price=Decimal(str(product["price"])),
                        quantity=item_data["quantity"],
                        subtotal=0,
                    )

                items = list(order.items.all())

            for item in items:
                product = product_map.get(str(item.product_id))
                if not product:
                    raise ValueError(f"Produit introuvable : {item.product_id}")

                item.product_name = product["name"]
                item.unit_price = Decimal(str(product["price"]))
                item.subtotal = item.unit_price * item.quantity
                item.save(
                    update_fields=[
                        "product_name",
                        "unit_price",
                        "subtotal",
                        "updated_at",
                    ]
                )

            order.update_total()

            if order.status == Order.StatusChoices.DRAFT:
                order.status = Order.StatusChoices.PENDING

            order.save(
                update_fields=[
                    "user_name",
                    "client_name",
                    "status",
                    "updated_at",
                ]
            )

        return {"order_id": str(order.id), "status": "processed"}

    except Exception as exc:

        # Si tous les retries ne sont pas encore épuisés
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)

        # Plus de retry : on libère le stock
        items = [
            {
                "product_id": str(item.product_id),
                "quantity": item.quantity,
            }
            for item in order.items.all()
        ]

        try:
            release_stock(items, access_token)
        except Exception:
            # À logger
            pass

        order.status = Order.StatusChoices.CANCELLED
        order.save(update_fields=["status", "updated_at"])

        raise
from celery import shared_task
from django.db import transaction

from .services import order_processing_service, release_stock


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def process_order_creation(self, order_id: str, access_token: str | None = None):

    try:
        return order_processing_service(order_id, access_token)

    except Exception as exc:

        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)

        # fallback final
        try:
            release_stock(order_id, access_token)
        except Exception:
            pass

        from .models import Order

        Order.objects.filter(id=order_id).update(
            status=Order.StatusChoices.CANCELLED
        )

        raise
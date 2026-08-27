from .database import SessionLocal
from .models import Invoice
import uuid


async def handle_order_accounted(event):

    db = SessionLocal()

    try:

        order_id = uuid.UUID(event["order_id"])

        # Vérifier si la facture existe déjà
        existing_invoice = (
            db.query(Invoice)
            .filter(
                Invoice.order_id == order_id
            )
            .first()
        )

        if existing_invoice:

            print(
                f"Facture déjà existante pour {order_id}"
            )

            return

        invoice_number = generate_invoice_number()

        invoice = Invoice(
            invoice_number=invoice_number,
            order_id=order_id,
            client_id=uuid.UUID(event["client_id"]),
            client_name=event["client_name"],
            total_amount=event["total_amount"],
            status="issued",
        )

        db.add(invoice)

        db.commit()

        db.refresh(invoice)

        print(
            "FACTURE CRÉÉE :",
            invoice.invoice_number
        )

    except Exception:

        db.rollback()

        raise

    finally:

        db.close()


def generate_invoice_number():

    return f"FAC-{uuid.uuid4().hex[:8].upper()}"
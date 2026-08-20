import uuid

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    invoice_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
    )

    order_id: Mapped[uuid.UUID]

    client_id: Mapped[uuid.UUID]

    client_name: Mapped[str] = mapped_column(
        String(150)
    )

    total_amount: Mapped[float] = mapped_column(
        Numeric(10, 2)
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="issued",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )
import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from armada.db import Base


class Product(Base):
    __tablename__ = "products"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    msrp: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2), nullable=False)
    product_type: Mapped[str] = mapped_column(String(50), nullable=False)

    __mapper_args__ = {
        "polymorphic_on": "product_type",
        "polymorphic_identity": "product",
    }


class ProductGun(Product):
    __tablename__ = "product_guns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), primary_key=True
    )
    caliber: Mapped[str] = mapped_column(String(50), nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    weight_lbs: Mapped[Decimal] = mapped_column(Numeric(precision=5, scale=2), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(200), nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": "gun",
    }

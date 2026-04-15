import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import with_polymorphic

from armada.models.products import Product, ProductGun
from armada.types.products import ProductGunCreate, ProductGunUpdate


class ProductManager:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_gun(self, data: ProductGunCreate) -> ProductGun:
        product = ProductGun(
            name=data.name,
            description=data.description,
            msrp=data.msrp,
            caliber=data.caliber,
            action_type=data.action_type,
            weight_lbs=data.weight_lbs,
            category=data.category,
            manufacturer=data.manufacturer,
        )
        self.session.add(product)
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def get_by_id(self, product_id: uuid.UUID) -> Product | None:
        entity = with_polymorphic(Product, [ProductGun])
        result = await self.session.execute(
            select(entity).where(
                entity.id == product_id,
                entity.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def list_products(self, product_type: str | None = None) -> list[Product]:
        entity = with_polymorphic(Product, [ProductGun])
        stmt = select(entity).where(entity.is_deleted == False)  # noqa: E712
        if product_type is not None:
            stmt = stmt.where(entity.product_type == product_type)
        stmt = stmt.order_by(entity.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_gun(self, product_id: uuid.UUID, data: ProductGunUpdate) -> ProductGun | None:
        product = await self.get_by_id(product_id)
        if product is None:
            return None
        updates = data.model_dump(exclude_unset=True)
        for key, value in updates.items():
            setattr(product, key, value)
        # Explicitly touch parent row so updated_at fires even when only child columns change
        product.updated_at = func.now()
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def delete(self, product_id: uuid.UUID) -> Product | None:
        product = await self.get_by_id(product_id)
        if product is None:
            return None
        product.is_deleted = True
        await self.session.commit()
        await self.session.refresh(product)
        return product

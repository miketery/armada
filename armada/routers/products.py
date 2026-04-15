import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from armada.auth.dependencies import (
    SuperUserDependency,
    UserDependency,
    get_product_manager,
)
from armada.managers.products import ProductManager
from armada.types.products import (
    ProductGunCreate,
    ProductGunResponse,
    ProductGunUpdate,
    ProductResponse,
)

products_router = APIRouter(prefix="/products", tags=["products"])


@products_router.post(
    "/guns", response_model=ProductGunResponse, status_code=status.HTTP_201_CREATED
)
async def create_gun(
    data: ProductGunCreate,
    current_user: SuperUserDependency,
    manager: ProductManager = Depends(get_product_manager),
):
    product = await manager.create_gun(data)
    return product


@products_router.get("", response_model=list[ProductGunResponse])
async def list_products(
    current_user: UserDependency,
    product_type: str | None = None,
    manager: ProductManager = Depends(get_product_manager),
):
    return await manager.list_products(product_type=product_type)


@products_router.get("/{product_id}", response_model=ProductGunResponse)
async def get_product(
    product_id: uuid.UUID,
    current_user: UserDependency,
    manager: ProductManager = Depends(get_product_manager),
):
    product = await manager.get_by_id(product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@products_router.patch("/guns/{product_id}", response_model=ProductGunResponse)
async def update_gun(
    product_id: uuid.UUID,
    data: ProductGunUpdate,
    current_user: SuperUserDependency,
    manager: ProductManager = Depends(get_product_manager),
):
    product = await manager.update_gun(product_id, data)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@products_router.delete("/{product_id}", response_model=ProductResponse)
async def delete_product(
    product_id: uuid.UUID,
    current_user: SuperUserDependency,
    manager: ProductManager = Depends(get_product_manager),
):
    product = await manager.delete(product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product

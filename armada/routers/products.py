import uuid
from html import escape

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse

from armada.auth.dependencies import (
    SuperUserDependency,
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


@products_router.get("/browse", response_class=HTMLResponse)
async def browse_products(
    product_type: str | None = "gun",
    manager: ProductManager = Depends(get_product_manager),
):
    products = await manager.list_products(product_type=product_type)
    if not products:
        return HTMLResponse('<p class="text-zinc-400 text-center py-12">No products found.</p>')
    cards = []
    for p in products:
        category_label = escape(p.category).replace("_", " ").title()
        if p.images:
            image_html = (
                f'<img src="{escape(p.images[0].url)}" alt="{escape(p.name)}"'
                f' class="w-full h-48 object-contain bg-zinc-900 rounded mb-4" loading="lazy">'
            )
        else:
            image_html = (
                '<div class="w-full h-48 bg-zinc-900 rounded mb-4 flex items-center'
                ' justify-center text-zinc-600 text-sm">No image</div>'
            )
        cards.append(f"""
        <div class="bg-zinc-800 border border-zinc-700 rounded-lg p-6
                    hover:border-amber-500/50 transition-colors">
            {image_html}
            <div class="flex justify-between items-start mb-3">
                <h3 class="text-lg font-semibold text-white">{escape(p.name)}</h3>
                <span class="text-amber-400 font-bold text-lg">${p.msrp:,.2f}</span>
            </div>
            <p class="text-zinc-400 text-sm mb-4 line-clamp-2">{escape(p.description)}</p>
            <div class="flex flex-wrap gap-2">
                <span class="px-2 py-1 bg-zinc-700 rounded text-xs text-zinc-300">
                    {escape(p.manufacturer)}</span>
                <span class="px-2 py-1 bg-zinc-700 rounded text-xs text-zinc-300">
                    {escape(p.caliber)}</span>
                <span class="px-2 py-1 bg-zinc-700 rounded text-xs text-zinc-300">
                    {escape(p.action_type)}</span>
                <span class="px-2 py-1 bg-zinc-700 rounded text-xs text-zinc-300">
                    {category_label}</span>
                <span class="px-2 py-1 bg-zinc-700 rounded text-xs text-zinc-300">
                    {p.weight_lbs} lbs</span>
            </div>
        </div>""")
    return HTMLResponse("\n".join(cards))


@products_router.get("", response_model=list[ProductGunResponse])
async def list_products(
    product_type: str | None = None,
    manager: ProductManager = Depends(get_product_manager),
):
    return await manager.list_products(product_type=product_type)


@products_router.get("/{product_id}", response_model=ProductGunResponse)
async def get_product(
    product_id: uuid.UUID,
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

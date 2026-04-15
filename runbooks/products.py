import argparse
import asyncio
import sys
from decimal import Decimal

from armada.db import get_database
from armada.managers.products import ProductManager
from armada.types.products import ProductGunCreate, ProductGunUpdate


async def list_products(args):
    async with get_database() as session:
        manager = ProductManager(session)
        products = await manager.list_products(product_type=args.type)
        if not products:
            print("No products found")
            return
        for p in products:
            line = f"[{p.id}] {p.name} - ${p.msrp} ({p.product_type})"
            if hasattr(p, "category"):
                line += f" [{p.category}]"
            print(line)
        print(f"\n{len(products)} product(s)")


async def create_gun(args):
    data = ProductGunCreate(
        name=args.name,
        description=args.description,
        msrp=Decimal(args.msrp),
        caliber=args.caliber,
        action_type=args.action_type,
        weight_lbs=Decimal(args.weight_lbs),
        category=args.category,
        manufacturer=args.manufacturer,
    )
    async with get_database() as session:
        manager = ProductManager(session)
        product = await manager.create_gun(data)
        print(f"Created: [{product.id}] {product.name} - ${product.msrp}")


async def update_gun(args):
    updates = {}
    for field in [
        "name",
        "description",
        "msrp",
        "caliber",
        "action_type",
        "weight_lbs",
        "category",
        "manufacturer",
    ]:
        val = getattr(args, field, None)
        if val is not None:
            if field in ("msrp", "weight_lbs"):
                val = Decimal(val)
            updates[field] = val

    if not updates:
        print("No fields to update")
        sys.exit(1)

    data = ProductGunUpdate(**updates)
    async with get_database() as session:
        manager = ProductManager(session)
        product = await manager.update_gun(args.id, data)
        if product is None:
            print(f"Product not found: {args.id}")
            sys.exit(1)
        print(f"Updated: [{product.id}] {product.name} - ${product.msrp}")


def main():
    parser = argparse.ArgumentParser(description="Armada product management")
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    ls = sub.add_parser("list", help="List products")
    ls.add_argument("--type", help="Filter by product_type (e.g. gun)")

    # create-gun
    cg = sub.add_parser("create-gun", help="Create a gun product")
    cg.add_argument("--name", required=True)
    cg.add_argument("--description", required=True)
    cg.add_argument("--msrp", required=True)
    cg.add_argument("--caliber", required=True)
    cg.add_argument("--action-type", required=True)
    cg.add_argument("--weight-lbs", required=True)
    cg.add_argument("--category", required=True)
    cg.add_argument("--manufacturer", required=True)

    # update-gun
    ug = sub.add_parser("update-gun", help="Update a gun product")
    ug.add_argument("id", help="Product UUID")
    ug.add_argument("--name")
    ug.add_argument("--description")
    ug.add_argument("--msrp")
    ug.add_argument("--caliber")
    ug.add_argument("--action-type")
    ug.add_argument("--weight-lbs")
    ug.add_argument("--category")
    ug.add_argument("--manufacturer")

    args = parser.parse_args()

    if args.command == "list":
        asyncio.run(list_products(args))
    elif args.command == "create-gun":
        asyncio.run(create_gun(args))
    elif args.command == "update-gun":
        asyncio.run(update_gun(args))


if __name__ == "__main__":
    main()

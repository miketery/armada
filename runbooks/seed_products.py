import asyncio
import csv
from decimal import Decimal
from pathlib import Path

from armada.db import get_database
from armada.managers.products import ProductManager
from armada.types.products import ProductGunCreate, ProductImageCreate


def parse_images(raw: str, product_name: str) -> list[ProductImageCreate]:
    if not raw:
        return []
    return [
        ProductImageCreate(url=url.strip(), alt_text=product_name, sort_order=i)
        for i, url in enumerate(raw.split("|"))
        if url.strip()
    ]


async def main():
    csv_path = Path(__file__).resolve().parent.parent / "data" / "guns.csv"

    async with get_database() as session:
        manager = ProductManager(session)

        existing = await manager.list_products(product_type="gun")
        if existing:
            print(f"Products already seeded ({len(existing)} guns found)")
            return

        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                images = parse_images(row.get("images", ""), row["name"])
                data = ProductGunCreate(
                    name=row["name"],
                    description=row["description"],
                    msrp=Decimal(row["msrp"]),
                    caliber=row["caliber"],
                    action_type=row["action_type"],
                    weight_lbs=Decimal(row["weight_lbs"]),
                    category=row["category"],
                    manufacturer=row["manufacturer"],
                    images=images,
                )
                product = await manager.create_gun(data)
                print(
                    f"  Created: {product.name} ({product.category})"
                    f" with {len(product.images)} image(s)"
                )
                count += 1

        print(f"Seeded {count} products")


if __name__ == "__main__":
    asyncio.run(main())

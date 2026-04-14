import asyncio

from armada.db import get_database
from armada.managers.users import UserManager


async def main():
    async with get_database() as session:
        manager = UserManager(session)
        existing = await manager.get_by_email("michael@tmisha.com")
        if existing:
            print(f"User already exists: {existing.id}")
            return
        user = await manager.create_user("michael@tmisha.com", "password123", is_superuser=True)
        print(f"Created user: {user.id} ({user.email})")


if __name__ == "__main__":
    asyncio.run(main())

import asyncio

from armada.database import async_session
from armada.modules.users.manager import UserManager


async def main():
    async with async_session() as session:
        manager = UserManager(session)
        existing = await manager.get_by_email("michael@tmisha.com")
        if existing:
            print(f"User already exists: {existing.id}")
            return
        user = await manager.create_user("michael@tmisha.com", "password123")
        print(f"Created user: {user.id} ({user.email})")


if __name__ == "__main__":
    asyncio.run(main())

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from armada.config import settings
from armada.models.users import Session, User

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class UserManager:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_user(self, email: str, password: str) -> User:
        password_hash = pwd_context.hash(password)
        user = User(email=email, password_hash=password_hash)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def authenticate(self, email: str, password: str) -> User | None:
        user = await self.get_by_email(email)
        if user is None:
            return None
        if not pwd_context.verify(password, user.password_hash):
            return None
        return user

    async def create_session(self, user_id: uuid.UUID) -> Session:
        token = secrets.token_hex(32)
        expires_at = datetime.now(UTC) + timedelta(minutes=settings.session_expire_minutes)
        session = Session(user_id=user_id, token=token, expires_at=expires_at)
        self.session.add(session)
        await self.session.commit()
        await self.session.refresh(session)
        return session

    async def get_user_by_token(self, token: str) -> User | None:
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(User)
            .join(Session, Session.user_id == User.id)
            .where(Session.token == token, Session.expires_at > now)
        )
        return result.scalar_one_or_none()

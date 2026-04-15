from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from armada.db import DatabaseSession, database_dependency
from armada.managers.products import ProductManager
from armada.managers.users import UserManager
from armada.models.users import User

bearer_scheme = HTTPBearer()

Database = Annotated[DatabaseSession, Depends(database_dependency)]


def get_manager(db: Database) -> UserManager:
    return UserManager(db)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    manager: UserManager = Depends(get_manager),
) -> User:
    user = await manager.get_user_by_token(credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


UserDependency = Annotated[User, Depends(get_current_user)]


async def require_superuser(current_user: UserDependency) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required",
        )
    return current_user


SuperUserDependency = Annotated[User, Depends(require_superuser)]


def get_product_manager(db: Database) -> ProductManager:
    return ProductManager(db)

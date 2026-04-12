from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from armada.database import get_session
from armada.modules.users.manager import UserManager
from armada.modules.users.models import User
from armada.modules.users.types import TokenResponse, UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/users", tags=["users"])
bearer_scheme = HTTPBearer()


def get_manager(session: AsyncSession = Depends(get_session)) -> UserManager:
    return UserManager(session)


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


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, manager: UserManager = Depends(get_manager)):
    existing = await manager.get_by_email(data.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user = await manager.create_user(data.email, data.password)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, manager: UserManager = Depends(get_manager)):
    user = await manager.authenticate(data.email, data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    session = await manager.create_session(user.id)
    return TokenResponse(token=session.token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user

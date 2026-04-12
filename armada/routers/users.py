from fastapi import APIRouter, Depends, HTTPException, status

from armada.auth.dependencies import CurrentUser, Database, get_manager
from armada.managers.users import UserManager
from armada.types.users import TokenResponse, UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


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
async def me(current_user: CurrentUser):
    return current_user

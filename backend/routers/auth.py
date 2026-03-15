from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.security import verify_password, get_password_hash, create_access_token
from models.models import User
from schemas.schemas import UserCreate, UserLogin, Token, UserOut

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    try:
        # Check if email already exists
        result = await db.execute(select(User).where(User.email == user_data.email))
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=get_password_hash(user_data.password),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login and get JWT token."""
    try:
        result = await db.execute(select(User).where(User.email == credentials.email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(credentials.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        if not user.is_active:
            raise HTTPException(status_code=400, detail="Account is deactivated")

        token = create_access_token({"sub": user.email, "user_id": user.id, "name": user.full_name})
        return Token(
            access_token=token,
            user=UserOut.model_validate(user)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

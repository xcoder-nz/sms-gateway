from fastapi import APIRouter, Depends, HTTPException
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.api.schemas import UserCreate, UserOut, UserPatch
from app.db import get_db
from app.models import User, Wallet

router = APIRouter(prefix="/api/users", tags=["users"])
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    return db.query(User).order_by(User.id.asc()).all()


@router.post("", response_model=UserOut)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    exists = db.query(User).filter(User.phone_number == payload.phone_number).first()
    if exists:
        raise HTTPException(status_code=400, detail="Phone already exists")
    user = User(
        full_name=payload.full_name,
        phone_number=payload.phone_number,
        pin_hash=pwd.hash(payload.pin),
        role=payload.role,
        status=payload.status,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.add(Wallet(user_id=user.id, currency="AFN", balance=0, wallet_status="active"))
    db.commit()
    return user


@router.patch("/{user_id}", response_model=UserOut)
def patch_user(user_id: int, payload: UserPatch, db: Session = Depends(get_db)) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.status is not None:
        user.status = payload.status
    db.commit()
    db.refresh(user)
    return user

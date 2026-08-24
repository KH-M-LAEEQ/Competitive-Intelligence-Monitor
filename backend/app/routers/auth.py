from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy.orm import Session 
from app.database import get_db
from app.models.user import User
from app.schemas.auth import UserRegister
from app.core.security import hash_password
from app.schemas.auth import UserLogin
from app.dependencies import get_current_user
from app.core.security import (verify_password,create_access_token)

router=APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

@router.post("/register")
def register(
    user: UserRegister,
    db: Session = Depends(get_db)
):
    existing_user=(
        db.query(User)
        .filter(User.email == user.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email Already Exist"
        )

    new_user=User(
        email=user.email,
        hashed_password=hash_password(user.password),
        full_name=user.full_name
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return{
        "Message" : "User Registered Successfully"
    }

@router.post("/login")
def login(
    user : UserLogin,
    db : Session=Depends(get_db)
):
     db_user = (
        db.query(User)
        .filter(User.email == user.email)
        .first()
    )
     if not db_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )
     if not verify_password(
        user.password,
        db_user.hashed_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )
     access_token = create_access_token(
        data={"sub": db_user.email}
    )
     return {
        "access_token": access_token,
        "token_type": "bearer"
    }
@router.get("/me")
def me(
    current_user: User = Depends(get_current_user)
):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name
    }
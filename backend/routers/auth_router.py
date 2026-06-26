from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas
import auth

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=schemas.UserOut, status_code=201)
def signup(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Creates a new user.
    - Checks for duplicate email (HTTP 400 if taken)
    - Hashes password with bcrypt
    - Returns user info — NOT the password hash
    """
    existing = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = models.User(
        email=user_data.email,
        hashed_password=auth.get_password_hash(user_data.password),
        full_name=user_data.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)  # Refresh to get DB-generated id and created_at
    return user


@router.post("/login", response_model=schemas.Token)
def login(user_data: schemas.UserLogin, db: Session = Depends(get_db)):
    """
    Authenticates user and returns JWT.
    Returns 401 for BOTH wrong email AND wrong password —
    never reveal which one was wrong (prevents user enumeration attacks).
    """
    user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if not user or not auth.verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    """Returns the logged-in user's profile. Used by frontend to show the user's name."""
    return current_user
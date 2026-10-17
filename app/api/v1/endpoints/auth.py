from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from pymongo.errors import DuplicateKeyError

from app.db.mongo import get_db
from app.schemas.user import LoginRequest, UserCreate, UserOut
from app.services.auth_service import (
    hash_password, verify_password, create_access_token, get_current_user
)
from app.services.user_service import ensure_unique_user_fields, duplicate_key_error

router = APIRouter()


@router.post("/login")
def login(body: LoginRequest, db=Depends(get_db)):
    """Login → dapat JWT token"""
    user = db["users"].find_one({"username": body.username})

    if not user or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Username atau password salah.")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Akun Anda dinonaktifkan.")

    token = create_access_token({"sub": str(user["_id"]), "role": user["role"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserOut.from_doc(user)
    }


@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    """Data user yang sedang login"""
    return UserOut.from_doc(current_user)


@router.post("/register")
def register(body: UserCreate, db=Depends(get_db)):
    """Daftar akun baru (role selalu 'user')"""
    ensure_unique_user_fields(db, body.model_dump())

    doc = {
        "name": body.name,
        "username": body.username,
        "email": body.email,
        "nik": body.nik,
        "hashed_password": hash_password(body.password),
        "role": "user",
        "is_active": True,
        "face_encoding": None,
        "created_at": datetime.utcnow(),
        "updated_at": None,
    }
    try:
        result = db["users"].insert_one(doc)
    except DuplicateKeyError as e:
        raise duplicate_key_error(e)
    doc["_id"] = result.inserted_id
    return UserOut.from_doc(doc)
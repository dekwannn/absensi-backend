from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    admin = "admin"
    user = "user"


# ─── Auth ─────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


# ─── User ─────────────────────────────────────────────────
class UserCreate(BaseModel):
    name: str
    username: str
    password: str
    email: Optional[str] = None
    nik: Optional[str] = None
    role: UserRole = UserRole.user

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    nik: Optional[str] = None
    password: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

class UserOut(BaseModel):
    id: str
    name: str
    username: str
    email: Optional[str] = None
    nik: Optional[str] = None
    role: str
    is_active: bool
    has_face: bool = False
    created_at: Optional[datetime] = None

    @classmethod
    def from_doc(cls, doc: dict) -> "UserOut":
        return cls(
            id=str(doc["_id"]),
            name=doc["name"],
            username=doc["username"],
            email=doc.get("email"),
            nik=doc.get("nik"),
            role=doc.get("role", "user"),
            is_active=doc.get("is_active", True),
            has_face=doc.get("face_encoding") is not None,
            created_at=doc.get("created_at"),
        )

TokenResponse.model_rebuild()
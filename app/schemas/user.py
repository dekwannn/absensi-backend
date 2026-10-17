from pydantic import BaseModel, Field, field_validator
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
PASSWORD_MIN = 6  # samakan dengan validasi di frontend


class _UserFields(BaseModel):
    @field_validator("name", "username", "email", "nik", mode="before", check_fields=False)
    @classmethod
    def strip_text(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("email", "nik", check_fields=False)
    @classmethod
    def empty_to_none(cls, v):
        # string kosong disimpan sebagai None agar tidak bentrok dengan unique index
        return v or None


class UserCreate(_UserFields):
    name: str = Field(min_length=1)
    username: str = Field(min_length=1)
    password: str = Field(min_length=PASSWORD_MIN)
    email: Optional[str] = None
    nik: Optional[str] = None
    role: UserRole = UserRole.user

class UserUpdate(_UserFields):
    name: Optional[str] = Field(default=None, min_length=1)
    email: Optional[str] = None
    nik: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=PASSWORD_MIN)
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
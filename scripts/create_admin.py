"""
Buat akun admin baru (mis. admin pertama setelah database dikosongkan).
Pendaftaran lewat /auth/register selalu menghasilkan role 'user',
jadi admin pertama harus dibuat lewat skrip ini.

Jalankan dari root proyek:
    python -m scripts.create_admin
"""
import sys
from datetime import datetime
from getpass import getpass

from fastapi import HTTPException
from pydantic import ValidationError
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

from app.core.config import settings
from app.db.mongo import ensure_indexes
from app.schemas.user import UserCreate, UserRole
from app.services.auth_service import hash_password
from app.services.user_service import ensure_unique_user_fields


def main():
    client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
    except ServerSelectionTimeoutError:
        sys.exit("MongoDB tidak bisa dihubungi. Pastikan service MongoDB sudah berjalan.")
    db = client[settings.DB_NAME]
    ensure_indexes(db)

    print(f"Membuat admin baru di database {settings.DB_NAME}")
    name = input("Nama lengkap : ").strip()
    username = input("Username     : ").strip()
    email = input("Email (opsional, Enter untuk lewati): ").strip()
    password = getpass("Password (min. 6 karakter, tidak terlihat saat diketik): ")
    if getpass("Ulangi password: ") != password:
        sys.exit("Password tidak sama. Tidak ada yang dibuat.")

    try:
        body = UserCreate(name=name, username=username, email=email, password=password, role=UserRole.admin)
        ensure_unique_user_fields(db, body.model_dump())
    except ValidationError as e:
        sys.exit("Data tidak valid: " + "; ".join(f"{err['loc'][-1]}: {err['msg']}" for err in e.errors()))
    except HTTPException as e:
        sys.exit(e.detail)

    db["users"].insert_one({
        "name": body.name,
        "username": body.username,
        "email": body.email,
        "nik": None,
        "hashed_password": hash_password(body.password),
        "role": "admin",
        "is_active": True,
        "face_encoding": None,
        "created_at": datetime.utcnow(),
        "updated_at": None,
    })
    print(f"Admin '{body.username}' berhasil dibuat. Silakan login di aplikasi.")
    client.close()


if __name__ == "__main__":
    main()

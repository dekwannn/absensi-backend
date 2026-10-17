from typing import Optional

from bson import ObjectId
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

DUPLICATE_MESSAGES = {
    "username": "Username sudah digunakan.",
    "email": "Email sudah digunakan.",
    "nik": "NIK sudah digunakan.",
}


def ensure_unique_user_fields(db, values: dict, exclude_id: Optional[ObjectId] = None):
    """Tolak (400) jika username/email/nik sudah dipakai user lain. Nilai None dilewati."""
    for field, message in DUPLICATE_MESSAGES.items():
        value = values.get(field)
        if value is None:
            continue
        query = {field: value}
        if exclude_id is not None:
            query["_id"] = {"$ne": exclude_id}
        if db["users"].find_one(query, {"_id": 1}):
            raise HTTPException(status_code=400, detail=message)


def duplicate_key_error(e: DuplicateKeyError) -> HTTPException:
    """
    Cadangan bila dua request lolos pengecekan bersamaan:
    unique index menolak, ubah jadi pesan yang sama seperti di atas.
    """
    fields = (e.details or {}).get("keyPattern", {})
    for field in fields:
        if field in DUPLICATE_MESSAGES:
            return HTTPException(status_code=400, detail=DUPLICATE_MESSAGES[field])
    return HTTPException(status_code=400, detail="Data sudah digunakan.")

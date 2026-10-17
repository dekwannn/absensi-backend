from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from datetime import datetime
from bson import ObjectId

from app.db.mongo import get_db
from app.schemas.user import UserCreate, UserUpdate, UserOut
from app.services.auth_service import get_current_user, require_admin
from app.services.face_logic import FaceService

router = APIRouter()


@router.get("")
def list_users(db=Depends(get_db), _: dict = Depends(require_admin)):
    """[Admin] Lihat semua user"""
    users = list(db["users"].find().sort("created_at", -1))
    return [UserOut.from_doc(u) for u in users]


@router.get("/{user_id}")
def get_user(user_id: str, db=Depends(get_db), _: dict = Depends(require_admin)):
    """[Admin] Detail user"""
    user = db["users"].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")
    return UserOut.from_doc(user)


@router.post("")
def create_user(body: UserCreate, db=Depends(get_db), _: dict = Depends(require_admin)):
    """[Admin] Buat user baru"""
    if db["users"].find_one({"username": body.username}):
        raise HTTPException(status_code=400, detail="Username sudah digunakan.")

    from app.services.auth_service import hash_password
    doc = {
        "name": body.name,
        "username": body.username,
        "email": body.email,
        "nik": body.nik,
        "hashed_password": hash_password(body.password),
        "role": body.role,
        "is_active": True,
        "face_encoding": None,
        "created_at": datetime.utcnow(),
        "updated_at": None,
    }
    result = db["users"].insert_one(doc)
    doc["_id"] = result.inserted_id
    return UserOut.from_doc(doc)


@router.put("/{user_id}")
def update_user(user_id: str, body: UserUpdate, db=Depends(get_db), _: dict = Depends(require_admin)):
    """[Admin] Update data user"""
    user = db["users"].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")

    updates = {}
    if body.name is not None:       updates["name"] = body.name
    if body.email is not None:      updates["email"] = body.email
    if body.nik is not None:        updates["nik"] = body.nik
    if body.role is not None:       updates["role"] = body.role
    if body.is_active is not None:  updates["is_active"] = body.is_active
    if body.password is not None:
        from app.services.auth_service import hash_password
        updates["hashed_password"] = hash_password(body.password)

    if updates:
        updates["updated_at"] = datetime.utcnow()
        db["users"].update_one({"_id": ObjectId(user_id)}, {"$set": updates})

    updated = db["users"].find_one({"_id": ObjectId(user_id)})
    return UserOut.from_doc(updated)


@router.delete("/{user_id}")
def delete_user(user_id: str, db=Depends(get_db), current_user: dict = Depends(require_admin)):
    """[Admin] Hapus user"""
    if str(current_user["_id"]) == user_id:
        raise HTTPException(status_code=400, detail="Tidak bisa menghapus akun sendiri.")

    user = db["users"].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")

    db["users"].delete_one({"_id": ObjectId(user_id)})
    return {"status": "success", "message": f"User {user['name']} berhasil dihapus."}


# ── Face Enrollment ───────────────────────────────────

@router.post("/{user_id}/enroll-face")
def enroll_face(
    user_id: str,
    file: UploadFile = File(...),
    db=Depends(get_db),
    _: dict = Depends(require_admin)
):
    """[Admin] Daftarkan wajah user"""
    user = db["users"].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")

    encoding = FaceService.process_image(file)
    if encoding is None:
        raise HTTPException(status_code=400, detail="Wajah tidak terdeteksi pada foto.")

    db["users"].update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"face_encoding": FaceService.encoding_to_db(encoding), "updated_at": datetime.utcnow()}}
    )
    return {"status": "success", "message": f"Wajah {user['name']} berhasil didaftarkan."}


@router.delete("/{user_id}/enroll-face")
def remove_face(user_id: str, db=Depends(get_db), _: dict = Depends(require_admin)):
    """[Admin] Hapus data wajah user"""
    user = db["users"].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")

    db["users"].update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"face_encoding": None, "updated_at": datetime.utcnow()}}
    )
    return {"status": "success", "message": "Data wajah berhasil dihapus."}
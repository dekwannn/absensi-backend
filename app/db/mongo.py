from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.database import Database
from app.core.config import settings

MONGO_URI = settings.MONGO_URI
DB_NAME = settings.DB_NAME

client: MongoClient = None
db: Database = None

def connect_db():
    global client, db
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    print(f"✅ MongoDB connected: {DB_NAME}")
    ensure_indexes(db)

def disconnect_db():
    global client
    if client:
        client.close()
        print("🔌 MongoDB disconnected")

def get_db() -> Database:
    return db


# email & nik boleh kosong → unik hanya untuk yang berisi string
_ONLY_STRINGS = lambda field: {"partialFilterExpression": {field: {"$type": "string"}}}

INDEXES = [
    ("users",       [("username", ASCENDING)],                  {"unique": True}),
    ("users",       [("email", ASCENDING)],                     {"unique": True, **_ONLY_STRINGS("email")}),
    ("users",       [("nik", ASCENDING)],                       {"unique": True, **_ONLY_STRINGS("nik")}),
    # satu record absensi per user per hari; juga mencegah double check-in bersamaan
    ("attendances", [("user_id", ASCENDING), ("date", DESCENDING)], {"unique": True}),
    ("attendances", [("date", DESCENDING)],                     {}),
]

def ensure_indexes(database: Database):
    """Buat index jika belum ada. Gagal (mis. data duplikat lama) tidak menghentikan server."""
    for collection, keys, options in INDEXES:
        try:
            database[collection].create_index(keys, **options)
        except Exception as e:
            fields = ", ".join(k for k, _ in keys)
            print(f"⚠️  Gagal membuat index {collection}({fields}): {e}")


def to_object_id(value: str, not_found_detail: str = "Data tidak ditemukan.") -> ObjectId:
    """ID dari URL → ObjectId. Format salah dianggap tidak ditemukan (404), bukan error 500."""
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail=not_found_detail)

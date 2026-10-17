from pymongo import MongoClient
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

def disconnect_db():
    global client
    if client:
        client.close()
        print("🔌 MongoDB disconnected")

def get_db() -> Database:
    return db

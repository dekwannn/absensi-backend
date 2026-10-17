"""
Kosongkan database aplikasi (semua user & absensi) untuk mulai dari awal.
PERMANEN — data tidak bisa dikembalikan.

Jalankan dari root proyek:
    python -m scripts.reset_db

Skrip menampilkan isi database lalu meminta Anda mengetik nama database
sebagai konfirmasi. Setelah itu buat admin baru dengan:
    python -m scripts.create_admin
"""
import sys

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

from app.core.config import settings
from app.db.mongo import ensure_indexes


def main():
    client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
    except ServerSelectionTimeoutError:
        sys.exit("MongoDB tidak bisa dihubungi. Pastikan service MongoDB sudah berjalan.")

    db = client[settings.DB_NAME]
    collections = db.list_collection_names()
    print(f"Database: {settings.DB_NAME}")
    if not collections:
        print("Database sudah kosong. Langkah berikutnya: python -m scripts.create_admin")
        return
    for name in sorted(collections):
        print(f"  {name}: {db[name].count_documents({})} dokumen")

    print("\nSEMUA data di atas akan DIHAPUS PERMANEN.")
    answer = input(f"Ketik nama database ({settings.DB_NAME}) untuk melanjutkan: ").strip()
    if answer != settings.DB_NAME:
        sys.exit("Dibatalkan. Tidak ada yang dihapus.")

    client.drop_database(settings.DB_NAME)
    ensure_indexes(client[settings.DB_NAME])
    print(f"Database {settings.DB_NAME} sudah dikosongkan.")
    print("Langkah berikutnya: python -m scripts.create_admin")
    client.close()


if __name__ == "__main__":
    main()

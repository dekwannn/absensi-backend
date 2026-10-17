"""
Migrasi face_encoding lama (bytes hasil pickle.dumps numpy array) → list float.

Jalankan SEKALI dari root proyek:
    python -m scripts.migrate_face_encoding           # dry-run: hanya laporan
    python -m scripts.migrate_face_encoding --apply   # benar-benar menulis ke DB

Data lama dibaca dengan unpickler terbatas yang hanya mengizinkan kelas numpy
untuk membangun array, jadi isi pickle lain (yang bisa menjalankan kode) ditolak.
"""
import io
import pickle
import sys

from app.core.config import settings
from app.services.face_logic import ENCODING_SIZE, FaceService
from pymongo import MongoClient

ALLOWED = {
    ("numpy", "ndarray"),
    ("numpy", "dtype"),
    ("numpy.core.multiarray", "_reconstruct"),
    ("numpy._core.multiarray", "_reconstruct"),
    ("numpy.core.multiarray", "scalar"),
    ("numpy._core.multiarray", "scalar"),
}


class NumpyOnlyUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if (module, name) in ALLOWED:
            return super().find_class(module, name)
        raise pickle.UnpicklingError(f"kelas tidak diizinkan: {module}.{name}")


def load_legacy(data: bytes) -> list:
    arr = NumpyOnlyUnpickler(io.BytesIO(data)).load()
    enc = FaceService.encoding_to_db(arr)
    if len(enc) != ENCODING_SIZE:
        raise ValueError(f"panjang encoding {len(enc)}, seharusnya {ENCODING_SIZE}")
    return enc


def main(apply: bool):
    client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
    users = client[settings.DB_NAME]["users"]

    converted, failed = 0, []
    for u in users.find({"face_encoding": {"$type": "binData"}}, {"username": 1, "face_encoding": 1}):
        try:
            enc = load_legacy(bytes(u["face_encoding"]))
        except Exception as e:
            failed.append((u.get("username"), str(e)))
            continue
        if apply:
            users.update_one({"_id": u["_id"]}, {"$set": {"face_encoding": enc}})
        converted += 1

    mode = "DIUBAH" if apply else "akan diubah (dry-run)"
    print(f"{converted} user {mode}.")
    for username, err in failed:
        print(f"  GAGAL {username}: {err} -> daftarkan ulang wajahnya lewat admin")
    if not apply and converted:
        print("Jalankan lagi dengan --apply untuk menyimpan perubahan.")
    client.close()


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)

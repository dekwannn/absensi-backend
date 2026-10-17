import io
import logging

import face_recognition
import numpy as np
from fastapi import UploadFile

logger = logging.getLogger(__name__)

ENCODING_SIZE = 128  # panjang encoding dari face_recognition


class FaceService:

    @staticmethod
    def encoding_to_db(encoding) -> list:
        """numpy array → list float biasa, aman disimpan di MongoDB."""
        return [float(x) for x in encoding]

    @staticmethod
    def encoding_from_db(value):
        """
        Baca encoding dari MongoDB. Hanya menerima list angka (format baru).
        Data lama hasil pickle (bytes) TIDAK di-unpickle di sini demi keamanan —
        konversi dulu dengan scripts/migrate_face_encoding.py.
        """
        if not isinstance(value, list) or len(value) != ENCODING_SIZE:
            if value is not None:
                logger.warning("face_encoding format tidak dikenal (%s), perlu migrasi/daftar ulang",
                               type(value).__name__)
            return None
        return np.array(value, dtype=np.float64)

    @staticmethod
    def process_image(file: UploadFile):
        """
        Hitung encoding wajah dari foto yang diupload.
        Sinkron & berat di CPU — panggil dari endpoint `def` biasa
        (FastAPI menjalankannya di threadpool, jadi server tidak macet).
        Foto diproses langsung di memori, tanpa file sementara,
        sehingga upload dari beberapa user sekaligus tidak saling tertimpa.
        """
        contents = file.file.read()
        logger.debug("Face upload: content_type=%s size=%d", file.content_type, len(contents))

        if not contents:
            logger.info("File foto kosong")
            return None

        try:
            image = face_recognition.load_image_file(io.BytesIO(contents))
            encodings = face_recognition.face_encodings(image)
        except Exception:
            logger.exception("Gagal memproses foto wajah")
            return None

        logger.debug("Total wajah terdeteksi: %d", len(encodings))
        if not encodings:
            return None
        return encodings[0]

    @staticmethod
    def compare_face(known_encoding, unknown_encoding, tolerance=0.5):
        if known_encoding is None or unknown_encoding is None:
            return False

        try:
            distance = face_recognition.face_distance(
                [np.array(known_encoding)],
                np.array(unknown_encoding)
            )[0]
        except Exception:
            logger.exception("Gagal membandingkan wajah")
            return False

        logger.debug("Face distance: %.4f (tolerance %.2f)", distance, tolerance)
        return distance <= tolerance

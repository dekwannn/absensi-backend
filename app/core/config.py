from datetime import time
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# .env selalu dicari di root proyek, tidak tergantung dari folder mana uvicorn dijalankan
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "GeoFace Attendance API"

    # ─── MongoDB ──────────────────────────────────────────
    MONGO_URI: str = "mongodb://localhost:27017"
    DB_NAME: str = "geoface_db"

    # ─── JWT ──────────────────────────────────────────────
    SECRET_KEY: str  # wajib diisi di .env
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 jam

    # ─── Lokasi kantor ────────────────────────────────────
    OFFICE_LAT: float = -8.11405
    OFFICE_LON: float = 115.13409
    MAX_RADIUS: float = 100  # meter

    # ─── Jam kerja (WITA, format HH:MM) ──────────────────
    CHECKIN_OPEN: time = time(7, 0)      # absen masuk mulai dibuka
    CHECKIN_ON_TIME: time = time(8, 0)   # ≤ jam ini → tepat waktu
    CHECKIN_CLOSE: time = time(9, 0)     # absen masuk ditutup

    CHECKOUT_OPEN: time = time(16, 30)   # baru bisa check-out
    CHECKOUT_NORMAL: time = time(17, 0)  # ≥ jam ini → pulang normal
    CHECKOUT_CLOSE: time = time(21, 0)   # check-out ditutup

    @model_validator(mode="after")
    def check_schedule_order(self):
        if not (self.CHECKIN_OPEN <= self.CHECKIN_ON_TIME <= self.CHECKIN_CLOSE):
            raise ValueError("Urutan jam check-in harus OPEN <= ON_TIME <= CLOSE")
        if not (self.CHECKOUT_OPEN <= self.CHECKOUT_NORMAL <= self.CHECKOUT_CLOSE):
            raise ValueError("Urutan jam check-out harus OPEN <= NORMAL <= CLOSE")
        return self


settings = Settings()

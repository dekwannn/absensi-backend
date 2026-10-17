from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.db.mongo import get_db
from app.services.face_logic import FaceService
from app.services.geo_logic import GeoService
from app.services.auth_service import get_current_user, require_admin

router = APIRouter()

OFFICE_LAT = settings.OFFICE_LAT
OFFICE_LON = settings.OFFICE_LON
MAX_RADIUS = settings.MAX_RADIUS

WITA = timezone(timedelta(hours=8))

# ═══════════════════════════════════════════════════════════
# ATURAN JAM KERJA (WITA) — atur lewat .env, lihat app/core/config.py
# ═══════════════════════════════════════════════════════════
CHECKIN_OPEN     = settings.CHECKIN_OPEN     # absen masuk mulai dibuka
CHECKIN_ON_TIME  = settings.CHECKIN_ON_TIME  # ≤ jam ini → tepat waktu
CHECKIN_CLOSE    = settings.CHECKIN_CLOSE    # absen masuk ditutup

CHECKOUT_OPEN    = settings.CHECKOUT_OPEN    # baru bisa check-out
CHECKOUT_NORMAL  = settings.CHECKOUT_NORMAL  # ≥ jam ini → pulang normal
CHECKOUT_CLOSE   = settings.CHECKOUT_CLOSE   # check-out ditutup


def to_wita(dt):
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(WITA).isoformat()


def get_checkin_status(now: datetime) -> dict:
    """Return status check-in berdasarkan jam sekarang (WITA)"""
    t = now.time().replace(second=0, microsecond=0, tzinfo=None)

    if t < CHECKIN_OPEN:
        return {
            "can": False,
            "status": "too_early",
            "label": f"Absen masuk belum dibuka. Buka pukul {CHECKIN_OPEN.strftime('%H:%M')}."
        }
    if t > CHECKIN_CLOSE:
        return {
            "can": False,
            "status": "closed",
            "label": f"Absen masuk sudah ditutup sejak pukul {CHECKIN_CLOSE.strftime('%H:%M')}."
        }
    if t <= CHECKIN_ON_TIME:
        return {
            "can": True,
            "status": "on_time",
            "label": "Tepat Waktu"
        }

    # 08:01 – 09:00 → terlambat
    deadline = now.replace(
        hour=CHECKIN_ON_TIME.hour,
        minute=CHECKIN_ON_TIME.minute,
        second=0, microsecond=0
    )
    minutes_late = int((now - deadline).total_seconds() / 60)
    return {
        "can": True,
        "status": "late",
        "label": f"Terlambat {minutes_late} menit"
    }


def get_checkout_status(now: datetime) -> dict:
    """Return status check-out berdasarkan jam sekarang (WITA)"""
    t = now.time().replace(second=0, microsecond=0, tzinfo=None)

    if t < CHECKOUT_OPEN:
        return {
            "can": False,
            "status": "too_early",
            "label": f"Belum bisa pulang. Minimal pukul {CHECKOUT_OPEN.strftime('%H:%M')}."
        }
    if t > CHECKOUT_CLOSE:
        return {
            "can": False,
            "status": "closed",
            "label": f"Check-out sudah ditutup sejak pukul {CHECKOUT_CLOSE.strftime('%H:%M')}."
        }
    if t >= CHECKOUT_NORMAL:
        return {
            "can": True,
            "status": "normal",
            "label": "Pulang Normal"
        }

    # 16:30 – 16:59 → pulang lebih awal
    normal_time = now.replace(
        hour=CHECKOUT_NORMAL.hour,
        minute=CHECKOUT_NORMAL.minute,
        second=0, microsecond=0
    )
    minutes_early = int((normal_time - now).total_seconds() / 60)
    return {
        "can": True,
        "status": "early",
        "label": f"Pulang {minutes_early} menit lebih awal"
    }


def _fmt(a):
    return {
        "id": str(a["_id"]),
        "user_id": a["user_id"],
        "username": a.get("username"),
        "date": a["date"],
        "check_in": to_wita(a.get("check_in_time")),
        "check_out": to_wita(a.get("check_out_time")),
        # lokasi check-in (nama field lama dipertahankan agar data lama tetap terbaca)
        "latitude": a.get("latitude"),
        "longitude": a.get("longitude"),
        "distance": a.get("distance"),
        "checkout_latitude": a.get("checkout_latitude"),
        "checkout_longitude": a.get("checkout_longitude"),
        "checkout_distance": a.get("checkout_distance"),
        "checkin_status": a.get("checkin_status"),
        "checkin_label": a.get("checkin_label"),
        "checkout_status": a.get("checkout_status"),
        "checkout_label": a.get("checkout_label"),
        "status": a.get("status"),
    }


# ═══════════════════════════════════════════════════════════
# CHECK-IN
# ═══════════════════════════════════════════════════════════

@router.post("/check-in")
def check_in(
    file: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    try:
        now = datetime.now(WITA)
        today_str = now.strftime("%Y-%m-%d")

        # 1. Cek jam — boleh check-in sekarang?
        time_check = get_checkin_status(now)
        if not time_check["can"]:
            return JSONResponse(status_code=400, content={
                "status": "error",
                "detail": time_check["label"]
            })

        # 2. Validasi Lokasi
        is_valid_loc, distance = GeoService.is_within_radius(
            latitude, longitude, OFFICE_LAT, OFFICE_LON, MAX_RADIUS
        )
        if not is_valid_loc:
            return JSONResponse(status_code=400, content={
                "status": "error",
                "detail": f"Jarak Anda: {int(distance)}m. Maksimal: {MAX_RADIUS}m."
            })

        # 3. Cek sudah check-in hari ini
        existing = db["attendances"].find_one({
            "user_id": str(current_user["_id"]),
            "date": today_str
        })
        if existing:
            return JSONResponse(status_code=400, content={
                "status": "error", "detail": "Anda sudah check-in hari ini."
            })

        # 4. Cek wajah terdaftar
        if not current_user.get("face_encoding"):
            return JSONResponse(status_code=400, content={
                "status": "error", "detail": "Wajah Anda belum didaftarkan. Hubungi admin."
            })
        known_encoding = FaceService.encoding_from_db(current_user["face_encoding"])
        if known_encoding is None:
            return JSONResponse(status_code=400, content={
                "status": "error", "detail": "Data wajah Anda perlu didaftarkan ulang. Hubungi admin."
            })

        # 5. Validasi Wajah
        unknown_encoding = FaceService.process_image(file)
        if unknown_encoding is None:
            return JSONResponse(status_code=400, content={
                "status": "error", "detail": "Wajah tidak terdeteksi."
            })

        if not FaceService.compare_face(known_encoding, unknown_encoding):
            return JSONResponse(status_code=400, content={
                "status": "error", "detail": "Wajah tidak cocok dengan akun Anda."
            })

        # 6. Simpan ke Database
        db["attendances"].insert_one({
            "user_id": str(current_user["_id"]),
            "username": current_user.get("username", "Unknown"),
            "date": today_str,
            "check_in_time": now,
            "check_out_time": None,
            "latitude": latitude,
            "longitude": longitude,
            "distance": distance,
            "checkout_latitude": None,
            "checkout_longitude": None,
            "checkout_distance": None,
            "checkin_status": time_check["status"],
            "checkin_label": time_check["label"],
            "checkout_status": None,
            "checkout_label": None,
            "status": "present",
            "created_at": now,
        })

        return {
            "status": "success",
            "message": "Check-in berhasil",
            "user": current_user["name"],
            "user_id": str(current_user["_id"]),
            "time": now.isoformat(),
            "checkin_status": time_check["status"],
            "checkin_label": time_check["label"],
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})


# ═══════════════════════════════════════════════════════════
# CHECK-OUT
# ═══════════════════════════════════════════════════════════

@router.post("/check-out")
def check_out(
    file: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    try:
        now = datetime.now(WITA)
        today_str = now.strftime("%Y-%m-%d")

        # 1. Cek jam — boleh check-out sekarang?
        time_check = get_checkout_status(now)
        if not time_check["can"]:
            return JSONResponse(status_code=400, content={
                "status": "error",
                "detail": time_check["label"]
            })

        # 2. Validasi Lokasi
        is_valid_loc, distance = GeoService.is_within_radius(
            latitude, longitude, OFFICE_LAT, OFFICE_LON, MAX_RADIUS
        )
        if not is_valid_loc:
            return JSONResponse(status_code=400, content={
                "status": "error",
                "detail": f"Jarak Anda: {int(distance)}m. Maksimal: {MAX_RADIUS}m."
            })

        # 3. Cek wajah terdaftar
        if not current_user.get("face_encoding"):
            return JSONResponse(status_code=400, content={
                "status": "error", "detail": "Wajah Anda belum didaftarkan."
            })
        known_encoding = FaceService.encoding_from_db(current_user["face_encoding"])
        if known_encoding is None:
            return JSONResponse(status_code=400, content={
                "status": "error", "detail": "Data wajah Anda perlu didaftarkan ulang. Hubungi admin."
            })

        # 4. Validasi Wajah
        unknown_encoding = FaceService.process_image(file)
        if unknown_encoding is None:
            return JSONResponse(status_code=400, content={
                "status": "error", "detail": "Wajah tidak terdeteksi."
            })

        if not FaceService.compare_face(known_encoding, unknown_encoding):
            return JSONResponse(status_code=400, content={
                "status": "error", "detail": "Wajah tidak cocok dengan akun Anda."
            })

        # 5. Cari attendance hari ini
        record = db["attendances"].find_one({
            "user_id": str(current_user["_id"]),
            "date": today_str
        })
        if not record:
            return JSONResponse(status_code=400, content={
                "status": "error", "detail": "Anda belum check-in hari ini."
            })
        if record.get("check_out_time"):
            waktu = to_wita(record["check_out_time"])
            return JSONResponse(status_code=400, content={
                "status": "error", "detail": f"Anda sudah check-out pukul {waktu[11:16]}."
            })

        # 6. Update check-out
        db["attendances"].update_one(
            {"_id": record["_id"]},
            {"$set": {
                "check_out_time": now,
                "checkout_latitude": latitude,
                "checkout_longitude": longitude,
                "checkout_distance": distance,
                "checkout_status": time_check["status"],
                "checkout_label": time_check["label"],
            }}
        )

        return {
            "status": "success",
            "message": "Check-out berhasil",
            "user": current_user["name"],
            "user_id": str(current_user["_id"]),
            "time": now.isoformat(),
            "checkout_status": time_check["status"],
            "checkout_label": time_check["label"],
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})


# ═══════════════════════════════════════════════════════════
# HISTORY & TODAY
# ═══════════════════════════════════════════════════════════

@router.get("/attendance/my-history")
def my_history(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    records = list(
        db["attendances"]
        .find({"user_id": str(current_user["_id"])})
        .sort("date", -1)
    )
    return {"status": "success", "data": [_fmt(r) for r in records]}


@router.get("/attendance/today")
def today_status(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    today_str = datetime.now(WITA).strftime("%Y-%m-%d")
    record = db["attendances"].find_one({
        "user_id": str(current_user["_id"]),
        "date": today_str
    })

    # Kirim juga info jadwal ke frontend
    schedule = {
        "checkin_open":    CHECKIN_OPEN.strftime("%H:%M"),
        "checkin_on_time": CHECKIN_ON_TIME.strftime("%H:%M"),
        "checkin_close":   CHECKIN_CLOSE.strftime("%H:%M"),
        "checkout_open":   CHECKOUT_OPEN.strftime("%H:%M"),
        "checkout_normal": CHECKOUT_NORMAL.strftime("%H:%M"),
        "checkout_close":  CHECKOUT_CLOSE.strftime("%H:%M"),
    }

    return {
        "status": "success",
        "data": _fmt(record) if record else None,
        "schedule": schedule
    }


# ═══════════════════════════════════════════════════════════
# ADMIN
# ═══════════════════════════════════════════════════════════

@router.get("/attendance")
def get_all(db=Depends(get_db), _: dict = Depends(require_admin)):
    records = list(db["attendances"].find().sort("date", -1))
    return {"status": "success", "data": [_fmt(r) for r in records]}


@router.get("/attendance/user/{user_id}")
def user_history(user_id: str, db=Depends(get_db), _: dict = Depends(require_admin)):
    records = list(
        db["attendances"]
        .find({"user_id": user_id})
        .sort("date", -1)
    )
    return {"status": "success", "data": [_fmt(r) for r in records]}
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.db.mongo import connect_db, disconnect_db
from app.api.v1.router import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    connect_db()   
    yield
    disconnect_db()  


app = FastAPI(
    title="GeoFace Attendance API",
    description="Sistem Absensi Face Recognition & Geolocation",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


FIELD_LABELS = {"name": "Nama", "username": "Username", "password": "Password",
                "email": "Email", "nik": "NIK", "file": "Foto"}


def _validation_message(err: dict) -> str:
    field = str(err["loc"][-1]) if err.get("loc") else "data"
    label = FIELD_LABELS.get(field, field.replace("_", " ").capitalize())
    ctx = err.get("ctx") or {}
    if err["type"] == "missing":
        return f"{label} wajib diisi."
    if err["type"] == "string_too_short":
        min_length = ctx.get("min_length", 1)
        return f"{label} wajib diisi." if min_length == 1 else f"{label} minimal {min_length} karakter."
    return f"{label}: {err['msg']}"


@app.exception_handler(RequestValidationError)
def validation_error_handler(request: Request, exc: RequestValidationError):
    # frontend menampilkan `detail` sebagai teks, jadi kirim string, bukan list objek
    detail = " ".join(_validation_message(e) for e in exc.errors())
    return JSONResponse(status_code=422, content={"status": "error", "detail": detail})


@app.get("/")
def root():
    return {"message": "GeoFace API v2.0 running 🚀"}
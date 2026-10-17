from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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


@app.get("/")
def root():
    return {"message": "GeoFace API v2.0 running 🚀"}
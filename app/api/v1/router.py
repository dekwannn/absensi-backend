from fastapi import APIRouter
from app.api.v1.endpoints import attendance, auth, users

router = APIRouter()

router.include_router(auth.router,       prefix="/auth",  tags=["Auth"])
router.include_router(users.router,      prefix="/users", tags=["Users"])
router.include_router(attendance.router, prefix="",       tags=["Attendance"])
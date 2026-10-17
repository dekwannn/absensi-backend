# Entry point alternatif agar `uvicorn main:app` tetap jalan.
# Aplikasi sebenarnya ada di app/main.py.
from app.main import app  # noqa: F401

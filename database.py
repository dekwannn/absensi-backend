# database.py
from sqlalchemy import create_engine, Column, Integer, String, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Menggunakan SQLite lokal
DATABASE_URL = "sqlite:///./absensi.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Model User
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    role = Column(String) # Misal: Karyawan, Admin
    # Kita simpan encoding wajah sebagai BYTES (Pickle)
    face_encoding = Column(LargeBinary) 

# Buat tabel otomatis saat file ini dijalankan/diimport
Base.metadata.create_all(bind=engine)
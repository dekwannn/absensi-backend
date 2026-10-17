from sqlalchemy import Column, Integer, ForeignKey, DateTime, Float, String, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base

class Attendance(Base):
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True, index=True)
    
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User")

    date = Column(Date, default=datetime.utcnow)

    check_in_time = Column(DateTime, nullable=True)
    check_out_time = Column(DateTime, nullable=True)

    status = Column(String, default="present")

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    distance = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

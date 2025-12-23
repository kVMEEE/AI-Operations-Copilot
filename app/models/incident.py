from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from app.core.database import Base

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    severity = Column(String)
    status = Column(String, default="open")
    source = Column(String)  # logs | metrics | alerts
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Text
from datetime import datetime
from app.db.session import Base

class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    answer_found = Column(Boolean, nullable=False)
    response_time_ms = Column(Float, nullable=False)
    source_chunks = Column(Text, nullable=False)  # JSON-encoded array of source metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./wellness_tracker.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    url = Column(String, unique=True, index=True)
    description = Column(Text)
    business_model = Column(String)       # subscription | freemium | one-time | marketplace | B2B | unknown
    ai_usage = Column(Boolean, default=False)
    ai_details = Column(Text)             # what AI is used for
    location = Column(String, default="California")
    scan_date = Column(DateTime, default=datetime.utcnow)
    raw_snippet = Column(Text)


class ScanLog(Base):
    __tablename__ = "scan_logs"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    results_found = Column(Integer, default=0)
    status = Column(String, default="running")   # running | completed | failed
    error = Column(Text)


def create_tables():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

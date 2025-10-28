# src/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import settings

# For SQLite, need connect_args
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency helper (FastAPI later)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

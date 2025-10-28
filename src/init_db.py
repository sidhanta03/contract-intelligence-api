# src/init_db.py
from src.config import Base
from src.db import engine
import src.models.documents  # import models so they are registered on Base metadata

def init_db():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Done. Tables created.")

if __name__ == "__main__":
    init_db()

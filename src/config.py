# src/config.py
from sqlalchemy.ext.declarative import declarative_base
from pydantic_settings import BaseSettings
import os

Base = declarative_base()

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./contracts.db")

settings = Settings()

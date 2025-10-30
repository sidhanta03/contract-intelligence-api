# src/config.py
from sqlalchemy.ext.declarative import declarative_base
from pydantic_settings import BaseSettings
from typing import Optional
import os

Base = declarative_base()

class Settings(BaseSettings):
    # Database Configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite:///./contracts.db"
    )
    
    # PostgreSQL specific settings
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "contract_intelligence")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "contract_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "contract_password")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    
    # Database Pool Settings
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "3600"))
    
    # Application Settings
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    
    # API Keys
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

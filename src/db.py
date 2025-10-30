# src/db.py
from sqlalchemy import create_engine, event, pool, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from src.config import settings
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Determine if we're using PostgreSQL or SQLite
is_postgres = settings.DATABASE_URL.startswith("postgresql")
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# Configure engine parameters based on database type
engine_kwargs = {
    "echo": settings.ENVIRONMENT == "development",
}

if is_postgres:
    # PostgreSQL specific configuration
    engine_kwargs.update({
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
        "pool_recycle": settings.DB_POOL_RECYCLE,
        "pool_pre_ping": True,  # Enable connection health checks
        "poolclass": pool.QueuePool,
    })
    logger.info("Configuring PostgreSQL engine with connection pooling")
elif is_sqlite:
    # SQLite specific configuration
    engine_kwargs.update({
        "connect_args": {"check_same_thread": False},
        "poolclass": pool.StaticPool,
    })
    logger.info("Configuring SQLite engine")

# Create engine
engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

# Add connection event listeners for PostgreSQL
if is_postgres:
    @event.listens_for(engine, "connect")
    def receive_connect(dbapi_conn, connection_record):
        """Set connection parameters on connect"""
        connection_record.info['pid'] = dbapi_conn.get_backend_pid()
        logger.debug(f"New connection established: PID {connection_record.info['pid']}")
    
    @event.listens_for(engine, "checkout")
    def receive_checkout(dbapi_conn, connection_record, connection_proxy):
        """Log connection checkout"""
        logger.debug(f"Connection checked out: PID {connection_record.info.get('pid')}")

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Dependency for FastAPI to get database session.
    Includes retry logic for handling temporary connection issues.
    """
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        db = SessionLocal()
        try:
            # Test the connection
            db.execute(text("SELECT 1"))
            yield db
            return
        except OperationalError as e:
            db.close()
            if attempt < max_retries - 1:
                logger.warning(
                    f"Database connection failed (attempt {attempt + 1}/{max_retries}): {e}"
                )
                time.sleep(retry_delay)
            else:
                logger.error(f"Database connection failed after {max_retries} attempts: {e}")
                raise
        except Exception as e:
            db.close()
            logger.error(f"Unexpected database error: {e}")
            raise
        finally:
            if db:
                db.close()

def check_db_connection():
    """
    Check if database connection is working.
    Returns True if successful, False otherwise.
    """
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False

def wait_for_db(max_retries=30, retry_interval=2):
    """
    Wait for database to be ready.
    Useful for startup when database might not be immediately available.
    """
    for attempt in range(max_retries):
        if check_db_connection():
            logger.info("Database is ready")
            return True
        logger.info(
            f"Waiting for database... (attempt {attempt + 1}/{max_retries})"
        )
        time.sleep(retry_interval)
    
    logger.error(f"Database not ready after {max_retries} attempts")
    return False

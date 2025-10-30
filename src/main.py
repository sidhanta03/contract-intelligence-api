from fastapi import FastAPI
from src.routers import ingest, extract  # import both routers
from dotenv import load_dotenv
from src.routers.ask_route import router as ask_router
from src.routers.audit import router as audit_router
from src.db import check_db_connection
import logging

# ---- Configure logging ----
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---- Load environment variables (.env) ----
load_dotenv()

# ---- Initialize FastAPI app ----
app = FastAPI(
    title="Contract Intelligence API",
    description="AI-powered contract analysis and clause extraction API",
    version="2.0.0",
)


# ---- Startup Event ----
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Contract Intelligence API...")
    
    # Check database connection (non-blocking)
    try:
        if check_db_connection():
            logger.info("✓ Database connection established")
        else:
            logger.warning("⚠ Database connection check returned False - will retry on first request")
    except Exception as e:
        logger.warning(f"⚠ Database connection check failed with error: {e} - will retry on first request")


# ---- Include Routers ----
app.include_router(ingest.router, prefix="/api", tags=["Ingest"])
app.include_router(extract.router, prefix="/api", tags=["Extract"])
app.include_router(ask_router, prefix="/api", tags=["Ask"])
app.include_router(audit_router, prefix="/api", tags=["Audit"])


# ---- Health Check ----
@app.get("/healthz")
def health_check():
    """Health check endpoint - basic liveness check"""
    return {
        "status": "healthy",
        "message": "Server is running 🚀",
        "version": "2.0.0"
    }

# ---- Root Endpoint ----
@app.get("/")
def root():
    return {
        "message": "Welcome to the Contract Intelligence API",
        "version": "2.0.0",
        "database": "PostgreSQL",
        "docs": "/docs"
    }

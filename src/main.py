# src/main.py
from fastapi import FastAPI
from src.routers import ingest

app = FastAPI(title="Contract Intelligence API")

app.include_router(ingest.router)

@app.get("/healthz")
def health_check():
    return {"status": "ok"}

# src/routers/ingest.py
import os
import uuid
from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from src.db import get_db
from src.models.documents import Document
from src.utils.pdf_utils import extract_pdf_text

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/ingest")
async def ingest_pdfs(files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    document_ids = []

    for file in files:
        # Save file locally
        file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # Extract text + metadata
        extracted = extract_pdf_text(file_path)

        # Store record in DB
        doc = Document(
            filename=file.filename,
            file_size=os.path.getsize(file_path),
            extracted_text=extracted["text"],
            document_metadata=extracted["metadata"],
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        document_ids.append(doc.id)

    return {"document_ids": document_ids}

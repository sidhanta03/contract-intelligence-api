from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import os
import uuid
import logging
from datetime import datetime
from typing import List
import google.generativeai as genai
from dotenv import load_dotenv

from src.db import get_db
from src.models.documents import Document, DocumentChunk
from src.utils.pdf_utils import extract_text_from_pdf

# Configure logging
logger = logging.getLogger(__name__)
load_dotenv()

# Configure Gemini for embeddings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    EMBED_MODEL = "models/embedding-001"
else:
    logger.warning("GEMINI_API_KEY not found - embedding functionality will be disabled")
    EMBED_MODEL = None

router = APIRouter(prefix="/ingest", tags=["Ingest"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {".pdf"}
CHUNK_SIZE = 1000  # Characters per chunk
CHUNK_OVERLAP = 200  # Overlap between chunks


def validate_file(file: UploadFile) -> None:
    """Validate uploaded file"""
    # Check extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check if filename is provided
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[dict]:
    """Split text into overlapping chunks with metadata"""
    chunks = []
    text_length = len(text)
    
    if text_length == 0:
        return chunks
    
    start = 0
    chunk_index = 0
    
    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk_text = text[start:end]
        
        chunks.append({
            "text": chunk_text,
            "chunk_index": chunk_index,
            "char_start": start,
            "char_end": end
        })
        
        chunk_index += 1
        start = end - overlap if end < text_length else text_length
    
    return chunks


def create_embeddings(chunks: List[dict]) -> List[dict]:
    """Generate embeddings for text chunks using Gemini with error handling"""
    if not EMBED_MODEL:
        logger.warning("Embedding model not configured - skipping embeddings")
        return chunks
    
    embedded_count = 0
    failed_count = 0
    
    try:
        for chunk in chunks:
            try:
                response = genai.embed_content(
                    model=EMBED_MODEL,
                    content=chunk["text"]
                )
                chunk["embedding"] = response["embedding"]
                embedded_count += 1
            except Exception as e:
                error_str = str(e)
                # Check for quota errors
                if "429" in error_str or "quota" in error_str.lower():
                    logger.warning(f"Gemini API quota exceeded. Embeddings will be skipped for remaining chunks.")
                    failed_count = len(chunks) - embedded_count
                    break  # Stop trying if quota exceeded
                else:
                    logger.error(f"Failed to create embedding for chunk {chunk['chunk_index']}: {e}")
                    failed_count += 1
                    chunk["embedding"] = None
        
        if embedded_count > 0:
            logger.info(f"Successfully created {embedded_count}/{len(chunks)} embeddings")
        if failed_count > 0:
            logger.warning(f"Failed to create {failed_count}/{len(chunks)} embeddings")
        
        return chunks
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        # Continue without embeddings rather than failing
        return chunks


@router.post("/")
async def ingest_pdfs(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload and process PDF files
    
    - **files**: List of PDF files to upload
    
    Returns:
        - document_ids: List of generated document IDs
        - details: Processing details for each file
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided"
        )
    
    if len(files) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 files allowed per request"
        )
    
    document_ids = []
    processing_details = []
    
    for file in files:
        try:
            # Validate file
            validate_file(file)
            
            # Generate unique ID
            file_id = str(uuid.uuid4())
            
            # Save file
            file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
            file_content = await file.read()
            
            # Check file size
            file_size = len(file_content)
            if file_size > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File {file.filename} exceeds maximum size of 50MB"
                )
            
            with open(file_path, "wb") as f:
                f.write(file_content)
            
            # Extract text
            try:
                extracted_text = extract_text_from_pdf(file_path)
                if not extracted_text or len(extracted_text.strip()) == 0:
                    raise ValueError("No text could be extracted from PDF")
            except Exception as e:
                # Clean up file
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Failed to extract text from {file.filename}: {str(e)}"
                )
            
            # Create document record
            doc = Document(
                id=file_id,
                filename=file.filename,
                file_size=file_size,
                extracted_text=extracted_text,
                status="processing",
                document_metadata={
                    "path": file_path,
                    "upload_timestamp": datetime.utcnow().isoformat(),
                    "original_filename": file.filename
                }
            )
            
            db.add(doc)
            db.flush()  # Get the ID without committing
            
            # Create chunks with embeddings
            text_chunks = chunk_text(extracted_text)
            chunks_with_embeddings = create_embeddings(text_chunks)
            
            # Store chunks in database
            for chunk_data in chunks_with_embeddings:
                chunk = DocumentChunk(
                    id=str(uuid.uuid4()),
                    document_id=file_id,
                    chunk_text=chunk_data["text"],
                    chunk_index=chunk_data["chunk_index"],
                    char_start=chunk_data["char_start"],
                    char_end=chunk_data["char_end"],
                    embedding=chunk_data.get("embedding")
                )
                db.add(chunk)
            
            # Update document status
            doc.status = "ingested"
            db.commit()
            
            document_ids.append(file_id)
            processing_details.append({
                "document_id": file_id,
                "filename": file.filename,
                "file_size": file_size,
                "text_length": len(extracted_text),
                "chunks_created": len(text_chunks),
                "status": "success"
            })
            
            logger.info(f"Successfully ingested {file.filename} with ID {file_id}")
            
        except HTTPException:
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error while processing {file.filename}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while processing {file.filename}"
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Unexpected error processing {file.filename}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process {file.filename}: {str(e)}"
            )
    
    return {
        "message": f"Successfully ingested {len(document_ids)} file(s)",
        "document_ids": document_ids,
        "details": processing_details
    }

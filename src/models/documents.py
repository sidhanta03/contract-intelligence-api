import uuid
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, Float, ForeignKey, Boolean, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.config import Base

def generate_uuid():
    return str(uuid.uuid4())

class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    filename = Column(String, index=True, nullable=False)
    file_size = Column(Integer, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="uploaded", index=True)
    extracted_text = Column(Text, nullable=True)
    document_metadata = Column(JSON, nullable=True)
    
    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    extraction_results = relationship("ExtractionResult", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """Store text chunks with embeddings for RAG"""
    __tablename__ = "document_chunks"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Position in document
    page_number = Column(Integer, nullable=True)  # PDF page number
    char_start = Column(Integer, nullable=True)  # Character range start
    char_end = Column(Integer, nullable=True)  # Character range end
    embedding = Column(JSON, nullable=True)  # Store embedding as JSON array
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    document = relationship("Document", back_populates="chunks")


class ExtractionResult(Base):
    __tablename__ = "extraction_results"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    parties = Column(JSON, nullable=True)
    effective_date = Column(String, nullable=True)
    term = Column(String, nullable=True)
    governing_law = Column(String, nullable=True)
    payment_terms = Column(Text, nullable=True)
    termination = Column(Text, nullable=True)
    auto_renewal = Column(Boolean, nullable=True)
    confidentiality = Column(Text, nullable=True)
    indemnity = Column(Text, nullable=True)
    liability_cap = Column(JSON, nullable=True)  # {"amount": 1000000, "currency": "USD"}
    signatories = Column(JSON, nullable=True)  # [{"name": "John Doe", "title": "CEO"}]
    confidence_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    document = relationship("Document", back_populates="extraction_results")

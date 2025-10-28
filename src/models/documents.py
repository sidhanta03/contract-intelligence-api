import uuid
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, Float
from sqlalchemy.sql import func
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


class ExtractionResult(Base):
    __tablename__ = "extraction_results"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    document_id = Column(String, index=True, nullable=False)
    parties = Column(JSON, nullable=True)
    effective_date = Column(String, nullable=True)
    term = Column(String, nullable=True)
    governing_law = Column(String, nullable=True)
    payment_terms = Column(String, nullable=True)
    termination = Column(String, nullable=True)
    auto_renewal = Column(String, nullable=True)
    confidentiality = Column(String, nullable=True)
    indemnity = Column(String, nullable=True)
    liability_cap = Column(JSON, nullable=True)
    signatories = Column(JSON, nullable=True)
    confidence_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

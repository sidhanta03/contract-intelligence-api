from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from src.db import get_db
from src.models.documents import Document, DocumentChunk
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import google.generativeai as genai
import os
import logging
from dotenv import load_dotenv
import uuid

# Configure logging
logger = logging.getLogger(__name__)
load_dotenv()

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY not found - audit endpoint will not work")
else:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("Gemini API configured for audit endpoint")

LLM_MODEL = "gemini-2.0-flash-exp"

router = APIRouter()

# ---------- Schemas ----------

class AuditRequest(BaseModel):
    document_id: str = Field(..., description="UUID of the document to audit")

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }


class Finding(BaseModel):
    clause_type: str
    severity: str
    description: str
    evidence_text: str
    evidence_span: Optional[List[int]] = None
    suggestion: Optional[str] = None


class AuditResponse(BaseModel):
    document_id: str
    total_findings: int
    findings: List[Finding]


# ---------- Endpoint ----------

@router.post("/audit", response_model=AuditResponse)
def audit_contract(request: AuditRequest, db: Session = Depends(get_db)):
    """
    Audit the given contract for risky or non-standard clauses.
    Example risks:
      - Auto-renewal with <30d notice
      - Unlimited liability
      - Broad indemnity clauses
      - Weak confidentiality or termination clauses
    """

    # Validate UUID
    try:
        uuid.UUID(request.document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document_id format. Must be a valid UUID."
        )

    # Fetch document
    try:
        doc = db.query(Document).filter(Document.id == request.document_id).first()
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching document: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if not doc.extracted_text:
        raise HTTPException(status_code=400, detail="Document has no extracted text")

    # Fetch chunks (optional for context)
    try:
        chunks = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == request.document_id
        ).order_by(DocumentChunk.chunk_index).all()
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching chunks: {e}")
        chunks = []

    # Combine all text for audit
    contract_text = doc.extracted_text
    if not contract_text and chunks:
        contract_text = "\n".join([c.chunk_text for c in chunks])

    if not contract_text:
        raise HTTPException(status_code=400, detail="No text available for audit")

    if not GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="Gemini API not configured")

    # Prompt
    prompt = f"""
You are a contract risk analysis AI assistant. Review the following contract text and detect potentially risky clauses.
Return a structured JSON array where each finding has:
- clause_type: The type of clause (e.g., "Auto-Renewal", "Liability", "Indemnity")
- severity: One of ["low", "medium", "high"]
- description: Why this clause is risky or noteworthy
- evidence_text: The exact snippet or clause from the contract
- suggestion: How to mitigate or modify the risk (optional)

Focus especially on:
1. Auto-renewal with less than 30 days notice
2. Unlimited liability clauses
3. Broad indemnity clauses
4. Weak confidentiality terms
5. Ambiguous termination terms

Contract Text:
{contract_text[:16000]}  # Limit prompt to avoid exceeding token limit

Return strictly in JSON format (array of findings), no extra commentary.
"""

    try:
        model = genai.GenerativeModel(LLM_MODEL)
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
    except Exception as e:
        logger.error(f"Gemini API error during audit: {e}")
        raise HTTPException(status_code=503, detail="AI service unavailable")

    # Try parsing JSON safely
    import json
    findings = []
    try:
        findings_data = json.loads(raw_text)
        if isinstance(findings_data, dict):
            findings_data = [findings_data]
        for f in findings_data:
            findings.append(Finding(**f))
    except Exception as e:
        logger.warning(f"Failed to parse structured JSON. Returning plain-text fallback. Error: {e}")
        findings = [Finding(
            clause_type="Unparsed",
            severity="medium",
            description="Could not parse structured output from Gemini.",
            evidence_text=raw_text[:2000]
        )]

    return AuditResponse(
        document_id=request.document_id,
        total_findings=len(findings),
        findings=findings
    )

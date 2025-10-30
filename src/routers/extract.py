from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from src.db import get_db
from src.models.documents import Document, ExtractionResult
from pydantic import BaseModel, Field
import google.generativeai as genai
from dotenv import load_dotenv
import os
import json
import uuid
import re
import logging
from typing import Optional, List, Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini only if API key is available
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash-exp")  # Using the latest model
    logger.info("Gemini API configured successfully")
else:
    model = None
    logger.warning("GEMINI_API_KEY not found - extraction endpoint will not work")

# Router
router = APIRouter()

# Pydantic schemas
class ExtractRequest(BaseModel):
    document_id: str = Field(..., description="UUID of the document to extract fields from")
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }


class LiabilityCap(BaseModel):
    amount: Optional[float] = None
    currency: Optional[str] = None


class Signatory(BaseModel):
    name: str
    title: Optional[str] = None


class ExtractionResponse(BaseModel):
    document_id: str
    parties: Optional[List[str]] = None
    effective_date: Optional[str] = None
    term: Optional[str] = None
    governing_law: Optional[str] = None
    payment_terms: Optional[str] = None
    termination: Optional[str] = None
    auto_renewal: Optional[bool] = None
    confidentiality: Optional[str] = None
    indemnity: Optional[str] = None
    liability_cap: Optional[Dict[str, Any]] = None
    signatories: Optional[List[Dict[str, str]]] = None


def clean_gemini_response(text: str) -> str:
    """Remove markdown code blocks and extra whitespace from Gemini response"""
    # Remove ```json or ``` wrappers
    text = re.sub(r'^```(?:json)?|```$', '', text.strip(), flags=re.MULTILINE)
    return text.strip()


def validate_extraction_data(data: dict) -> dict:
    """Validate and normalize extraction data"""
    # Ensure auto_renewal is boolean
    if "auto_renewal" in data:
        if isinstance(data["auto_renewal"], str):
            data["auto_renewal"] = data["auto_renewal"].lower() in ["yes", "true", "1"]
        elif isinstance(data["auto_renewal"], bool):
            pass
        else:
            data["auto_renewal"] = None
    
    # Validate liability_cap structure
    if "liability_cap" in data and data["liability_cap"]:
        if isinstance(data["liability_cap"], dict):
            # Ensure amount is numeric if present
            if "amount" in data["liability_cap"]:
                try:
                    data["liability_cap"]["amount"] = float(data["liability_cap"]["amount"])
                except (ValueError, TypeError):
                    data["liability_cap"]["amount"] = None
        else:
            data["liability_cap"] = None
    
    # Ensure parties and signatories are lists
    if "parties" in data and not isinstance(data["parties"], list):
        data["parties"] = [data["parties"]] if data["parties"] else None
    
    if "signatories" in data:
        if not isinstance(data["signatories"], list):
            data["signatories"] = [data["signatories"]] if data["signatories"] else None
        elif data["signatories"]:
            # Ensure each signatory is a dict with name and title
            normalized = []
            for sig in data["signatories"]:
                if isinstance(sig, dict):
                    normalized.append({
                        "name": sig.get("name", ""),
                        "title": sig.get("title", "")
                    })
                elif isinstance(sig, str):
                    normalized.append({"name": sig, "title": ""})
            data["signatories"] = normalized
    
    return data


@router.post("/extract", response_model=ExtractionResponse)
def extract_fields(request: ExtractRequest, db: Session = Depends(get_db)):
    """
    Extract structured contract fields using Gemini AI
    
    - **document_id**: UUID of the document to process
    
    Returns structured contract data including:
    - parties, effective_date, term, governing_law
    - payment_terms, termination, auto_renewal
    - confidentiality, indemnity, liability_cap, signatories
    """
    
    # Check if Gemini is configured
    if not model:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service not configured. GEMINI_API_KEY is missing."
        )
    
    # Validate UUID format
    try:
        uuid.UUID(request.document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document_id format. Must be a valid UUID"
        )
    
    # Fetch the document
    try:
        doc = db.query(Document).filter(Document.id == request.document_id).first()
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {request.document_id} not found"
        )
    
    if not doc.extracted_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has no extracted text. Please ensure the document was properly ingested."
        )
    
    # Check if extraction already exists
    existing_extraction = db.query(ExtractionResult).filter(
        ExtractionResult.document_id == request.document_id
    ).first()
    
    if existing_extraction:
        logger.info(f"Returning cached extraction for document {request.document_id}")
        return ExtractionResponse(
            document_id=request.document_id,
            parties=existing_extraction.parties,
            effective_date=existing_extraction.effective_date,
            term=existing_extraction.term,
            governing_law=existing_extraction.governing_law,
            payment_terms=existing_extraction.payment_terms,
            termination=existing_extraction.termination,
            auto_renewal=existing_extraction.auto_renewal,
            confidentiality=existing_extraction.confidentiality,
            indemnity=existing_extraction.indemnity,
            liability_cap=existing_extraction.liability_cap,
            signatories=existing_extraction.signatories
        )
    
    # Create extraction prompt
    prompt = f"""You are a legal contract analyzer. Extract the following fields from the contract text below.
Return ONLY valid JSON with no explanations, no markdown formatting, no code blocks.

Required JSON structure:
{{
  "parties": ["Party A name", "Party B name"],
  "effective_date": "YYYY-MM-DD or descriptive text",
  "term": "duration description",
  "governing_law": "jurisdiction",
  "payment_terms": "payment description",
  "termination": "termination clause text",
  "auto_renewal": true or false,
  "confidentiality": "confidentiality clause text",
  "indemnity": "indemnity clause text",
  "liability_cap": {{"amount": numeric_value, "currency": "USD"}},
  "signatories": [{{"name": "Full Name", "title": "Title"}}]
}}

If a field is not found, use null. Be precise and extract exact text where applicable.

Contract Text (first 15000 characters):
{doc.extracted_text[:15000]}

Return only the JSON object:"""
    
    # Send to Gemini
    try:
        response = model.generate_content(prompt)
        text_response = response.text.strip()
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service temporarily unavailable. Please try again later."
        )
    
    # Clean and parse response
    clean_response = clean_gemini_response(text_response)
    
    try:
        extracted_data = json.loads(clean_response)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response: {text_response[:500]}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse AI response. The model returned invalid JSON."
        )
    
    # Validate and normalize data
    try:
        extracted_data = validate_extraction_data(extracted_data)
    except Exception as e:
        logger.error(f"Data validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate extracted data"
        )
    
    # Store extraction result
    try:
        result = ExtractionResult(
            id=str(uuid.uuid4()),
            document_id=request.document_id,
            parties=extracted_data.get("parties"),
            effective_date=extracted_data.get("effective_date"),
            term=extracted_data.get("term"),
            governing_law=extracted_data.get("governing_law"),
            payment_terms=extracted_data.get("payment_terms"),
            termination=extracted_data.get("termination"),
            auto_renewal=extracted_data.get("auto_renewal"),
            confidentiality=extracted_data.get("confidentiality"),
            indemnity=extracted_data.get("indemnity"),
            liability_cap=extracted_data.get("liability_cap"),
            signatories=extracted_data.get("signatories"),
            confidence_score=0.85  # Could implement actual confidence scoring
        )
        
        db.add(result)
        db.commit()
        db.refresh(result)
        
        logger.info(f"Successfully extracted fields for document {request.document_id}")
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error saving extraction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save extraction results"
        )
    
    # Return response
    return ExtractionResponse(
        document_id=request.document_id,
        parties=result.parties,
        effective_date=result.effective_date,
        term=result.term,
        governing_law=result.governing_law,
        payment_terms=result.payment_terms,
        termination=result.termination,
        auto_renewal=result.auto_renewal,
        confidentiality=result.confidentiality,
        indemnity=result.indemnity,
        liability_cap=result.liability_cap,
        signatories=result.signatories
    )

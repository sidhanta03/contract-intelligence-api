from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from src.db import get_db
from src.models.documents import Document, DocumentChunk
from pydantic import BaseModel, Field
import google.generativeai as genai
import numpy as np
import os
from dotenv import load_dotenv
import logging
from typing import List, Dict, Any, Optional
import uuid
import time
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine_similarity

# Configure logging
logger = logging.getLogger(__name__)

load_dotenv()

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY not found - ask endpoint will not work")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("Gemini API configured for ask endpoint")

# Models
EMBED_MODEL = "models/embedding-001"
LLM_MODEL = "gemini-2.0-flash-exp"

router = APIRouter()

# Pydantic schemas
class AskRequest(BaseModel):
    document_id: str = Field(..., description="UUID of the document to query")
    query: str = Field(..., min_length=1, max_length=1000, description="Question about the contract")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of relevant chunks to retrieve")
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "123e4567-e89b-12d3-a456-426614174000",
                "query": "What are the termination terms?",
                "top_k": 5
            }
        }


class Citation(BaseModel):
    document_id: str
    chunk_id: str
    chunk_index: int
    page: Optional[int] = None
    char_range: List[int]
    relevance_score: float


class AskResponse(BaseModel):
    answer: str
    citations: List[Citation]
    query: str
    document_id: str


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two vectors"""
    try:
        a = np.array(vec1)
        b = np.array(vec2)
        
        if len(a) == 0 or len(b) == 0:
            return 0.0
        
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(np.dot(a, b) / (norm_a * norm_b))
    except Exception as e:
        logger.error(f"Error computing cosine similarity: {e}")
        return 0.0


def retrieve_relevant_chunks(
    query_embedding: List[float],
    chunks: List[DocumentChunk],
    top_k: int
) -> List[tuple]:
    """
    Retrieve top-k most relevant chunks based on cosine similarity
    
    Returns: List of (chunk, similarity_score) tuples
    """
    scored_chunks = []
    
    for chunk in chunks:
        if chunk.embedding:
            try:
                similarity = cosine_similarity(query_embedding, chunk.embedding)
                scored_chunks.append((chunk, similarity))
            except Exception as e:
                logger.error(f"Error computing similarity for chunk {chunk.id}: {e}")
                continue
    
    if not scored_chunks:
        return []
    
    # Sort by similarity (highest first)
    scored_chunks.sort(key=lambda x: x[1], reverse=True)
    
    return scored_chunks[:top_k]


def retrieve_relevant_chunks_tfidf(
    query: str,
    chunks: List[DocumentChunk],
    top_k: int
) -> List[tuple]:
    """
    Fallback retrieval using TF-IDF when embeddings are unavailable
    
    Returns: List of (chunk, similarity_score) tuples
    """
    try:
        # Extract chunk texts
        chunk_texts = [chunk.chunk_text for chunk in chunks]
        
        if not chunk_texts:
            return []
        
        # Create TF-IDF vectorizer
        vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        
        # Fit and transform
        corpus = chunk_texts + [query]
        tfidf_matrix = vectorizer.fit_transform(corpus)
        
        # Query is the last vector
        query_vector = tfidf_matrix[-1]
        chunk_vectors = tfidf_matrix[:-1]
        
        # Compute similarities
        similarities = sklearn_cosine_similarity(query_vector, chunk_vectors).flatten()
        
        # Create scored chunks
        scored_chunks = []
        for i, chunk in enumerate(chunks):
            scored_chunks.append((chunk, float(similarities[i])))
        
        # Sort by similarity (highest first)
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        
        return scored_chunks[:top_k]
        
    except Exception as e:
        logger.error(f"Error in TF-IDF retrieval: {e}")
        # Return all chunks with equal score as last resort
        return [(chunk, 0.5) for chunk in chunks[:top_k]]


def generate_embedding_with_retry(content: str, max_retries: int = 3, initial_delay: float = 1.0) -> Optional[List[float]]:
    """
    Generate embedding with retry logic and exponential backoff
    
    Returns: Embedding vector or None if all retries fail
    """
    for attempt in range(max_retries):
        try:
            response = genai.embed_content(
                model=EMBED_MODEL,
                content=content
            )
            return response["embedding"]
        except Exception as e:
            error_str = str(e)
            
            # Check if it's a quota error
            if "429" in error_str or "quota" in error_str.lower():
                logger.warning(f"Gemini API quota exceeded: {e}")
                return None  # Don't retry on quota errors
            
            # For other errors, retry with exponential backoff
            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)
                logger.warning(f"Embedding attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                time.sleep(delay)
            else:
                logger.error(f"All embedding attempts failed: {e}")
                return None
    
    return None


@router.post("/ask", response_model=AskResponse)
def ask_about_contract(request: AskRequest, db: Session = Depends(get_db)):
    """
    Question answering grounded in uploaded documents (RAG)
    
    - **document_id**: UUID of the document to query
    - **query**: Natural language question about the contract
    - **top_k**: Number of relevant chunks to retrieve (1-20)
    
    Returns answer with citations including page numbers and character ranges
    """
    
    # Check if Gemini is configured
    if not GEMINI_API_KEY:
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
    
    # Fetch document
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
            detail="Document has no extracted text"
        )
    
    # Fetch chunks for this document
    try:
        chunks = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == request.document_id
        ).order_by(DocumentChunk.chunk_index).all()
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching chunks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while fetching document chunks"
        )
    
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No text chunks available for this document. Please re-ingest the document."
        )
    
    # Generate query embedding with retry logic
    query_embedding = None
    use_tfidf_fallback = False
    
    if GEMINI_API_KEY:
        query_embedding = generate_embedding_with_retry(request.query)
        
        if query_embedding is None:
            logger.warning("Falling back to TF-IDF due to embedding API failure")
            use_tfidf_fallback = True
    else:
        logger.warning("No Gemini API key, using TF-IDF fallback")
        use_tfidf_fallback = True
    
    # Retrieve relevant chunks
    try:
        if use_tfidf_fallback:
            # Use TF-IDF fallback
            relevant_chunks = retrieve_relevant_chunks_tfidf(
                request.query,
                chunks,
                request.top_k
            )
            logger.info("Using TF-IDF retrieval method")
        else:
            # Use embedding-based retrieval
            relevant_chunks = retrieve_relevant_chunks(
                query_embedding,
                chunks,
                request.top_k
            )
            logger.info("Using embedding-based retrieval method")
    except Exception as e:
        logger.error(f"Error retrieving relevant chunks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving relevant document chunks"
        )
    
    if not relevant_chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No relevant chunks found for your query."
        )
    
    # Build context from top chunks
    context_parts = []
    citations_data = []
    
    for chunk, score in relevant_chunks:
        context_parts.append(f"[Chunk {chunk.chunk_index}]: {chunk.chunk_text}")
        citations_data.append({
            "chunk": chunk,
            "score": score
        })
    
    context = "\n\n".join(context_parts)
    
    # Generate answer using Gemini
    prompt = f"""You are a legal AI assistant specialized in contract analysis. 
Answer the user's question based ONLY on the contract excerpts provided below. 

Important guidelines:
1. Only use information from the provided contract context
2. If the answer is not in the context, say "This information is not found in the provided contract"
3. Cite specific clauses or sections when possible
4. Be precise and concise
5. If multiple interpretations exist, mention them

Contract Context:
{context}

User Question: {request.query}

Provide a clear, well-structured answer:"""
    
    try:
        model = genai.GenerativeModel(LLM_MODEL)
        response = model.generate_content(prompt)
        answer = response.text.strip()
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service temporarily unavailable. Please try again later."
        )
    
    # Build citations
    citations = []
    for i, cite_data in enumerate(citations_data):
        chunk = cite_data["chunk"]
        citations.append(Citation(
            document_id=request.document_id,
            chunk_id=chunk.id,
            chunk_index=chunk.chunk_index,
            page=chunk.page_number,
            char_range=[chunk.char_start or 0, chunk.char_end or 0],
            relevance_score=round(cite_data["score"], 4)
        ))
    
    logger.info(f"Successfully answered query for document {request.document_id}")
    
    return AskResponse(
        answer=answer,
        citations=citations,
        query=request.query,
        document_id=request.document_id
    )

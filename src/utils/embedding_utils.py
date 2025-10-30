from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import os

# Load embedding model once (free, local)
model = SentenceTransformer("all-MiniLM-L6-v2")

# Initialize FAISS index
dimension = 384  # for MiniLM-L6-v2
index = faiss.IndexFlatL2(dimension)

def create_embeddings(chunks):
    """Return embeddings for text chunks."""
    embeddings = model.encode(chunks)
    return np.array(embeddings, dtype=np.float32)

def add_to_vector_store(chunks, document_id):
    """Add chunks to FAISS with document reference."""
    embeddings = create_embeddings(chunks)
    index.add(embeddings)
    os.makedirs("vector_store", exist_ok=True)
    faiss.write_index(index, f"vector_store/{document_id}.index")

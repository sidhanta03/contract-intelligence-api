# src/utils/pdf_utils.py
import PyPDF2
from typing import Dict

def extract_pdf_text(file_path: str) -> Dict:
    """
    Extracts text and metadata (page count) from PDF.
    """
    text = ""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() or ""

        metadata = {
            "num_pages": len(reader.pages),
        }
    return {"text": text, "metadata": metadata}

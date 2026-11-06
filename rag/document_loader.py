"""
Document Loader module for Government Scheme Assistant.
Extracts text and metadata from PDF files using PyMuPDF (fitz) with robust fallbacks.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from rag.text_preprocessor import clean_text

logger = logging.getLogger(__name__)


class Document:
    """Standardized Document class representing a document page or chunk."""
    def __init__(self, page_content: str, metadata: Optional[Dict[str, Any]] = None):
        self.page_content = page_content
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_content": self.page_content,
            "metadata": self.metadata
        }

    def __repr__(self) -> str:
        return f"Document(page={self.metadata.get('page')}, source={self.metadata.get('filename')}, chars={len(self.page_content)})"


def load_pdf(file_path: Path, scheme_metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
    """
    Extract text from a PDF file page-by-page.
    Prioritizes PyMuPDF (fitz), with automatic fallback to pypdf / pdfplumber.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"PDF document not found at: {file_path}")

    filename = file_path.name
    base_meta = scheme_metadata or {}
    base_meta.update({
        "filename": filename,
        "file_path": str(file_path),
        "source": filename
    })

    documents = []

    # Try PyMuPDF (fitz)
    try:
        import fitz
        doc = fitz.open(str(file_path))
        total_pages = len(doc)
        
        for page_num in range(total_pages):
            page = doc[page_num]
            text = page.get_text("text") or ""
            cleaned = clean_text(text)
            
            if cleaned:
                meta = dict(base_meta)
                meta.update({
                    "page": page_num + 1,
                    "total_pages": total_pages,
                    "extractor": "pymupdf"
                })
                documents.append(Document(page_content=cleaned, metadata=meta))
        
        doc.close()
        if documents:
            logger.info(f"Loaded {len(documents)} pages from {filename} using PyMuPDF.")
            return documents
    except Exception as e:
        logger.warning(f"PyMuPDF extraction failed for {filename} ({e}). Attempting fallback to pypdf...")

    # Fallback: pypdf
    try:
        import pypdf
        reader = pypdf.PdfReader(str(file_path))
        total_pages = len(reader.pages)
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            cleaned = clean_text(text)
            if cleaned:
                meta = dict(base_meta)
                meta.update({
                    "page": page_num + 1,
                    "total_pages": total_pages,
                    "extractor": "pypdf"
                })
                documents.append(Document(page_content=cleaned, metadata=meta))

        if documents:
            logger.info(f"Loaded {len(documents)} pages from {filename} using pypdf fallback.")
            return documents
    except Exception as e:
        logger.warning(f"pypdf extraction failed for {filename} ({e}). Attempting pdfplumber...")

    # Fallback: pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(str(file_path)) as pdf:
            total_pages = len(pdf.pages)
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                cleaned = clean_text(text)
                if cleaned:
                    meta = dict(base_meta)
                    meta.update({
                        "page": page_num + 1,
                        "total_pages": total_pages,
                        "extractor": "pdfplumber"
                    })
                    documents.append(Document(page_content=cleaned, metadata=meta))
        
        if documents:
            logger.info(f"Loaded {len(documents)} pages from {filename} using pdfplumber.")
            return documents
    except Exception as e:
        logger.error(f"All PDF extractors failed for {filename}: {e}")

    return documents


def load_all_documents_in_dir(directory: Path, schemes_map: Optional[Dict[str, Dict]] = None) -> List[Document]:
    """Load all PDF documents present in a directory and enrich with scheme metadata."""
    directory = Path(directory)
    all_docs = []
    
    if not directory.exists():
        return all_docs

    pdf_files = list(directory.glob("*.pdf"))
    for pdf_path in pdf_files:
        filename = pdf_path.name
        scheme_meta = {}
        if schemes_map and filename in schemes_map:
            scheme_meta = schemes_map[filename]
        
        docs = load_pdf(pdf_path, scheme_meta)
        all_docs.extend(docs)

    return all_docs

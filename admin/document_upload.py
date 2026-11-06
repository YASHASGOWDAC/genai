"""
Admin Document Upload module for Government Scheme Assistant.
Processes uploaded PDF guidelines, extracts text using PyMuPDF, chunks, embeds,
saves processed data into data/processed_documents/, and stores in ChromaDB & SQLite.
"""

import os
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Tuple

from config import RAW_DOCS_DIR, CENTRAL_DOCS_DIR, KARNATAKA_DOCS_DIR, PROCESSED_DOCS_DIR
from rag.document_loader import load_pdf
from rag.chunking import chunk_documents
from rag.vector_store import GovernmentSchemeVectorStore
from database.sqlite_db import add_or_update_document, document_exists, insert_or_update_scheme
from utils.source_validator import validate_government_url

try:
    from utils.performance_monitor import TimingContext
except ImportError:
    class TimingContext:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass

logger = logging.getLogger(__name__)


def process_and_index_uploaded_pdf(
    file_bytes: bytes,
    filename: str,
    scheme_name: str,
    department: str,
    level: str,
    category: str,
    source_url: str,
    publication_date: str,
    last_verified: str,
    vector_store: GovernmentSchemeVectorStore,
    overwrite: bool = False
) -> Tuple[bool, str, int]:
    """
    Save, preprocess, embed, and index an uploaded official government PDF into the local knowledge base.
    Prevents duplicate indexing unless overwrite=True.
    Returns (success, message, chunk_count).
    """
    if not filename.lower().endswith(".pdf"):
        return False, "Only PDF format documents are supported.", 0

    # Duplicate check
    is_already_indexed = document_exists(filename)
    if is_already_indexed and not overwrite:
        return False, f"Document '{filename}' is already indexed in the local knowledge base. Enable 'Update / Re-index Existing Document' to replace it.", 0

    # Source URL validation
    is_valid_url, url_reason = validate_government_url(source_url)
    if not is_valid_url:
        logger.warning(f"Source URL validation notice: {url_reason}")

    # Determine destination folder (Central vs Karnataka)
    dest_dir = KARNATAKA_DOCS_DIR if level == "Karnataka" else CENTRAL_DOCS_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    target_path = dest_dir / filename
    root_copy_path = RAW_DOCS_DIR / filename

    try:
        with open(target_path, "wb") as f:
            f.write(file_bytes)
        # Keep a copy in root raw_documents for quick resolution
        with open(root_copy_path, "wb") as f:
            f.write(file_bytes)
    except Exception as e:
        return False, f"Failed to save file to local directory: {e}", 0

    # If updating an existing document, delete previous chunks from ChromaDB
    if is_already_indexed and overwrite:
        logger.info(f"Overwriting existing document: removing previous vector chunks for {filename}")
        vector_store.delete_document_chunks(filename)

    # Extract text using PyMuPDF (fitz)
    scheme_id = filename.lower().replace(".pdf", "").replace(" ", "-")
    scheme_meta = {
        "scheme_id": scheme_id,
        "scheme_name": scheme_name,
        "department": department,
        "level": level,
        "category": category,
        "source_url": source_url,
        "publication_date": publication_date,
        "last_verified": last_verified
    }

    try:
        with TimingContext("pdf_processing", f"load_pdf_{filename}"):
            pages = load_pdf(target_path, scheme_meta)
        if not pages:
            return False, "Could not extract text from the uploaded PDF. The file may be empty or corrupted.", 0

        # Chunk document
        chunks = chunk_documents(pages)
        if not chunks:
            return False, "No valid text chunks were created from the document.", 0

        # Save clean extracted text + metadata to data/processed_documents/
        PROCESSED_DOCS_DIR.mkdir(parents=True, exist_ok=True)
        processed_file_path = PROCESSED_DOCS_DIR / f"{filename}.json"
        processed_record = {
            "filename": filename,
            "scheme_name": scheme_name,
            "level": level,
            "category": category,
            "department": department,
            "source_url": source_url,
            "publication_date": publication_date,
            "last_verified": last_verified,
            "total_pages": len(pages),
            "total_chunks": len(chunks),
            "extracted_pages": [p.to_dict() for p in pages]
        }
        with open(processed_file_path, "w", encoding="utf-8") as pf:
            json.dump(processed_record, pf, indent=2, ensure_ascii=False)

        # Add chunks with SentenceTransformer dense embeddings into persistent ChromaDB
        added_count = vector_store.add_chunks(chunks)

        # Update SQLite Document registry (database/schemes.db)
        add_or_update_document({
            "filename": filename,
            "file_path": str(target_path),
            "scheme_id": scheme_id,
            "scheme_name": scheme_name,
            "level": level,
            "category": category,
            "department": department,
            "source_url": source_url,
            "publication_date": publication_date,
            "last_verified": last_verified,
            "total_pages": len(pages),
            "total_chunks": added_count,
            "status": "indexed",
            "uploaded_by": "admin"
        })

        # Also register or update scheme record in SQLite schemes table
        full_text = "\n".join([p.page_content for p in pages])
        insert_or_update_scheme({
            "id": scheme_id,
            "name": scheme_name,
            "short_name": scheme_name[:30],
            "level": level,
            "department": department,
            "category": category,
            "description": full_text[:400] if len(full_text) > 50 else f"Government welfare program: {scheme_name}",
            "benefits_summary": f"Verified welfare assistance under {scheme_name}. Refer to {filename}.",
            "eligibility_summary": f"Eligible residents under {level} jurisdiction. Check policy document for parameters.",
            "application_portal": source_url if ("http" in source_url) else "https://www.myscheme.gov.in/",
            "is_verified": 1,
            "verification_date": last_verified,
            "source_document_name": filename,
            "source_url": source_url
        })

        action_word = "Updated and re-indexed" if is_already_indexed else "Indexed"
        return True, f"Successfully {action_word} '{filename}' ({len(pages)} pages, {added_count} chunks) in local knowledge base.", added_count

    except Exception as e:
        logger.error(f"Error during document indexing: {e}")
        return False, f"Indexing failed: {e}", 0

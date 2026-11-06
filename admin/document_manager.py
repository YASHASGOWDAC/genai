"""
Admin Document Manager module for Government Scheme Assistant.
Handles local document listing, deletion, re-indexing, and metadata verification.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime

from config import RAW_DOCS_DIR, CENTRAL_DOCS_DIR, KARNATAKA_DOCS_DIR, PROCESSED_DOCS_DIR
from rag.document_loader import load_pdf
from rag.chunking import chunk_documents
from rag.vector_store import GovernmentSchemeVectorStore
from database.sqlite_db import get_all_documents, delete_document_record, add_or_update_document, get_all_schemes

logger = logging.getLogger(__name__)


def list_managed_documents() -> List[Dict[str, Any]]:
    """Retrieve all indexed documents from the local knowledge base."""
    return get_all_documents()


def delete_indexed_document(filename: str, vector_store: GovernmentSchemeVectorStore) -> Tuple[bool, str]:
    """
    Delete a document completely:
    1. Removes all its vector chunks from ChromaDB without touching other documents.
    2. Removes its metadata from SQLite documents table.
    3. Removes physical file from central_schemes/ or karnataka_schemes/.
    4. Removes processed JSON file from data/processed_documents/.
    """
    try:
        # 1. Delete associated vectors from ChromaDB
        vector_store.delete_document_chunks(filename)

        # 2. Delete metadata from SQLite
        delete_document_record(filename)

        # 3. Remove physical PDF from all local subdirectories
        for dir_path in [CENTRAL_DOCS_DIR, KARNATAKA_DOCS_DIR, RAW_DOCS_DIR]:
            pdf_path = dir_path / filename
            if pdf_path.exists():
                try:
                    pdf_path.unlink()
                except Exception as e:
                    logger.warning(f"Could not remove physical file {pdf_path}: {e}")

        # 4. Remove processed JSON file
        processed_json = PROCESSED_DOCS_DIR / f"{filename}.json"
        if processed_json.exists():
            try:
                processed_json.unlink()
            except Exception:
                pass

        return True, f"Document '{filename}' and all its associated vector embeddings were deleted successfully from the local knowledge base."
    except Exception as e:
        logger.error(f"Error deleting document {filename}: {e}")
        return False, f"Failed to delete document: {e}"


def reindex_all_documents(vector_store: GovernmentSchemeVectorStore) -> Tuple[int, int]:
    """
    Wipe ChromaDB vector store collection and rebuild embeddings from all locally stored PDFs
    in central_schemes/ and karnataka_schemes/.
    """
    logger.info("Starting complete re-indexing of local knowledge base...")
    
    # Reset vector store collection
    vector_store.reset_collection()

    all_schemes = get_all_schemes()
    scheme_file_map = {}
    for s in all_schemes:
        doc_name = s.get("source_document_name")
        if doc_name:
            scheme_file_map[doc_name] = s

    # Discover all PDFs across central and karnataka directories
    pdf_files = []
    seen_names = set()
    for search_dir in [CENTRAL_DOCS_DIR, KARNATAKA_DOCS_DIR, RAW_DOCS_DIR]:
        if search_dir.exists():
            for p in search_dir.glob("*.pdf"):
                if p.name not in seen_names:
                    seen_names.add(p.name)
                    pdf_files.append(p)

    total_docs = len(pdf_files)
    total_chunks = 0
    PROCESSED_DOCS_DIR.mkdir(parents=True, exist_ok=True)

    for pdf in pdf_files:
        level = "Karnataka" if "karnataka" in str(pdf).lower() else "Central"
        scheme_info = scheme_file_map.get(pdf.name, {
            "name": pdf.name.replace(".pdf", ""),
            "department": "Government Department",
            "level": level,
            "category": "General",
            "source_url": "https://www.myscheme.gov.in/"
        })

        meta = {
            "scheme_name": scheme_info.get("name"),
            "department": scheme_info.get("department"),
            "level": scheme_info.get("level", level),
            "category": scheme_info.get("category", "General"),
            "source_url": scheme_info.get("source_url")
        }

        pages = load_pdf(pdf, meta)
        if pages:
            chunks = chunk_documents(pages)
            if chunks:
                added = vector_store.add_chunks(chunks)
                total_chunks += added

                # Save processed JSON
                processed_json_path = PROCESSED_DOCS_DIR / f"{pdf.name}.json"
                try:
                    with open(processed_json_path, "w", encoding="utf-8") as jf:
                        json.dump({
                            "filename": pdf.name,
                            "scheme_name": scheme_info.get("name"),
                            "level": meta["level"],
                            "category": meta["category"],
                            "department": meta["department"],
                            "total_pages": len(pages),
                            "total_chunks": added,
                            "last_verified": datetime.now().strftime("%Y-%m-%d"),
                            "pages": [p.to_dict() for p in pages]
                        }, jf, indent=2, ensure_ascii=False)
                except Exception as e:
                    logger.warning(f"Could not write processed JSON for {pdf.name}: {e}")

                add_or_update_document({
                    "filename": pdf.name,
                    "file_path": str(pdf),
                    "scheme_id": scheme_info.get("id", pdf.name.replace(".pdf", "")),
                    "scheme_name": scheme_info.get("name"),
                    "level": meta["level"],
                    "category": meta["category"],
                    "department": scheme_info.get("department"),
                    "source_url": scheme_info.get("source_url"),
                    "total_pages": len(pages),
                    "total_chunks": added,
                    "status": "indexed"
                })

    logger.info(f"Re-indexing complete: {total_docs} local files, {total_chunks} chunks.")
    return total_docs, total_chunks

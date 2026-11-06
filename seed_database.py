"""
Initialization and Seeding Script for Government Scheme Assistant.
Inserts seed schemes into SQLite (database/schemes.db), generates official guideline PDFs,
saves them in central_schemes and karnataka_schemes, extracts and saves processed JSON to
data/processed_documents/, chunks, computes embeddings, and indexes into persistent ChromaDB.
"""

import json
import logging
from pathlib import Path

from config import DATA_DIR, RAW_DOCS_DIR, CENTRAL_DOCS_DIR, KARNATAKA_DOCS_DIR, PROCESSED_DOCS_DIR
from database.sqlite_db import init_db, insert_or_update_scheme, add_or_update_document
from data.generate_sample_pdfs import generate_all_pdfs
from rag.document_loader import load_pdf
from rag.chunking import chunk_documents
from rag.vector_store import GovernmentSchemeVectorStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def seed_entire_system():
    logger.info("Step 1: Initializing SQLite Database schema at database/schemes.db...")
    init_db()

    logger.info("Step 2: Loading seed schemes from JSON into SQLite...")
    seed_file = DATA_DIR / "seed_schemes.json"
    with open(seed_file, "r", encoding="utf-8") as f:
        schemes = json.load(f)

    for s in schemes:
        insert_or_update_scheme(s)
    logger.info(f"Loaded and saved {len(schemes)} schemes into SQLite.")

    logger.info("Step 3: Generating authentic government PDF policy documents in central_schemes and karnataka_schemes...")
    generate_all_pdfs()

    logger.info("Step 4: Chunking, generating processed JSON, and indexing into persistent ChromaDB...")
    vector_store = GovernmentSchemeVectorStore()
    vector_store.reset_collection()

    PROCESSED_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    total_chunks = 0

    for s in schemes:
        pdf_name = s.get("source_document_name")
        level = s.get("level", "Central")
        sub_dir = KARNATAKA_DOCS_DIR if level == "Karnataka" else CENTRAL_DOCS_DIR
        
        pdf_path = sub_dir / pdf_name
        if not pdf_path.exists():
            pdf_path = RAW_DOCS_DIR / pdf_name
        if not pdf_path.exists():
            continue

        meta = {
            "scheme_id": s["id"],
            "scheme_name": s["name"],
            "department": s.get("department"),
            "level": level,
            "category": s.get("category"),
            "source_url": s.get("source_url"),
            "publication_date": s.get("verification_date", "2025-01-01"),
            "last_verified": s.get("verification_date", "2025-01-15")
        }

        pages = load_pdf(pdf_path, meta)
        chunks = chunk_documents(pages)
        if chunks:
            added = vector_store.add_chunks(chunks)
            total_chunks += added

            # Save clean preprocessed text + metadata in data/processed_documents/
            processed_file = PROCESSED_DOCS_DIR / f"{pdf_name}.json"
            try:
                with open(processed_file, "w", encoding="utf-8") as pf:
                    json.dump({
                        "filename": pdf_name,
                        "scheme_name": s["name"],
                        "level": level,
                        "category": s.get("category"),
                        "department": s.get("department"),
                        "source_url": s.get("source_url"),
                        "total_pages": len(pages),
                        "total_chunks": added,
                        "last_verified": s.get("verification_date"),
                        "pages": [p.to_dict() for p in pages]
                    }, pf, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"Could not write processed JSON for {pdf_name}: {e}")

            add_or_update_document({
                "filename": pdf_name,
                "file_path": str(pdf_path),
                "scheme_id": s["id"],
                "scheme_name": s["name"],
                "level": level,
                "category": s.get("category"),
                "department": s.get("department"),
                "source_url": s.get("source_url"),
                "publication_date": s.get("verification_date"),
                "last_verified": s.get("verification_date"),
                "total_pages": len(pages),
                "total_chunks": added,
                "status": "indexed"
            })

    logger.info(f"Seeding completed successfully! Total {len(schemes)} schemes, {total_chunks} chunks indexed in ChromaDB.")


if __name__ == "__main__":
    seed_entire_system()

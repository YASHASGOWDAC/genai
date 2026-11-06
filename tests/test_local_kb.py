"""
Comprehensive Test Suite for Local Knowledge Base Operations.
Tests:
- Local directory structure.
- Local PDF text extraction.
- Embedding generation without internet.
- ChromaDB persistence across client restarts.
- Local retrieval and source citation accuracy.
- Scheme metadata filtering.
- Duplicate document prevention and overwrite.
- Document deletion without affecting other documents.
- Explicit unavailability notice when scheme is not in local knowledge base.
"""

import os
import pytest
from pathlib import Path

from config import (
    CENTRAL_DOCS_DIR, KARNATAKA_DOCS_DIR, PROCESSED_DOCS_DIR, 
    CHROMA_PERSIST_DIR, SQLITE_DB_PATH
)
from rag.document_loader import load_pdf
from rag.chunking import chunk_documents
from rag.embeddings import GovernmentSchemeEmbeddings
from rag.vector_store import GovernmentSchemeVectorStore
from rag.retriever import GovernmentSchemeRetriever
from rag.answer_generator import GovernmentSchemeAnswerGenerator
from admin.document_upload import process_and_index_uploaded_pdf
from admin.document_manager import delete_indexed_document, list_managed_documents
from database.sqlite_db import get_all_schemes, document_exists, get_knowledge_base_stats
from pages import admin_page


def test_local_directories_and_db_exist():
    """Verify all designated local storage directories and database exist."""
    assert CENTRAL_DOCS_DIR.exists(), "central_schemes directory must exist"
    assert KARNATAKA_DOCS_DIR.exists(), "karnataka_schemes directory must exist"
    assert PROCESSED_DOCS_DIR.exists(), "processed_documents directory must exist"
    assert CHROMA_PERSIST_DIR.exists(), "chroma_db directory must exist"
    assert SQLITE_DB_PATH.exists(), "schemes.db SQLite database must exist"


def test_local_text_extraction():
    """Test text extraction using PyMuPDF from a local PDF."""
    central_pdfs = list(CENTRAL_DOCS_DIR.glob("*.pdf"))
    assert len(central_pdfs) > 0, "At least one Central scheme PDF should be stored locally"
    
    sample_pdf = central_pdfs[0]
    docs = load_pdf(sample_pdf, {"scheme_name": "Test Scheme", "level": "Central"})
    assert len(docs) > 0, "PyMuPDF must extract pages from local PDF"
    assert len(docs[0].page_content) > 50, "Extracted page content must not be empty"
    assert docs[0].metadata["page"] == 1
    assert docs[0].metadata["filename"] == sample_pdf.name


def test_embedding_generation_local():
    """Test Sentence Transformers dense embedding generation."""
    embedder = GovernmentSchemeEmbeddings()
    vector = embedder.embed_query("Local scheme retrieval query")
    assert isinstance(vector, list)
    assert len(vector) == 384
    assert any(v != 0.0 for v in vector)


def test_chromadb_persistence_restart():
    """Test ChromaDB persistence across client re-instantiations."""
    vs1 = GovernmentSchemeVectorStore()
    initial_count = vs1.count()
    assert initial_count > 0, "ChromaDB should contain indexed chunks"

    # Simulate restart by re-instantiating client
    vs2 = GovernmentSchemeVectorStore()
    assert vs2.count() == initial_count, "ChromaDB must retain all vector chunks after client re-instantiation"


def test_local_retrieval_and_source_citations():
    """Test local retrieval without internet access and citation accuracy."""
    retriever = GovernmentSchemeRetriever()
    results = retriever.retrieve("What are the financial benefits of PM-KISAN?", top_k=2)
    assert len(results) > 0, "Retriever must find matching local document chunks"
    
    top_chunk = results[0]
    meta = top_chunk["metadata"]
    assert "filename" in meta, "Citation must include document filename"
    assert "page" in meta, "Citation must include page number"
    assert meta["page"] >= 1


def test_scheme_metadata_filtering():
    """Test metadata filtering by level (Central vs Karnataka) and category."""
    retriever = GovernmentSchemeRetriever()

    # Filter by Karnataka
    karnataka_results = retriever.retrieve("scheme assistance", top_k=4, level="Karnataka")
    for r in karnataka_results:
        assert r["metadata"].get("level") == "Karnataka", "All retrieved chunks must match Karnataka level filter"

    # Filter by Central
    central_results = retriever.retrieve("scheme assistance", top_k=4, level="Central")
    for r in central_results:
        assert r["metadata"].get("level") == "Central", "All retrieved chunks must match Central level filter"


def test_duplicate_document_prevention():
    """Test that uploading an already-indexed document without overwrite is rejected."""
    vs = GovernmentSchemeVectorStore()
    test_pdf_content = b"%PDF-1.4 test dummy content for duplicate check"
    test_filename = "PM-KISAN Operational Guidelines.pdf"

    # Attempt to upload duplicate with overwrite=False
    success, msg, chunks = process_and_index_uploaded_pdf(
        file_bytes=test_pdf_content,
        filename=test_filename,
        scheme_name="PM-KISAN",
        department="Agriculture",
        level="Central",
        category="Agriculture & Rural Development",
        source_url="https://pmkisan.gov.in/",
        publication_date="2025-01-01",
        last_verified="2025-01-15",
        vector_store=vs,
        overwrite=False
    )
    assert not success, "Uploading existing document with overwrite=False must be rejected"
    assert "already indexed" in msg.lower()


def test_document_deletion_isolation():
    """Test document deletion removes its vectors and metadata without affecting others."""
    vs = GovernmentSchemeVectorStore()
    initial_chunks = vs.count()

    # Create and index a temporary scheme document
    from reportlab.platypus import SimpleDocTemplate, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    
    temp_filename = "Temporary_Test_Scheme.pdf"
    temp_path = CENTRAL_DOCS_DIR / temp_filename
    doc = SimpleDocTemplate(str(temp_path))
    doc.build([Paragraph("Temporary Government Policy Document content for testing deletion.", getSampleStyleSheet()['Normal'])])

    with open(temp_path, "rb") as f:
        bytes_data = f.read()

    # Index temp document
    success, msg, added = process_and_index_uploaded_pdf(
        file_bytes=bytes_data,
        filename=temp_filename,
        scheme_name="Temporary Scheme",
        department="Test Dept",
        level="Central",
        category="General",
        source_url="https://india.gov.in/",
        publication_date="2025-01-01",
        last_verified="2025-01-15",
        vector_store=vs,
        overwrite=True
    )
    assert success
    assert vs.count() == initial_chunks + added
    assert document_exists(temp_filename)

    # Delete temp document
    del_success, del_msg = delete_indexed_document(temp_filename, vs)
    assert del_success
    assert vs.count() == initial_chunks, "ChromaDB vector count must return to initial count after document deletion"
    assert not document_exists(temp_filename), "Document must be removed from SQLite registry"


def test_unverified_scheme_local_knowledge_base_message():
    """Test that requesting an unknown scheme explicitly informs user it is not in the local knowledge base."""
    ans_gen = GovernmentSchemeAnswerGenerator()
    resp = ans_gen.generate_answer(
        query="What is the benefit under Martian Alien Solar Subsidy 999?",
        retrieved_chunks=[]
    )
    assert not resp["is_verified"]
    assert "not available in the local government scheme knowledge base" in resp["answer"]
    assert len(resp["citations"]) == 0


def test_admin_access_disabled_without_password(monkeypatch):
    """Admin access must stay disabled until a password is configured."""
    monkeypatch.setattr(admin_page, "ADMIN_PASSWORD", "")
    monkeypatch.setattr(admin_page.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_page.st, "caption", lambda *args, **kwargs: None)
    errors = []
    monkeypatch.setattr(admin_page.st, "error", errors.append)

    admin_page.render_admin_dashboard()

    assert len(errors) == 1
    assert "admin access is disabled" in errors[0].lower()

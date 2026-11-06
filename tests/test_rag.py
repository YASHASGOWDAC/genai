"""
Unit and Integration Tests for RAG pipeline.
Tests document loader, preprocessor, chunker, embeddings, vector store, and retriever.
"""

import pytest
from pathlib import Path
from rag.document_loader import Document, load_pdf
from rag.text_preprocessor import clean_text, extract_headings
from rag.chunking import recursive_split_text, chunk_documents, DocumentChunk
from rag.embeddings import GovernmentSchemeEmbeddings, FallbackEmbeddingModel
from rag.vector_store import GovernmentSchemeVectorStore
from rag.retriever import GovernmentSchemeRetriever
from rag.answer_generator import GovernmentSchemeAnswerGenerator
from config import RAW_DOCS_DIR


def test_text_cleaning():
    raw = "  Government   of  Karnataka \n\n\n\n  Rs. 2000 per month.  Page 1 of 5 \n  "
    cleaned = clean_text(raw)
    assert "₹ 2000 per month." in cleaned
    assert "Government of Karnataka" in cleaned
    assert "Page 1 of 5" not in cleaned


def test_recursive_split_text():
    sample_text = (
        "Pradhan Mantri Kisan Samman Nidhi is a Central Sector Scheme. "
        "It provides financial assistance of Rs. 6000 per annum to all landholding farmer families. "
        "The financial benefit is released directly to bank accounts in three installments. "
        "Eligible farmers can register on the pmkisan.gov.in portal."
    )
    splits = recursive_split_text(sample_text, chunk_size=120, chunk_overlap=20)
    assert len(splits) >= 2
    assert all(len(s) <= 150 for s in splits)


def test_chunk_documents_metadata_enrichment():
    doc = Document(
        page_content="Under the Gruha Lakshmi scheme, women heads of families receive Rs 2000 monthly.",
        metadata={
            "filename": "Gruha Lakshmi Government Order.pdf",
            "page": 1,
            "scheme_name": "Karnataka Gruha Lakshmi Scheme",
            "department": "Women and Child Development",
            "level": "Karnataka"
        }
    )
    chunks = chunk_documents([doc])
    assert len(chunks) >= 1
    c = chunks[0]
    assert "SCHEME: Karnataka Gruha Lakshmi Scheme" in c.content
    assert c.metadata["page"] == 1
    assert c.metadata["level"] == "Karnataka"


def test_embeddings():
    embedder = GovernmentSchemeEmbeddings()
    vec = embedder.embed_query("PM-KISAN benefits")
    assert isinstance(vec, list)
    assert len(vec) == 384
    assert any(v != 0.0 for v in vec)


def test_vector_store_and_retriever():
    vector_store = GovernmentSchemeVectorStore()
    assert vector_store.count() > 0

    retriever = GovernmentSchemeRetriever(vector_store)
    results = retriever.retrieve("How much money do farmers get in PM-KISAN?", top_k=3)
    
    assert len(results) > 0
    top_chunk = results[0]
    assert "PM-KISAN" in top_chunk["content"] or "Kisan" in top_chunk["content"] or top_chunk["similarity"] > 0.3


def test_answer_generator_fallback():
    generator = GovernmentSchemeAnswerGenerator(api_key="")
    dummy_chunk = [{
        "chunk_id": "test_1",
        "content": "SCHEME: PM-KISAN\nCore Benefit: ₹6,000 per year in 3 installments.\nOfficial Portal: https://pmkisan.gov.in/",
        "metadata": {
            "filename": "PM-KISAN Operational Guidelines.pdf",
            "page": 1,
            "scheme_name": "PM-KISAN",
            "department": "Agriculture",
            "source_url": "https://pmkisan.gov.in/"
        },
        "similarity": 0.85
    }]
    ans = generator.generate_answer("How much benefit in PM-KISAN?", dummy_chunk)
    assert "₹6,000" in ans["answer"] or "PM-KISAN" in ans["answer"]
    assert len(ans["citations"]) > 0
    assert ans["citations"][0]["document"] == "PM-KISAN Operational Guidelines.pdf"

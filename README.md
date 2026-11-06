ADMIN_PASSWORD=
Copy `.env.example` to `.env` and set a unique `ADMIN_PASSWORD` before enabling the admin dashboard. Admin access remains disabled when it is blank. Keep `.env` private; it is excluded from Git.

Verify your other `.env` settings:
# 🏛️ AI-Powered Government Scheme Information Assistant (Local Knowledge Base RAG)

An enterprise-grade, retrieval-augmented generation (RAG) platform designed to empower Indian citizens to discover, evaluate eligibility for, and navigate **Central Government** and **Karnataka State Government** welfare schemes.

The entire system operates on a **completely locally stored government scheme knowledge base**. It retrieves information **only from locally stored and verified official documents**—never fetching live scheme details from the internet or hallucinating benefits.

---

## 🌟 Key Features & Local Knowledge Base Architecture

1. **Completely Local Knowledge Base**:
   - All official government scheme documents are pre-stored and organized locally:
     - `data/raw_documents/central_schemes/` (Central Government policies).
     - `data/raw_documents/karnataka_schemes/` (Karnataka State Government orders).
     - `data/processed_documents/` (Extracted and preprocessed JSON records with metadata).
     - `database/chroma_db/` (Local persistent ChromaDB vector store).
     - `database/schemes.db` (Local SQLite database storing schemes, documents, user profiles, and chat logs).
   - **Zero Live Internet Retrieval**: Does not search the web for scheme rules or hallucinate information.

2. **Admin Document Upload & Local Ingestion**:
   - Authorized administrators can upload official government scheme PDFs.
   - Metadata capture: Scheme Name, Category, Jurisdiction (Central / Karnataka), Department, Source URL, Publication Date, and Last Verified Date.
   - Text extraction using **PyMuPDF (`pymupdf` / `fitz`)**.
   - Cleaned, normalized, and split into semantic chunks with context headers.
   - Stored in persistent local ChromaDB and SQLite (`database/schemes.db`).
   - **Duplicate Detection & Re-indexing**: Prevents duplicate indexing; provides an update mode that removes prior vector chunks before re-indexing.

3. **Local RAG Retrieval & Grounded Answering**:
   - User questions search only the local ChromaDB vector store.
   - Hybrid retrieval combines dense semantic similarity (`sentence-transformers/all-MiniLM-L6-v2`) with domain keyword bonuses.
   - Metadata filtering by state/level (`Central`, `Karnataka`) and category.
   - Every response provides explicit local source citations: document name and page number.
   - **Explicit Unavailability Notice**: If a scheme is not indexed locally, the system clearly informs the citizen:
     *"The requested scheme information is not available in the local government scheme knowledge base. Please contact an administrator to upload the official policy PDF guidelines for this scheme."*

4. **Offline Capability & LLM Flexibility**:
   - The retrieval and search pipeline runs **100% offline** using local Sentence Transformers cache and persistent ChromaDB.
   - **Ollama Support**: Supports locally running offline LLMs via Ollama (e.g. `llama3`, `mistral`, `gemma`, `phi3`) at `http://localhost:11434`.
   - **Deterministic Local Synthesizer**: Built-in offline structured extractor that works without any LLM server or API key.
   - **Google Gemini API (Optional)**: Optional online answering provider, strictly grounded in retrieved local chunks (never used for web searches).

5. **Local Scheme Explorer**:
   - Built on top of SQLite records in `database/schemes.db`.
   - Search stored schemes, filter by category and state/jurisdiction.
   - View eligibility conditions, financial quantum, mandatory documents, and step-by-step procedures.

6. **Knowledge Base Management Dashboard**:
   - Admin view displaying:
     - Total schemes stored.
     - Total documents uploaded.
     - Total indexed chunks in ChromaDB.
     - Central Government schemes count.
     - Karnataka schemes count.
     - Latest document verification dates.
     - Indexing status.
   - Document deletion removes associated vectors and metadata without affecting any other documents.
   - One-click master re-indexing.

7. **Multilingual Interface**:
   - Full support for **English**, **Kannada (ಕನ್ನಡ)**, and **Hindi (हिंदी)** with official legal terminology preservation.

---

## 📁 Updated Directory Structure

```
Government_Scheme_Assistant/
│
├── app.py                      # Main Streamlit application entry point
├── config.py                   # Central settings, paths, Ollama & database configs
├── seed_database.py            # Automated script to seed database & ChromaDB vector store
├── requirements.txt            # Python dependencies
├── .env.example                # Example environment configuration
├── README.md                   # Complete documentation
│
├── data/
│   ├── raw_documents/
│   │   ├── central_schemes/    # Local Central Govt PDFs (PM-KISAN, AB-PMJAY, MUDRA, etc.)
│   │   └── karnataka_schemes/  # Local Karnataka State PDFs (Gruha Lakshmi, Yuva Nidhi, etc.)
│   ├── processed_documents/    # Extracted JSON files with page content & metadata
│   ├── seed_schemes.json       # Ground-truth scheme specifications (Central & Karnataka)
│   └── generate_sample_pdfs.py # ReportLab script creating authentic policy PDFs
│
├── database/
│   ├── schemes.db              # Local SQLite database (schemes, documents, chat history)
│   ├── sqlite_db.py            # SQLite schema and query methods
│   └── chroma_db/              # Local persistent ChromaDB vector store directory
│
├── rag/
│   ├── document_loader.py      # PyMuPDF extractor with fallback to pypdf
│   ├── text_preprocessor.py    # Text cleaning, header/footer removal, normalization
│   ├── chunking.py             # Context-aware recursive character chunker
│   ├── embeddings.py           # Sentence Transformers wrapper with offline mode
│   ├── vector_store.py         # Persistent ChromaDB client, indexing, batching, queries
│   ├── retriever.py            # Hybrid semantic + lexical retriever with metadata filtering
│   └── answer_generator.py     # Grounding caller supporting Ollama, Gemini, & Local Synthesizer
│
├── modules/
│   ├── chatbot.py              # Chat coordinator and history manager
│   ├── eligibility_checker.py  # Deterministic rule engine for Central & Karnataka schemes
│   ├── scheme_explorer.py      # Multicriteria search and filtering module
│   ├── document_assistant.py   # Document checklist generator and issuing directory
│   └── multilingual.py         # Localization and entity-preserving language detector
│
├── admin/
│   ├── document_upload.py      # Admin upload, text extraction, and indexing pipeline
│   └── document_manager.py     # Document listing, deletion, and full re-indexing
│
├── utils/
│   ├── source_validator.py     # Verifies authentic .gov.in and .nic.in domains
│   └── helpers.py              # Formatting helpers, badges, currency formatters
│
├── pages/
│   ├── dashboard.py            # Home dashboard metrics and quick actions
│   ├── chatbot_page.py         # AI Assistant conversational UI with provider selector
│   ├── schemes_page.py         # Searchable directory and scheme cards
│   ├── eligibility_page.py     # Interactive eligibility assessment form
│   ├── documents_page.py       # Mandatory document checklist & rejection guide
│   ├── saved_schemes_page.py   # Citizen bookmarked schemes & notes
│   ├── evaluation_page.py      # Real-time RAG evaluation benchmark
│   └── admin_page.py           # Password-protected admin document manager & KB stats
│
└── tests/
    ├── test_local_kb.py        # Tests for local storage, extraction, ChromaDB, deletion, etc.
    ├── test_rag.py             # Tests for loader, preprocessor, chunker, vector store
    ├── test_eligibility.py     # Tests for eligibility criteria and exclusions
    └── test_multilingual.py    # Tests for language detection and UI translation
```

---

## 🚀 Running the Application

### 1. Environment Configuration
Copy `.env.example` to `.env` and set a unique `ADMIN_PASSWORD` before enabling the admin dashboard. Admin access stays disabled when it is blank. Keep `.env` private; it is excluded from Git.
```ini
GEMINI_API_KEY=your_gemini_api_key_here
ADMIN_PASSWORD=
SQLITE_DB_PATH=database/schemes.db
CHROMA_PERSIST_DIR=database/chroma_db
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
DEFAULT_LLM_PROVIDER=auto
```

### 2. Seeding Local Knowledge Base
Populate `database/schemes.db`, organize local PDFs into `central_schemes/` and `karnataka_schemes/`, generate processed JSON files, and index vector embeddings in ChromaDB:
```bash
python seed_database.py
```

### 3. Start the Web Dashboard
```bash
streamlit run app.py
```
Open `http://localhost:8501` in your browser.

---

## 🧪 Test Suite Results

Run all 22 automated tests with pytest:
```bash
pytest tests/ -v
```

### Test Coverage Breakdown:
```text
tests/test_eligibility.py::test_karnataka_domicile_eligibility PASSED      [  4%]
tests/test_eligibility.py::test_pm_kisan_taxpayer_disqualification PASSED   [  9%]
tests/test_eligibility.py::test_pm_kisan_eligible_farmer PASSED            [ 13%]
tests/test_eligibility.py::test_yuva_nidhi_unemployment_duration PASSED    [ 18%]
tests/test_eligibility.py::test_insufficient_information PASSED            [ 22%]
tests/test_local_kb.py::test_local_directories_and_db_exist PASSED         [ 27%]
tests/test_local_kb.py::test_local_text_extraction PASSED                  [ 31%]
tests/test_local_kb.py::test_embedding_generation_local PASSED             [ 36%]
tests/test_local_kb.py::test_chromadb_persistence_restart PASSED           [ 40%]
tests/test_local_kb.py::test_local_retrieval_and_source_citations PASSED   [ 45%]
tests/test_local_kb.py::test_scheme_metadata_filtering PASSED              [ 50%]
tests/test_local_kb.py::test_duplicate_document_prevention PASSED          [ 54%]
tests/test_local_kb.py::test_document_deletion_isolation PASSED            [ 59%]
tests/test_local_kb.py::test_unverified_scheme_local_knowledge_base_message PASSED [ 63%]
tests/test_multilingual.py::test_language_detection PASSED                 [ 68%]
tests/test_multilingual.py::test_ui_translation PASSED                     [ 72%]
tests/test_rag.py::test_text_cleaning PASSED                               [ 77%]
tests/test_rag.py::test_recursive_split_text PASSED                        [ 81%]
tests/test_rag.py::test_chunk_documents_metadata_enrichment PASSED         [ 86%]
tests/test_rag.py::test_embeddings PASSED                                  [ 90%]
tests/test_rag.py::test_vector_store_and_retriever PASSED                  [ 95%]
tests/test_rag.py::test_answer_generator_fallback PASSED                   [100%]

======================= 22 passed in 21.72s ========================
```

---

## 🔒 Security & Privacy

- Scheme documents are stored and processed strictly on the local filesystem.
- No documents or search queries are transmitted to external web search APIs.
- Administrator functions (uploading, re-indexing, deleting) are secured with password authentication.

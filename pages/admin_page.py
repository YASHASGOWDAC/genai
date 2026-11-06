"""
Admin Dashboard Page for Government Scheme Information Assistant.
Password-authenticated management for local document ingestion, vector indexing, audits,
performance metrics, and knowledge base statistics.

Optimized with:
- Lazy vector store loading (only instantiated on upload/delete/reindex actions)
- In-memory cached database stats
- Real-time performance monitoring telemetry dashboard
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
from config import ADMIN_PASSWORD, SCHEME_CATEGORIES, STATE_APPLICABILITY
from database.sqlite_db import get_knowledge_base_stats, document_exists, get_all_documents

try:
    from utils.performance_monitor import TimingContext, get_performance_summary, get_recent_timings
except ImportError:
    class TimingContext:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
    def get_performance_summary(): return {}
    def get_recent_timings(limit=50): return []


def render_admin_dashboard():
    with TimingContext("page_navigation", "render_admin_dashboard"):
        st.subheader("🔒 Administrator Document & Knowledge Base Management")
        st.caption("Authorized portal for uploading government guidelines, managing local ChromaDB vector store, and auditing records.")

        # Authentication Check
        if not ADMIN_PASSWORD:
            st.error("Admin access is disabled. Set ADMIN_PASSWORD in your local .env file and restart the app.")
            return

        if "admin_authenticated" not in st.session_state:
            st.session_state.admin_authenticated = False

        if not st.session_state.admin_authenticated:
            with st.container(border=True):
                st.markdown("#### Admin Login")
                entered_pwd = st.text_input("Enter Admin Security Password:", type="password")
                if st.button("Unlock Admin Portal", type="primary"):
                    if entered_pwd == ADMIN_PASSWORD:
                        st.session_state.admin_authenticated = True
                        st.success("Authenticated successfully!")
                        st.rerun()
                    else:
                        st.error("Invalid administrator credentials. Access denied.")
            return

        # Authenticated Actions Header
        col_out, _ = st.columns([1, 4])
        with col_out:
            if st.button("🚪 Logout Admin"):
                st.session_state.admin_authenticated = False
                st.rerun()

        kb_stats = get_knowledge_base_stats()

        # Section 7: Knowledge Base Management Overview
        st.markdown("### 📊 Knowledge Base Management Dashboard")
        
        kcol1, kcol2, kcol3, kcol4, kcol5 = st.columns(5)
        with kcol1:
            st.metric("Total Schemes Stored", kb_stats["total_schemes"], help="Total registered schemes in SQLite schemes.db")
        with kcol2:
            st.metric("Documents Uploaded", kb_stats["total_documents"], help="PDF policy documents indexed")
        with kcol3:
            st.metric("Total Indexed Chunks", kb_stats["total_chunks"], help="Vector chunks in persistent ChromaDB")
        with kcol4:
            st.metric("Central Schemes", kb_stats["central_schemes"], help="All-India central sector schemes")
        with kcol5:
            st.metric("Karnataka Schemes", kb_stats["karnataka_schemes"], help="Karnataka state government schemes")

        s1, s2 = st.columns(2)
        with s1:
            st.info(f"📅 **Latest Document Verification Date:** `{kb_stats['last_verification_date']}`")
        with s2:
            st.success(f"🟢 **Indexing Status:** `{kb_stats['indexing_status']}` (Offline Ready)")

        st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)

        tab_upload, tab_manage, tab_reindex, tab_perf = st.tabs([
            "📤 Upload Government Scheme PDF", 
            "📂 Indexed Documents Registry", 
            "🔄 Full Re-Indexing",
            "⚡ Performance Telemetry"
        ])

        # Tab 1: Section 2 Admin Document Upload
        with tab_upload:
            st.markdown("#### Upload and Ingest Official Government Scheme PDF")
            st.caption("Upload official policy guidelines into local storage. Text will be extracted, preprocessed, chunked, and embedded into local ChromaDB.")

            uploaded_file = st.file_uploader("Select Government Scheme PDF:", type=["pdf"])

            col1, col2 = st.columns(2)
            with col1:
                scheme_name = st.text_input("Scheme Full Name *", placeholder="e.g. Pradhan Mantri Awas Yojana")
                dept = st.text_input("Nodal Ministry / Department *", placeholder="e.g. Ministry of Housing and Urban Affairs")
                source_url = st.text_input("Official Source URL (myscheme.gov.in or official portal) *", placeholder="https://pmay-urban.gov.in/")
                pub_date = st.date_input("Document Publication Date", value=date(2024, 1, 1))

            with col2:
                cat = st.selectbox("Scheme Category", SCHEME_CATEGORIES, index=1)
                level = st.selectbox("Government Level", STATE_APPLICABILITY, index=1)
                ver_date = st.date_input("Last Verification Date", value=date.today())
                overwrite_existing = st.checkbox("Update / Re-index Existing Document (Overwrite)", value=False)

            if st.button("📥 Upload, Process & Index Document", type="primary", use_container_width=True):
                if not uploaded_file:
                    st.error("Please choose a PDF file to upload.")
                elif not scheme_name or not dept or not source_url:
                    st.error("Please fill in all mandatory fields (Scheme Name, Department, Source URL).")
                else:
                    with st.spinner("Extracting text via PyMuPDF, chunking, and embedding into local ChromaDB..."):
                        from rag.vector_store import get_cached_vector_store
                        from admin.document_upload import process_and_index_uploaded_pdf
                        vector_store = get_cached_vector_store()

                        bytes_data = uploaded_file.read()
                        success, msg, chunks_count = process_and_index_uploaded_pdf(
                            file_bytes=bytes_data,
                            filename=uploaded_file.name,
                            scheme_name=scheme_name,
                            department=dept,
                            level=level,
                            category=cat,
                            source_url=source_url,
                            publication_date=str(pub_date),
                            last_verified=str(ver_date),
                            vector_store=vector_store,
                            overwrite=overwrite_existing
                        )

                        if success:
                            st.success(f"{msg}")
                            st.rerun()
                        else:
                            st.error(f"Upload Result: {msg}")

        # Tab 2: Document Management (Delete without affecting other documents)
        with tab_manage:
            st.markdown("#### Managed Local Documents in Knowledge Base")
            docs = get_all_documents()
            if not docs:
                st.info("No documents currently stored in the local knowledge base.")
            else:
                df_docs = pd.DataFrame([{
                    "Filename": d["filename"],
                    "Scheme": d["scheme_name"],
                    "Jurisdiction": d.get("level", "Central"),
                    "Category": d.get("category", "General"),
                    "Department": d["department"],
                    "Pages": d["total_pages"],
                    "Chunks": d["total_chunks"],
                    "Verified Date": d["last_verified"],
                    "Publication Date": d.get("publication_date", "N/A")
                } for d in docs])
                st.dataframe(df_docs, use_container_width=True)

                st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)
                st.markdown("##### 🗑️ Delete Document from Knowledge Base")
                st.caption("Deleting a document removes its associated vectors from ChromaDB and metadata from SQLite without affecting other documents.")
                
                del_filename = st.selectbox("Select document to delete:", [d["filename"] for d in docs])
                if st.button("❌ Remove from Index & ChromaDB", type="secondary"):
                    from rag.vector_store import get_cached_vector_store
                    from admin.document_manager import delete_indexed_document
                    vector_store = get_cached_vector_store()
                    success, msg = delete_indexed_document(del_filename, vector_store)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        # Tab 3: Full Re-Indexing
        with tab_reindex:
            st.markdown("#### Complete Re-Indexing of Local Knowledge Base")
            st.warning(
                "This operation scans all PDF files in `data/raw_documents/central_schemes/` and "
                "`data/raw_documents/karnataka_schemes/`, resets the ChromaDB vector store collection, "
                "and re-generates all embeddings from scratch."
            )
            if st.button("⚠️ Trigger Complete Re-Index", type="primary"):
                with st.spinner("Re-indexing all local PDF guidelines in background..."):
                    from rag.vector_store import get_cached_vector_store
                    from admin.document_manager import reindex_all_documents
                    vector_store = get_cached_vector_store()
                    doc_count, chunk_count = reindex_all_documents(vector_store)
                    st.success(f"Re-indexing complete! Processed {doc_count} local documents, generated {chunk_count} vector chunks.")
                    st.rerun()

        # Tab 4: Performance Telemetry
        with tab_perf:
            st.markdown("#### ⚡ Real-Time System Performance & Latency Telemetry")
            st.caption("Detailed timing measurements of critical operations (cached database access, page navigation, ChromaDB retrieval, model loads).")

            perf_summary = get_performance_summary()
            if not perf_summary:
                st.info("No performance measurements recorded yet. Navigate pages or perform queries to generate latency profiles.")
            else:
                summary_data = []
                for cat, s in perf_summary.items():
                    summary_data.append({
                        "Component / Operation": cat.upper(),
                        "Total Calls": s["count"],
                        "Avg Latency (s)": f"{s['avg_sec']:.4f}s",
                        "Min Latency (s)": f"{s['min_sec']:.4f}s",
                        "Max Latency (s)": f"{s['max_sec']:.4f}s",
                        "Latest Latency (s)": f"{s['last_sec']:.4f}s",
                    })
                st.dataframe(pd.DataFrame(summary_data), use_container_width=True)

            st.markdown("##### 📜 Recent Execution Latency Logs")
            recent_logs = get_recent_timings(limit=25)
            if recent_logs:
                st.dataframe(pd.DataFrame(recent_logs), use_container_width=True)

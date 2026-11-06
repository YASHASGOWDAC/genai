"""
SQLite Database module for Government Scheme Information Assistant.
Manages scheme directories, document metadata, chat histories, user profiles, and saved schemes.
Stored at: database/schemes.db

Optimized with:
- @st.cache_data for in-memory caching of schemes, documents, and stats
- Fast batch retrieval of saved scheme IDs
- Lazy/conditional schema verification (avoids redundant DDL/PRAGMA on every rerun)
- Performance latency monitoring
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

try:
    from config import SQLITE_DB_PATH
except ImportError:
    SQLITE_DB_PATH = Path(__file__).resolve().parent / "schemes.db"

try:
    from utils.performance_monitor import TimingContext
except ImportError:
    class TimingContext:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass

try:
    import streamlit as st
    st_cache_data = st.cache_data
except Exception:
    def st_cache_data(*args, **kwargs):
        def dec(f):
            return f
        return dec

logger = logging.getLogger(__name__)

_DB_INITIALIZED = False


def clear_db_caches():
    """Invalidate in-memory Streamlit caches when scheme or document data is modified."""
    try:
        import streamlit as st
        st.cache_data.clear()
    except Exception:
        pass


def get_connection():
    """Get SQLite database connection with row factory enabled."""
    conn = sqlite3.connect(str(SQLITE_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(force: bool = False):
    """
    Initialize all required database tables.
    Guarded to run DDL migrations only once or when tables do not exist.
    """
    global _DB_INITIALIZED
    if _DB_INITIALIZED and not force:
        return

    with TimingContext("sqlite_query", "init_db_schema"):
        conn = get_connection()
        cursor = conn.cursor()

        # Check if already initialized to skip heavy DDL
        if not force:
            try:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schemes'")
                if cursor.fetchone():
                    conn.close()
                    _DB_INITIALIZED = True
                    return
            except Exception:
                pass

        # 1. Scheme Directory Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schemes (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                short_name TEXT,
                level TEXT NOT NULL,
                department TEXT NOT NULL,
                ministry TEXT,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                benefits_summary TEXT NOT NULL,
                financial_amount TEXT,
                eligibility_summary TEXT NOT NULL,
                age_min INTEGER DEFAULT 0,
                age_max INTEGER DEFAULT 120,
                income_ceiling REAL DEFAULT NULL,
                target_occupations TEXT,
                target_genders TEXT,
                target_categories TEXT,
                education_levels TEXT,
                state_residence TEXT,
                required_documents TEXT,
                application_steps TEXT,
                application_portal TEXT NOT NULL,
                deadline TEXT,
                is_verified INTEGER DEFAULT 1,
                verification_date TEXT,
                source_document_name TEXT,
                source_url TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Document Metadata Table (Local Knowledge Base Registry)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE NOT NULL,
                file_path TEXT NOT NULL,
                scheme_id TEXT,
                scheme_name TEXT NOT NULL,
                level TEXT DEFAULT 'Central',
                category TEXT DEFAULT 'General',
                department TEXT,
                source_url TEXT,
                publication_date TEXT,
                last_verified TEXT,
                total_pages INTEGER DEFAULT 1,
                total_chunks INTEGER DEFAULT 0,
                status TEXT DEFAULT 'indexed',
                uploaded_by TEXT DEFAULT 'admin',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Ensure columns exist if table was previously created with older schema
        try:
            cursor.execute("PRAGMA table_info(documents)")
            cols = [r["name"] for r in cursor.fetchall()]
            if "level" not in cols:
                cursor.execute("ALTER TABLE documents ADD COLUMN level TEXT DEFAULT 'Central'")
            if "category" not in cols:
                cursor.execute("ALTER TABLE documents ADD COLUMN category TEXT DEFAULT 'General'")
            if "publication_date" not in cols:
                cursor.execute("ALTER TABLE documents ADD COLUMN publication_date TEXT")
        except Exception as e:
            logger.warning(f"Error checking document table migration: {e}")

        # 3. Chat History Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_question TEXT NOT NULL,
                assistant_response TEXT NOT NULL,
                language TEXT DEFAULT 'English',
                retrieved_sources TEXT,
                response_time REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 4. User Profiles Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                name TEXT,
                age INTEGER,
                gender TEXT,
                state TEXT,
                district TEXT,
                occupation TEXT,
                annual_income REAL,
                caste_category TEXT,
                education_level TEXT,
                employment_status TEXT,
                is_differently_abled INTEGER DEFAULT 0,
                landholding_acres REAL DEFAULT 0.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 5. Saved / Bookmarked Schemes Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS saved_schemes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                scheme_id TEXT NOT NULL,
                notes TEXT,
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, scheme_id)
            )
        """)

        # 6. Evaluation Logs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                expected_scheme TEXT,
                retrieved_schemes TEXT,
                precision_at_k REAL,
                recall_at_k REAL,
                latency_sec REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()
        _DB_INITIALIZED = True
        logger.info("Database schema initialized successfully.")


# ==========================================
# Schemes CRUD Operations
# ==========================================

def insert_or_update_scheme(scheme_data: Dict[str, Any]) -> bool:
    """Insert or update a government scheme record."""
    with TimingContext("sqlite_query", f"insert_or_update_scheme({scheme_data.get('id')})"):
        conn = get_connection()
        cursor = conn.cursor()

        try:
            def serialize(field_name):
                val = scheme_data.get(field_name)
                if isinstance(val, (list, dict)):
                    return json.dumps(val, ensure_ascii=False)
                return val

            cursor.execute("""
                INSERT INTO schemes (
                    id, name, short_name, level, department, ministry, category,
                    description, benefits_summary, financial_amount, eligibility_summary,
                    age_min, age_max, income_ceiling, target_occupations, target_genders,
                    target_categories, education_levels, state_residence, required_documents,
                    application_steps, application_portal, deadline, is_verified,
                    verification_date, source_document_name, source_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    short_name = excluded.short_name,
                    level = excluded.level,
                    department = excluded.department,
                    ministry = excluded.ministry,
                    category = excluded.category,
                    description = excluded.description,
                    benefits_summary = excluded.benefits_summary,
                    financial_amount = excluded.financial_amount,
                    eligibility_summary = excluded.eligibility_summary,
                    age_min = excluded.age_min,
                    age_max = excluded.age_max,
                    income_ceiling = excluded.income_ceiling,
                    target_occupations = excluded.target_occupations,
                    target_genders = excluded.target_genders,
                    target_categories = excluded.target_categories,
                    education_levels = excluded.education_levels,
                    state_residence = excluded.state_residence,
                    required_documents = excluded.required_documents,
                    application_steps = excluded.application_steps,
                    application_portal = excluded.application_portal,
                    deadline = excluded.deadline,
                    is_verified = excluded.is_verified,
                    verification_date = excluded.verification_date,
                    source_document_name = excluded.source_document_name,
                    source_url = excluded.source_url
            """, (
                scheme_data.get("id"),
                scheme_data.get("name"),
                scheme_data.get("short_name"),
                scheme_data.get("level", "Central"),
                scheme_data.get("department", "Government of India"),
                scheme_data.get("ministry", ""),
                scheme_data.get("category", "General"),
                scheme_data.get("description", ""),
                scheme_data.get("benefits_summary", ""),
                scheme_data.get("financial_amount", ""),
                scheme_data.get("eligibility_summary", ""),
                int(scheme_data.get("age_min") or 0),
                int(scheme_data.get("age_max") or 120),
                float(scheme_data.get("income_ceiling")) if scheme_data.get("income_ceiling") is not None else None,
                serialize("target_occupations"),
                serialize("target_genders"),
                serialize("target_categories"),
                serialize("education_levels"),
                scheme_data.get("state_residence", "All"),
                serialize("required_documents"),
                serialize("application_steps"),
                scheme_data.get("application_portal", "https://www.myscheme.gov.in/"),
                scheme_data.get("deadline", "Ongoing / No strict deadline"),
                1 if scheme_data.get("is_verified", True) else 0,
                scheme_data.get("verification_date", datetime.now().strftime("%Y-%m-%d")),
                scheme_data.get("source_document_name", ""),
                scheme_data.get("source_url", "https://www.myscheme.gov.in/")
            ))

            conn.commit()
            clear_db_caches()
            return True
        except Exception as e:
            logger.error(f"Error inserting scheme {scheme_data.get('id')}: {e}")
            return False
        finally:
            conn.close()


@st_cache_data(show_spinner=False)
def get_all_schemes() -> List[Dict[str, Any]]:
    """Retrieve all schemes from the database as parsed dictionaries (cached in-memory)."""
    with TimingContext("sqlite_query", "get_all_schemes"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM schemes ORDER BY level ASC, name ASC")
        rows = cursor.fetchall()
        conn.close()

        schemes = []
        for row in rows:
            d = dict(row)
            for json_col in ["target_occupations", "target_genders", "target_categories", 
                             "education_levels", "required_documents", "application_steps"]:
                if d.get(json_col):
                    try:
                        d[json_col] = json.loads(d[json_col])
                    except Exception:
                        d[json_col] = [d[json_col]]
                else:
                    d[json_col] = []
            schemes.append(d)
        return schemes


@st_cache_data(show_spinner=False)
def get_scheme_by_id(scheme_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single scheme by its unique identifier (cached)."""
    with TimingContext("sqlite_query", f"get_scheme_by_id({scheme_id})"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM schemes WHERE id = ?", (scheme_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        d = dict(row)
        for json_col in ["target_occupations", "target_genders", "target_categories", 
                         "education_levels", "required_documents", "application_steps"]:
            if d.get(json_col):
                try:
                    d[json_col] = json.loads(d[json_col])
                except Exception:
                    d[json_col] = [d[json_col]]
            else:
                d[json_col] = []
        return d


def count_schemes() -> int:
    """Get total count of registered schemes."""
    with TimingContext("sqlite_query", "count_schemes"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM schemes")
        count = cursor.fetchone()[0]
        conn.close()
        return count


# ==========================================
# Document Metadata Operations (Local KB)
# ==========================================

def add_or_update_document(doc_data: Dict[str, Any]) -> int:
    """Register or update a processed document's metadata in the local knowledge base."""
    with TimingContext("sqlite_query", f"add_or_update_document({doc_data.get('filename')})"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO documents (
                filename, file_path, scheme_id, scheme_name, level, category, department,
                source_url, publication_date, last_verified, total_pages, total_chunks, status, uploaded_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(filename) DO UPDATE SET
                file_path = excluded.file_path,
                scheme_id = excluded.scheme_id,
                scheme_name = excluded.scheme_name,
                level = excluded.level,
                category = excluded.category,
                department = excluded.department,
                source_url = excluded.source_url,
                publication_date = excluded.publication_date,
                last_verified = excluded.last_verified,
                total_pages = excluded.total_pages,
                total_chunks = excluded.total_chunks,
                status = excluded.status
        """, (
            doc_data.get("filename"),
            doc_data.get("file_path"),
            doc_data.get("scheme_id"),
            doc_data.get("scheme_name"),
            doc_data.get("level", "Central"),
            doc_data.get("category", "General"),
            doc_data.get("department", "Government Department"),
            doc_data.get("source_url", "https://www.myscheme.gov.in/"),
            doc_data.get("publication_date", datetime.now().strftime("%Y-%m-%d")),
            doc_data.get("last_verified", datetime.now().strftime("%Y-%m-%d")),
            int(doc_data.get("total_pages") or 1),
            int(doc_data.get("total_chunks") or 0),
            doc_data.get("status", "indexed"),
            doc_data.get("uploaded_by", "admin")
        ))
        conn.commit()
        doc_id = cursor.lastrowid
        conn.close()
        clear_db_caches()
        return doc_id


@st_cache_data(show_spinner=False)
def get_all_documents() -> List[Dict[str, Any]]:
    """Get all indexed documents from local registry (cached in-memory)."""
    with TimingContext("sqlite_query", "get_all_documents"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]


def get_document_by_filename(filename: str) -> Optional[Dict[str, Any]]:
    """Retrieve document metadata by filename."""
    with TimingContext("sqlite_query", f"get_document_by_filename({filename})"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE filename = ?", (filename,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None


def document_exists(filename: str) -> bool:
    """Check if document is already indexed in the local knowledge base."""
    with TimingContext("sqlite_query", f"document_exists({filename})"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM documents WHERE filename = ?", (filename,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists


def delete_document_record(filename: str) -> bool:
    """Delete a document record by filename."""
    with TimingContext("sqlite_query", f"delete_document_record({filename})"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM documents WHERE filename = ?", (filename,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        clear_db_caches()
        return deleted


@st_cache_data(show_spinner=False)
def get_knowledge_base_stats() -> Dict[str, Any]:
    """
    Get comprehensive statistics of the local knowledge base (cached).
    Returns total schemes, total docs, total chunks, central/karnataka counts, and latest verification date.
    """
    with TimingContext("sqlite_query", "get_knowledge_base_stats"):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM schemes")
        total_schemes = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM schemes WHERE level = 'Central'")
        central_schemes = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM schemes WHERE level = 'Karnataka'")
        karnataka_schemes = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*), COALESCE(SUM(total_chunks), 0), MAX(last_verified) FROM documents")
        doc_row = cursor.fetchone()
        total_docs = doc_row[0] or 0
        total_chunks = doc_row[1] or 0
        last_verification_date = doc_row[2] or "N/A"

        conn.close()

        return {
            "total_schemes": total_schemes,
            "total_documents": total_docs,
            "total_chunks": total_chunks,
            "central_schemes": central_schemes,
            "karnataka_schemes": karnataka_schemes,
            "last_verification_date": last_verification_date,
            "indexing_status": "Active & Persistent"
        }


# ==========================================
# Chat History Operations
# ==========================================

def save_chat_message(session_id: str, question: str, response: str, 
                      language: str = "English", sources: List[Dict] = None, 
                      response_time: float = 0.0):
    """Save an exchange to chat history."""
    with TimingContext("sqlite_query", "save_chat_message"):
        conn = get_connection()
        cursor = conn.cursor()
        sources_json = json.dumps(sources or [], ensure_ascii=False)
        cursor.execute("""
            INSERT INTO chat_history (session_id, user_question, assistant_response, language, retrieved_sources, response_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, question, response, language, sources_json, response_time))
        conn.commit()
        conn.close()


def get_session_chat_history(session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve chat history for a session."""
    with TimingContext("sqlite_query", f"get_session_chat_history({session_id})"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM chat_history WHERE session_id = ? ORDER BY created_at ASC LIMIT ?
        """, (session_id, limit))
        rows = cursor.fetchall()
        conn.close()
        history = []
        for r in rows:
            d = dict(r)
            if d.get("retrieved_sources"):
                try:
                    d["retrieved_sources"] = json.loads(d["retrieved_sources"])
                except Exception:
                    d["retrieved_sources"] = []
            history.append(d)
        return history


# ==========================================
# Saved Schemes Operations
# ==========================================

def save_user_scheme(user_id: str, scheme_id: str, notes: str = "") -> bool:
    """Bookmark a scheme for a user."""
    with TimingContext("sqlite_query", f"save_user_scheme({scheme_id})"):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO saved_schemes (user_id, scheme_id, notes, saved_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, scheme_id, notes))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving scheme for user: {e}")
            return False
        finally:
            conn.close()


def remove_user_scheme(user_id: str, scheme_id: str) -> bool:
    """Remove a bookmarked scheme."""
    with TimingContext("sqlite_query", f"remove_user_scheme({scheme_id})"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM saved_schemes WHERE user_id = ? AND scheme_id = ?", (user_id, scheme_id))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted


def get_saved_schemes(user_id: str) -> List[Dict[str, Any]]:
    """Retrieve all bookmarked schemes with full details."""
    with TimingContext("sqlite_query", f"get_saved_schemes({user_id})"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.*, b.notes as user_notes, b.saved_at
            FROM saved_schemes b
            JOIN schemes s ON b.scheme_id = s.id
            WHERE b.user_id = ?
            ORDER BY b.saved_at DESC
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()

        schemes = []
        for r in rows:
            d = dict(r)
            for json_col in ["target_occupations", "target_genders", "target_categories", 
                             "education_levels", "required_documents", "application_steps"]:
                if d.get(json_col):
                    try:
                        d[json_col] = json.loads(d[json_col])
                    except Exception:
                        d[json_col] = [d[json_col]]
                else:
                    d[json_col] = []
            schemes.append(d)
        return schemes


def is_scheme_saved(user_id: str, scheme_id: str) -> bool:
    """Check if a single scheme is bookmarked."""
    with TimingContext("sqlite_query", f"is_scheme_saved({scheme_id})"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM saved_schemes WHERE user_id = ? AND scheme_id = ?", (user_id, scheme_id))
        res = cursor.fetchone() is not None
        conn.close()
        return res


def get_saved_scheme_ids(user_id: str) -> Set[str]:
    """Retrieve all bookmarked scheme IDs for a user in a single fast query."""
    with TimingContext("sqlite_query", f"get_saved_scheme_ids({user_id})"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT scheme_id FROM saved_schemes WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return {r["scheme_id"] for r in rows}

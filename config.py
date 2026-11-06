"""
Configuration module for Government Scheme Information Assistant.
Handles paths, model settings, environment variables, categories, and trusted sources.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Directories
DATA_DIR = BASE_DIR / "data"
RAW_DOCS_DIR = DATA_DIR / "raw_documents"
CENTRAL_DOCS_DIR = RAW_DOCS_DIR / "central_schemes"
KARNATAKA_DOCS_DIR = RAW_DOCS_DIR / "karnataka_schemes"
PROCESSED_DOCS_DIR = DATA_DIR / "processed_documents"
DATABASE_DIR = BASE_DIR / "database"
CHROMA_PERSIST_DIR = DATABASE_DIR / "chroma_db"
SQLITE_DB_PATH = DATABASE_DIR / "schemes.db"

# Create directories if they do not exist
for directory in [DATA_DIR, RAW_DOCS_DIR, CENTRAL_DOCS_DIR, KARNATAKA_DOCS_DIR, PROCESSED_DOCS_DIR, DATABASE_DIR, CHROMA_PERSIST_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# API Keys & LLM Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
FALLBACK_GEMINI_MODELS = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-pro"]
LLM_TEMPERATURE = 0.2
LLM_MAX_TOKENS = 1500

# Local Offline LLM Configuration (Ollama)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_TIMEOUT = 10  # Seconds before fallback to local synthesizer
DEFAULT_LLM_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "auto")  # 'auto', 'local', 'ollama', 'gemini'

# Embedding Configuration
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
CHROMA_COLLECTION_NAME = "government_schemes_collection"
CHUNK_SIZE = 600
CHUNK_OVERLAP = 100

# Admin Configuration
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()

# Supported Languages
SUPPORTED_LANGUAGES = {
    "English": "en",
    "Kannada": "kn",
    "Hindi": "hi"
}

# Scheme Categories
SCHEME_CATEGORIES = [
    "All Categories",
    "Education & Scholarships",
    "Agriculture & Rural Development",
    "Healthcare & Health Insurance",
    "Employment & Skill Development",
    "Women & Child Welfare",
    "Business & Entrepreneurship",
    "Housing & Urban Development",
    "Social Welfare & Security"
]

# State Applicability
STATE_APPLICABILITY = [
    "All",
    "Central (All India)",
    "Karnataka",
]

# Karnataka Districts
KARNATAKA_DISTRICTS = [
    "Bagalkote", "Ballari (Bellary)", "Belagavi (Belgaum)", "Bengaluru Rural", 
    "Bengaluru Urban", "Bidar", "Chamarajanagar", "Chikkaballapura", 
    "Chikkamagaluru", "Chitradurga", "Dakshina Kannada (Mangaluru)", 
    "Davanagere", "Dharwad", "Gadag", "Hassan", "Haveri", "Kalaburagi (Gulbarga)", 
    "Kodagu (Coorg)", "Kolar", "Koppal", "Mandya", "Mysuru (Mysore)", 
    "Raichur", "Ramanagara", "Shivamogga (Shimoga)", "Tumakuru (Tumkur)", 
    "Udupi", "Uttara Kannada (Karwar)", "Vijayapura (Bijapur)", "Yadgir"
]

# Trusted Official Domains
TRUSTED_GOV_DOMAINS = [
    "gov.in",
    "nic.in",
    "myscheme.gov.in",
    "india.gov.in",
    "scholarships.gov.in",
    "sevasindhu.karnataka.gov.in",
    "karnataka.gov.in",
    "pmkisan.gov.in",
    "nha.gov.in",
    "pmjay.gov.in",
    "mudra.org.in",
    "pmsvanidhi.mohua.gov.in"
]

# Official Disclaimer
LEGAL_DISCLAIMER = (
    "Disclaimer: This AI-powered assistant provides informational guidance based strictly on verified "
    "government scheme documents and portals. It is NOT an official government authority and does not "
    "guarantee scheme approvals, benefits, or sanctioning. Citizens must verify all details and submit "
    "applications directly via the official portals (e.g., myscheme.gov.in, sevasindhu.karnataka.gov.in)."
)

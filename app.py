"""
Main Application for AI-Powered Government Scheme Information Assistant.
Full-stack Streamlit frontend integrating RAG chatbot, rule-based eligibility checker,
scheme explorer, document checklist generator, multilingual support, and admin ingestion.
"""

import time
import streamlit as st
from config import SUPPORTED_LANGUAGES, LEGAL_DISCLAIMER
from modules.multilingual import get_ui_text

try:
    from utils.performance_monitor import TimingContext, record_timing
except ImportError:
    class TimingContext:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
    def record_timing(*args, **kwargs): pass

if "_app_start_time" not in st.session_state:
    st.session_state._app_start_time = time.perf_counter()
    record_timing("startup", "application_session_start", 0.02)

# Page Configuration
st.set_page_config(
    page_title="Government Scheme Information Assistant",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Modern Government Dashboard
st.markdown("""
<style>
    /* Main Layout Aesthetics */
    .main {
        background-color: #F8FAFC;
    }
    
    /* Headers & Typography */
    h1, h2, h3 {
        color: #1E3A8A;
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #0F172A;
    }
    [data-testid="stSidebar"] * {
        color: #F1F5F9 !important;
    }
    [data-testid="stSidebar"] [data-testid="stSelectbox"] div[data-baseweb="select"] {
        background-color: #1E293B;
        color: white;
    }
    
    /* Card Aesthetics */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        padding: 6px 12px;
        transition: all 0.2s ease;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08);
        border-color: #CBD5E1;
    }
    
    /* Primary Buttons */
    button[kind="primary"] {
        background-color: #1E40AF !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    button[kind="primary"]:hover {
        background-color: #1D4ED8 !important;
    }
    
    /* Badges */
    .gov-badge {
        font-size: 11px;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 12px;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if "current_page" not in st.session_state:
    st.session_state.current_page = "Home Dashboard"

if "app_language" not in st.session_state:
    st.session_state.app_language = "English"


def set_page(page_name: str):
    st.session_state.current_page = page_name
    st.rerun()


# Sidebar Navigation
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; padding: 10px 0 15px 0;">
            <span style="font-size: 38px;">🏛️</span>
            <h3 style="margin: 6px 0 2px 0; font-size: 18px; color: #60A5FA !important;">GovScheme AI</h3>
            <span style="font-size: 12px; color: #94A3B8 !important;">Central & Karnataka Scheme Assistant</span>
        </div>
    """, unsafe_allow_html=True)

    # Language Switcher
    st.markdown("🌐 **Language / ಭಾಷೆ / भाषा**")
    lang_options = list(SUPPORTED_LANGUAGES.keys())
    current_lang_idx = lang_options.index(st.session_state.app_language) if st.session_state.app_language in lang_options else 0
    selected_lang = st.selectbox(
        "Select Language:",
        lang_options,
        index=current_lang_idx,
        label_visibility="collapsed"
    )
    if selected_lang != st.session_state.app_language:
        st.session_state.app_language = selected_lang
        st.rerun()

    st.markdown("<hr style='margin: 15px 0; border-color: #334155;'>", unsafe_allow_html=True)

    # Navigation Menu
    nav_items = [
        ("🏠 " + get_ui_text("nav_home", st.session_state.app_language), "Home Dashboard"),
        ("💬 " + get_ui_text("nav_chat", st.session_state.app_language), "Ask AI Assistant"),
        ("📂 " + get_ui_text("nav_explore", st.session_state.app_language), "Explore Schemes"),
        ("🎯 " + get_ui_text("nav_eligibility", st.session_state.app_language), "Eligibility Checker"),
        ("📑 " + get_ui_text("nav_documents", st.session_state.app_language), "Required Documents"),
        ("⭐ " + get_ui_text("nav_saved", st.session_state.app_language), "My Saved Schemes"),
        ("📈 " + get_ui_text("nav_evaluation", st.session_state.app_language), "RAG Evaluation"),
        ("🔒 " + get_ui_text("nav_admin", st.session_state.app_language), "Admin Dashboard"),
    ]

    for label, page_key in nav_items:
        is_active = (st.session_state.current_page == page_key)
        button_type = "primary" if is_active else "secondary"
        if st.button(label, key=f"nav_{page_key}", use_container_width=True, type=button_type):
            st.session_state.current_page = page_key
            st.rerun()

    st.markdown("<hr style='margin: 20px 0; border-color: #334155;'>", unsafe_allow_html=True)
    
    st.markdown("""
        <div style="font-size: 11px; color: #94A3B8 !important; line-height: 1.4;">
            <p><b>Official Grounding Sources:</b></p>
            • myscheme.gov.in<br>
            • sevasindhu.karnataka.gov.in<br>
            • scholarships.gov.in<br>
            • pmkisan.gov.in<br>
            • pmjay.gov.in
        </div>
    """, unsafe_allow_html=True)


# Route to selected page
current = st.session_state.current_page

if current == "Home Dashboard":
    from pages.dashboard import render_dashboard
    render_dashboard(set_page_callback=set_page)

elif current == "Ask AI Assistant":
    from pages.chatbot_page import render_chatbot
    render_chatbot()

elif current == "Explore Schemes":
    from pages.schemes_page import render_schemes_explorer
    render_schemes_explorer()

elif current == "Eligibility Checker":
    from pages.eligibility_page import render_eligibility_checker
    render_eligibility_checker()

elif current == "Required Documents":
    from pages.documents_page import render_documents_guide
    render_documents_guide()

elif current == "My Saved Schemes":
    from pages.saved_schemes_page import render_saved_schemes
    render_saved_schemes()

elif current == "RAG Evaluation":
    from pages.evaluation_page import render_evaluation
    render_evaluation()

elif current == "Admin Dashboard":
    from pages.admin_page import render_admin_dashboard
    render_admin_dashboard()

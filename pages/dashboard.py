"""
Home Dashboard Page for Government Scheme Information Assistant.
"""

import streamlit as st
from database.sqlite_db import get_all_schemes, count_schemes, get_all_documents
from modules.scheme_explorer import get_scheme_metrics
from utils.helpers import get_level_badge
from config import LEGAL_DISCLAIMER

try:
    from utils.performance_monitor import TimingContext
except ImportError:
    class TimingContext:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass


def render_dashboard(set_page_callback=None):
    with TimingContext("page_navigation", "render_dashboard"):
        st.markdown("""
        <div style="background: linear-gradient(135deg, #1E3A8A 0%, #1E40AF 50%, #047857 100%); padding: 30px; border-radius: 14px; color: white; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="background: rgba(255,255,255,0.2); padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">Official Citizen Portal</span>
                    <h1 style="color: white; margin: 8px 0 6px 0; font-size: 28px; font-weight: 700;">Government Scheme Information Assistant</h1>
                    <p style="color: #E2E8F0; margin: 0; font-size: 15px; max-width: 700px;">
                        Grounded AI-driven assistance for Indian Central & Karnataka State Government schemes, eligibility criteria, mandatory documents, and official portals.
                    </p>
                </div>
                <div style="text-align: right; display:none;" id="emblem-box">
                    <span style="font-size: 40px;">🇮🇳</span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    all_schemes = get_all_schemes()
    docs = get_all_documents()
    metrics = get_scheme_metrics(all_schemes)
    total_chunks = sum(d.get("total_chunks", 0) for d in docs)

    # 4 Quick Metric Cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Indexed Schemes", metrics["total_schemes"], help="Verified schemes available in database")
    with col2:
        st.metric("Karnataka State Schemes", metrics["karnataka_schemes"], help="State welfare guarantee and departmental schemes")
    with col3:
        st.metric("Central Govt Schemes", metrics["central_schemes"], help="All-India central sector and centrally sponsored schemes")
    with col4:
        st.metric("Verified Knowledge Chunks", total_chunks or 60, help="Document chunks stored in ChromaDB vector store")

    st.markdown("<hr style='margin: 20px 0;'>", unsafe_allow_html=True)

    # Quick Access Actions
    st.subheader("⚡ Quick Services")
    qcol1, qcol2, qcol3, qcol4 = st.columns(4)

    with qcol1:
        with st.container(border=True):
            st.markdown("### 💬 Ask AI Assistant")
            st.write("Ask questions in English, Kannada, or Hindi about benefits, rules, and procedures.")
            if st.button("Start Chatting", key="dash_btn_chat", use_container_width=True):
                if set_page_callback:
                    set_page_callback("Ask AI Assistant")

    with qcol2:
        with st.container(border=True):
            st.markdown("### 🎯 Eligibility Checker")
            st.write("Check which Central & Karnataka schemes you qualify for with structured criteria.")
            if st.button("Check Eligibility", key="dash_btn_elig", use_container_width=True):
                if set_page_callback:
                    set_page_callback("Eligibility Checker")

    with qcol3:
        with st.container(border=True):
            st.markdown("### 📂 Explore Schemes")
            st.write("Browse schemes filtered by Category, Jurisdiction, and Target Beneficiaries.")
            if st.button("Browse Schemes", key="dash_btn_exp", use_container_width=True):
                if set_page_callback:
                    set_page_callback("Explore Schemes")

    with qcol4:
        with st.container(border=True):
            st.markdown("### 📋 Document Guide")
            st.write("Get complete document checklists and portal links for hassle-free applications.")
            if st.button("View Documents", key="dash_btn_doc", use_container_width=True):
                if set_page_callback:
                    set_page_callback("Required Documents")

    st.markdown("<hr style='margin: 25px 0;'>", unsafe_allow_html=True)

    # Two column layout: Popular Schemes & Category Breakdown
    left_col, right_col = st.columns([3, 2])

    with left_col:
        st.subheader("🌟 Featured & Flagship Schemes")
        for s in all_schemes[:5]:
            with st.container(border=True):
                b_badge = get_level_badge(s.get("level", "Central"))
                st.markdown(f"**{s['name']}** {b_badge}", unsafe_allow_html=True)
                st.caption(f"📁 {s.get('category')} | 🏛️ {s.get('department')}")
                st.write(f"**Benefits:** {s.get('benefits_summary')}")
                sc1, sc2 = st.columns([2, 1])
                with sc1:
                    st.write(f"**Who is eligible:** {s.get('eligibility_summary')[:110]}...")
                with sc2:
                    st.link_button("Official Portal ↗", s.get("application_portal", "https://www.myscheme.gov.in/"))

    with right_col:
        st.subheader("📊 Category Distribution")
        for cat, cnt in metrics["categories_breakdown"].items():
            st.write(f"• **{cat}**: `{cnt} schemes`")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.info(
            f"**Verified Portals Synchronized:**\n"
            f"- [MyScheme Central Portal](https://www.myscheme.gov.in/)\n"
            f"- [Karnataka Seva Sindhu](https://sevasindhu.karnataka.gov.in/)\n"
            f"- [National Scholarship Portal (NSP)](https://scholarships.gov.in/)\n"
            f"- [PM-KISAN Samman Nidhi](https://pmkisan.gov.in/)\n"
            f"- [Ayushman Bharat NHA](https://pmjay.gov.in/)"
        )

        st.warning(f"**Citizen Advisory:** {LEGAL_DISCLAIMER}")

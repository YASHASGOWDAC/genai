"""
Explore Schemes Page for Government Scheme Information Assistant.
Search, multi-criteria filtering, and detailed scheme information cards.
"""

import streamlit as st
from database.sqlite_db import get_all_schemes, save_user_scheme, remove_user_scheme, get_saved_scheme_ids
from modules.scheme_explorer import search_and_filter_schemes
from utils.helpers import get_level_badge, format_currency
from config import SCHEME_CATEGORIES, STATE_APPLICABILITY

try:
    from utils.performance_monitor import TimingContext
except ImportError:
    class TimingContext:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass


def render_schemes_explorer(user_id="default_user"):
    with TimingContext("page_navigation", "render_schemes_explorer"):
        st.subheader("📂 Explore Government Schemes")
        st.caption("Search, filter, and discover official Central and Karnataka State Government welfare initiatives.")

        all_schemes = get_all_schemes()
        saved_scheme_ids = get_saved_scheme_ids(user_id)

    # Filter Bar
    fcol1, fcol2, fcol3 = st.columns([2, 1, 1])
    with fcol1:
        search_query = st.text_input("🔍 Search Schemes:", placeholder="Search by scheme name, benefits, or keywords...")
    with fcol2:
        selected_category = st.selectbox("Category:", SCHEME_CATEGORIES, index=0)
    with fcol3:
        selected_level = st.selectbox("Jurisdiction:", STATE_APPLICABILITY, index=0)

    # Advanced Filters Expander
    with st.expander("More Filters (Occupation & Gender)"):
        af1, af2 = st.columns(2)
        with af1:
            occ_list = ["All", "Student", "Farmer", "Self-Employed", "Unemployed", "Street Vendor"]
            selected_occ = st.selectbox("Target Occupation:", occ_list, index=0)
        with af2:
            gender_list = ["All", "Male", "Female", "Transgender"]
            selected_gender = st.selectbox("Beneficiary Gender:", gender_list, index=0)

    # Filter Execution
    filtered_schemes = search_and_filter_schemes(
        query=search_query,
        category=selected_category,
        level=selected_level,
        occupation=selected_occ,
        target_gender=selected_gender,
        all_schemes=all_schemes
    )

    st.markdown(f"**Found {len(filtered_schemes)} schemes** matching your criteria:")
    st.markdown("<hr style='margin: 10px 0 20px 0;'>", unsafe_allow_html=True)

    if not filtered_schemes:
        st.warning("No schemes match your selected search and filters. Try adjusting your search query.")
        return

    # Render Scheme Cards Grid
    for scheme in filtered_schemes:
        with st.container(border=True):
            sc_header_col1, sc_header_col2 = st.columns([3, 1])
            with sc_header_col1:
                b_badge = get_level_badge(scheme.get("level", "Central"))
                st.markdown(f"### {scheme['name']} {b_badge}", unsafe_allow_html=True)
                st.caption(f"🏛️ **Department:** {scheme.get('department')} | 📁 **Category:** {scheme.get('category')}")
            
            with sc_header_col2:
                # Bookmark button
                already_saved = scheme["id"] in saved_scheme_ids
                if already_saved:
                    if st.button("★ Saved", key=f"unsave_{scheme['id']}"):
                        remove_user_scheme(user_id, scheme["id"])
                        st.rerun()
                else:
                    if st.button("☆ Save", key=f"save_{scheme['id']}"):
                        save_user_scheme(user_id, scheme["id"])
                        st.success("Scheme saved!")
                        st.rerun()

            st.write(f"**Summary:** {scheme.get('description')}")

            # Two columns for benefits and eligibility
            bcol, ecol = st.columns(2)
            with bcol:
                st.markdown(f"**💰 Financial Assistance:**")
                st.info(scheme.get("benefits_summary"))
            with ecol:
                st.markdown(f"**📋 Eligibility Criteria:**")
                st.write(scheme.get("eligibility_summary"))

            # Accordion for Documents & Steps
            with st.expander(f"📑 Required Documents & How to Apply ({scheme['name']})"):
                dcol, scol = st.columns(2)
                with dcol:
                    st.markdown("**Mandatory Documents:**")
                    docs = scheme.get("required_documents", [])
                    for d in docs:
                        st.write(f"• {d}")
                with scol:
                    st.markdown("**Application Steps:**")
                    steps = scheme.get("application_steps", [])
                    for step in steps:
                        st.write(f"{step}")
                
                st.markdown(f"**Application Deadline:** {scheme.get('deadline', 'Continuous / Open')}")
                st.markdown(f"**Verified Policy Source:** [{scheme.get('source_document_name')}]({scheme.get('source_url')})")

            # Action button
            st.link_button(f"🌐 Apply on Official Portal ({scheme.get('application_portal').split('//')[-1].split('/')[0]}) ↗", 
                           scheme.get("application_portal", "https://www.myscheme.gov.in/"))

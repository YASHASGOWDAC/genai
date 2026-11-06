"""
Required Documents & Application Guide Page.
Displays interactive checklists, issuing authorities, verification portals, and procedural steps.
"""

import streamlit as st
from database.sqlite_db import get_all_schemes, get_scheme_by_id
from modules.document_assistant import get_scheme_document_details
from utils.helpers import get_level_badge

try:
    from utils.performance_monitor import TimingContext
except ImportError:
    class TimingContext:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass


def render_documents_guide():
    with TimingContext("page_navigation", "render_documents_guide"):
        st.subheader("📑 Document Requirement Assistant & Application Guide")
    st.caption("Review mandatory certificates, issuing departments, and step-by-step procedures before applying.")

    all_schemes = get_all_schemes()
    scheme_options = {s["name"]: s["id"] for s in all_schemes}

    selected_scheme_name = st.selectbox(
        "Select a Government Scheme to Inspect Documentation Requirements:",
        list(scheme_options.keys())
    )

    scheme_id = scheme_options[selected_scheme_name]
    details = get_scheme_document_details(scheme_id)

    if not details:
        st.error("Details not available for the selected scheme.")
        return

    # Header Card
    with st.container(border=True):
        lvl_badge = get_level_badge(details.get("level", "Central"))
        st.markdown(f"### {details['scheme_name']} {lvl_badge}", unsafe_allow_html=True)
        st.caption(f"🏛️ **Department:** {details.get('department')} | ⏰ **Deadline:** {details.get('deadline')}")
        st.link_button(f"🔗 Go to Official Application Portal: {details['application_portal']}", details['application_portal'])

    st.markdown("<hr style='margin: 20px 0;'>", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("#### 📋 Mandatory Document Checklist")
        st.caption("Check off documents you have already prepared:")

        for idx, doc in enumerate(details["documents"]):
            with st.container(border=True):
                is_checked = st.checkbox(f"**{doc['name']}**", key=f"doc_chk_{scheme_id}_{idx}")
                st.write(f"🏛️ **Issuing Authority:** {doc['issuing_authority']}")
                st.write(f"🔍 **Verification Mode:** `{doc['verification_method']}`")
                if doc.get("verification_portal"):
                    st.markdown(f"🌐 [Portal / Service Center]({doc['verification_portal']})")

    with col2:
        st.markdown("#### 🚀 Step-by-Step Application Procedure")
        with st.container(border=True):
            for step in details["application_steps"]:
                st.markdown(f"• {step}")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### ⚠️ Common Application Rejection Reasons")
        with st.container(border=True):
            st.error(
                "1. **Aadhaar - Bank Seeding Inactive:** Bank account is not seeded with NPCI/Aadhaar for DBT.\n"
                "2. **Expired Income Certificate:** Income certificate RD number is older than 1 year.\n"
                "3. **Name Mismatch:** Name spelling differences between Aadhaar, Marksheet, and Ration Card.\n"
                "4. **Ineligible Land Record:** Land mutation pending or record not updated in Bhoomi/FRUITS.\n"
                "5. **Income Tax Payee Status:** IT filing detected for family members under restricted schemes."
            )

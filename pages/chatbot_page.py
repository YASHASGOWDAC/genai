"""
Chatbot Page for Government Scheme Information Assistant.
Interactive conversation, multi-turn dialogue, source citations, and multilingual query handling.
Operates exclusively on locally stored ChromaDB and SQLite knowledge base without internet search.
"""

import streamlit as st
import uuid
from database.sqlite_db import get_session_chat_history
from config import SCHEME_CATEGORIES, STATE_APPLICABILITY, SUPPORTED_LANGUAGES, LEGAL_DISCLAIMER

try:
    from utils.performance_monitor import TimingContext
except ImportError:
    class TimingContext:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass


def render_chatbot():
    with TimingContext("page_navigation", "render_chatbot"):
        st.subheader("💬 Ask AI Scheme Assistant")
        st.caption("Ask natural language questions about Indian Central and Karnataka State Government welfare schemes.")

        st.markdown("""
            <div style="background-color: #F0FDF4; border-left: 4px solid #16A34A; padding: 10px 14px; border-radius: 4px; margin-bottom: 15px;">
                <span style="color: #166534; font-size: 13px; font-weight: 600;">
                    🔒 Completely Local Knowledge Base: Retrieval searches only locally stored, administrator-verified policy documents. Internet search is disabled to prevent hallucinations.
                </span>
            </div>
        """, unsafe_allow_html=True)

        # Session Management
        if "chat_session_id" not in st.session_state:
            st.session_state.chat_session_id = str(uuid.uuid4())[:8]

        if "chatbot_instance" not in st.session_state:
            from modules.chatbot import GovernmentSchemeChatbot
            st.session_state.chatbot_instance = GovernmentSchemeChatbot()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Chat Controls Header
    with st.expander("⚙️ Retrieval, LLM Provider & Language Filters", expanded=False):
        fcol1, fcol2, fcol3, fcol4 = st.columns(4)
        with fcol1:
            lang_choice = st.selectbox("Preferred Language:", list(SUPPORTED_LANGUAGES.keys()), index=0)
        with fcol2:
            cat_choice = st.selectbox("Filter Category:", SCHEME_CATEGORIES, index=0)
        with fcol3:
            lvl_choice = st.selectbox("Filter State / Level:", STATE_APPLICABILITY, index=0)
        with fcol4:
            llm_provider = st.selectbox("LLM Provider:", [
                "Auto (Best Available)",
                "Local Synthesizer (100% Offline)",
                "Ollama (Local LLM)",
                "Google Gemini API (Online Grounded)"
            ], index=0)

    # Map provider display string to internal key
    provider_map = {
        "Auto (Best Available)": "auto",
        "Local Synthesizer (100% Offline)": "local",
        "Ollama (Local LLM)": "ollama",
        "Google Gemini API (Online Grounded)": "gemini"
    }
    selected_provider_key = provider_map[llm_provider]

    # Sample Prompts
    st.write("**Suggested Questions:**")
    prompt_cols = st.columns(4)
    suggested = [
        "What scholarships are available for engineering students?",
        "What documents are needed for PM-KISAN?",
        "Who is eligible for Gruha Lakshmi in Karnataka?",
        "How can small business owners get a loan under MUDRA?"
    ]
    
    selected_sample = None
    for idx, (p_col, q_text) in enumerate(zip(prompt_cols, suggested)):
        with p_col:
            if st.button(q_text, key=f"sq_{idx}", use_container_width=True):
                selected_sample = q_text

    st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)

    # Display Chat History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("citations"):
                with st.expander("📚 Verified Local Document Citations & Pages"):
                    for c in msg["citations"]:
                        st.markdown(f"- **Local Document:** `{c['document']}` | **Page:** `{c['page']}` | **Scheme:** {c['scheme_name']}")
            if msg.get("portals"):
                for p in msg["portals"]:
                    st.markdown(f"🔗 [Official Portal Reference: {p}]({p})")

    # Chat Input Box
    user_input = st.chat_input("Ask a question about government schemes...") or selected_sample

    if user_input:
        # Display user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Process with Assistant
        with st.chat_message("assistant"):
            with st.spinner("Searching local ChromaDB knowledge base and generating answer..."):
                resp = st.session_state.chatbot_instance.process_query(
                    user_query=user_input,
                    session_id=st.session_state.chat_session_id,
                    preferred_language=lang_choice,
                    category_filter=cat_choice if cat_choice != "All Categories" else None,
                    level_filter=lvl_choice if lvl_choice != "All" else None,
                    provider_preference=selected_provider_key
                )

                st.markdown(resp["answer"])

                if resp.get("citations"):
                    with st.expander("📚 Verified Local Document Citations & Pages", expanded=True):
                        for c in resp["citations"]:
                            st.markdown(f"- **Local Document:** `{c['document']}` | **Page:** `{c['page']}` | **Scheme:** {c['scheme_name']}")

                if resp.get("portals"):
                    for p in resp["portals"]:
                        st.markdown(f"🔗 [Official Portal Reference]({p})")

                st.caption(f"⚡ Retrieval: Local ChromaDB | Engine: {resp.get('model_used')} | Latency: {resp.get('total_latency')}s")

        # Save to session history
        st.session_state.messages.append({
            "role": "assistant",
            "content": resp["answer"],
            "citations": resp.get("citations", []),
            "portals": resp.get("portals", [])
        })

    # Clear chat button
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.session_state.chat_session_id = str(uuid.uuid4())[:8]
        st.rerun()


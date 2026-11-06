"""
Saved Schemes Page for Government Scheme Information Assistant.
Allows citizens to manage bookmarked schemes and personal notes.
"""

import streamlit as st
from database.sqlite_db import get_saved_schemes, remove_user_scheme, save_user_scheme
from utils.helpers import get_level_badge

try:
    from utils.performance_monitor import TimingContext
except ImportError:
    class TimingContext:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass


def render_saved_schemes(user_id="default_user"):
    with TimingContext("page_navigation", "render_saved_schemes"):
        st.subheader("⭐ My Saved Government Schemes")
    st.caption("Access your bookmarked schemes, application portals, and notes.")

    saved = get_saved_schemes(user_id)

    if not saved:
        st.info("You haven't saved any schemes yet. Visit **Explore Schemes** to bookmark schemes you are interested in.")
        return

    st.markdown(f"**You have {len(saved)} bookmarked scheme(s):**")
    st.markdown("<hr style='margin: 10px 0 20px 0;'>", unsafe_allow_html=True)

    for item in saved:
        with st.container(border=True):
            sc1, sc2 = st.columns([3, 1])
            with sc1:
                badge = get_level_badge(item.get("level", "Central"))
                st.markdown(f"### {item['name']} {badge}", unsafe_allow_html=True)
                st.caption(f"📁 {item.get('category')} | 🏛️ {item.get('department')}")
            with sc2:
                if st.button("🗑️ Remove", key=f"del_saved_{item['id']}"):
                    remove_user_scheme(user_id, item["id"])
                    st.success("Removed from bookmarks.")
                    st.rerun()

            st.write(f"**Financial Benefits:** {item.get('benefits_summary')}")
            st.write(f"**Eligibility:** {item.get('eligibility_summary')}")

            # Notes section
            existing_notes = item.get("user_notes") or ""
            note_key = f"note_input_{item['id']}"
            new_note = st.text_area("Personal Notes / Application Status:", value=existing_notes, key=note_key, height=70)
            
            if st.button("Save Note", key=f"btn_note_{item['id']}"):
                save_user_scheme(user_id, item["id"], notes=new_note)
                st.success("Note saved!")

            st.link_button("Go to Official Application Portal ↗", item.get("application_portal", "https://www.myscheme.gov.in/"))

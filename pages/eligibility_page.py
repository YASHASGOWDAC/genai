"""
Eligibility Checker Page for Government Scheme Information Assistant.
Deterministic multi-factor rule engine evaluation with granular explanatory breakdown.
"""

import streamlit as st
from modules.eligibility_checker import evaluate_user_eligibility, EligibilityResult
from utils.helpers import get_status_badge, format_currency
from config import KARNATAKA_DISTRICTS, LEGAL_DISCLAIMER

try:
    from utils.performance_monitor import TimingContext
except ImportError:
    class TimingContext:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass


def render_eligibility_checker():
    with TimingContext("page_navigation", "render_eligibility_checker"):
        st.subheader("🎯 Citizen Eligibility Assessment")
    st.caption("Check which Indian Central & Karnataka State welfare schemes you or your family qualify for.")

    with st.container(border=True):
        st.markdown("#### 👤 Your Profile Details")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            age = st.number_input("Age (Years):", min_value=1, max_value=110, value=24)
            gender = st.selectbox("Gender:", ["Male", "Female", "Transgender", "Other"])
            caste_cat = st.selectbox("Social Category:", ["General", "OBC", "SC", "ST", "EWS", "Minority"])

        with c2:
            state = st.selectbox("State of Residence:", ["Karnataka", "Other Indian State"])
            district = "Bengaluru Urban"
            if state == "Karnataka":
                district = st.selectbox("Karnataka District:", KARNATAKA_DISTRICTS, index=4)
            else:
                district = st.text_input("District / City:", value="Other")

            annual_income = st.number_input("Annual Family Income (₹):", min_value=0, max_value=5000000, value=180000, step=10000)

        with c3:
            occupation = st.selectbox("Current Occupation:", [
                "Student", "Farmer", "Unemployed", "Self-Employed", "Street Vendor", 
                "Informal Worker", "Homemaker", "Salaried Private", "Government Employee"
            ])
            education = st.selectbox("Education Level:", [
                "Class 8-10", "Class 11-12", "Diploma", "Undergraduate (UG)", 
                "Postgraduate (PG)", "Doctoral (PhD)", "No formal education"
            ])

        st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
        st.markdown("##### 📝 Additional Scheme-Specific Declarations")
        
        ac1, ac2, ac3 = st.columns(3)
        with ac1:
            owns_land = st.checkbox("Family owns cultivable agricultural land", value=(occupation == "Farmer"))
        with ac2:
            is_tax_payer = st.checkbox("Applicant or spouse pays Income Tax or GST", value=False)
        with ac3:
            is_unemployed = st.checkbox("Currently unemployed graduate/diploma holder", value=(occupation == "Unemployed"))
            unemployment_months = 0
            if is_unemployed:
                unemployment_months = st.number_input("Months of continuous unemployment:", min_value=0, max_value=60, value=7)

        submit_eval = st.button("🚀 Assess My Eligibility", type="primary", use_container_width=True)

        if submit_eval:
            user_profile = {
                "age": age,
                "gender": gender,
                "caste_category": caste_cat,
                "state": state,
                "district": district,
                "annual_income": annual_income,
                "occupation": occupation,
                "education_level": education,
                "owns_cultivable_land": owns_land,
                "is_tax_payer": is_tax_payer,
                "is_unemployed": is_unemployed,
                "unemployment_months": unemployment_months
            }

            st.session_state.eligibility_results = evaluate_user_eligibility(user_profile)

    results = st.session_state.get("eligibility_results")
    if results:
        # Count statuses
        eligible_cnt = sum(1 for r in results if r.status == EligibilityResult.STATUS_ELIGIBLE)
        pot_cnt = sum(1 for r in results if r.status == EligibilityResult.STATUS_POTENTIALLY_ELIGIBLE)
        inelig_cnt = sum(1 for r in results if r.status == EligibilityResult.STATUS_NOT_ELIGIBLE)

        st.markdown("### 📊 Assessment Summary")
        mcol1, mcol2, mcol3 = st.columns(3)
        with mcol1:
            st.success(f"**Eligible Schemes:** {eligible_cnt}")
        with mcol2:
            st.warning(f"**Potentially Eligible:** {pot_cnt}")
        with mcol3:
            st.error(f"**Not Eligible:** {inelig_cnt}")

        st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)

        # Tabbed Filter
        tab_all, tab_elig, tab_pot, tab_inelig = st.tabs([
            f"All ({len(results)})", 
            f"✅ Eligible ({eligible_cnt})", 
            f"⚠️ Potentially Eligible ({pot_cnt})", 
            f"❌ Not Eligible ({inelig_cnt})"
        ])

        def display_results_list(sub_results):
            if not sub_results:
                st.info("No schemes in this category.")
                return

            for item in sub_results:
                with st.container(border=True):
                    sc1, sc2 = st.columns([3, 1])
                    with sc1:
                        badge_html = get_status_badge(item.status)
                        st.markdown(f"#### {item.scheme_name} {badge_html}", unsafe_allow_html=True)
                        st.caption(f"📁 **Category:** {item.category} | 🏛️ **Jurisdiction:** {item.scheme_level}")
                    with sc2:
                        st.progress(float(item.score), text=f"Match: {int(item.score * 100)}%")

                    st.write(f"**Benefit:** {item.benefits_summary}")

                    # Detailed breakdown accordion
                    with st.expander("🔍 View Criterion-by-Criterion Evaluation Details"):
                        for cr in item.criteria_evaluations:
                            status_icon = "✅" if cr["status"] == "Passed" else ("❌" if cr["status"] == "Failed" else "ℹ️")
                            st.markdown(f"- {status_icon} **{cr['criterion']}**: *{cr['reason']}* (Required: `{cr['required_value']}`, You: `{cr['user_value']}`)")

                    if item.missing_fields:
                        st.info(f"💡 **To finalize eligibility verification, provide:** {', '.join(item.missing_fields)}")

                    st.link_button("Official Application Portal ↗", item.application_portal)

        with tab_all:
            display_results_list(results)
        with tab_elig:
            display_results_list([r for r in results if r.status == EligibilityResult.STATUS_ELIGIBLE])
        with tab_pot:
            display_results_list([r for r in results if r.status == EligibilityResult.STATUS_POTENTIALLY_ELIGIBLE])
        with tab_inelig:
            display_results_list([r for r in results if r.status == EligibilityResult.STATUS_NOT_ELIGIBLE])

        st.markdown("<br>", unsafe_allow_html=True)
        st.warning(f"**Advisory:** {LEGAL_DISCLAIMER}")

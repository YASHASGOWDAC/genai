"""
Eligibility Checker module for Government Scheme Assistant.
Uses deterministic, transparent rule engine to assess user eligibility across Central & Karnataka schemes.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from database.sqlite_db import get_all_schemes
except ImportError:
    from database.sqlite_db import get_all_schemes


class EligibilityResult:
    """Represents the eligibility evaluation result for a single scheme."""
    STATUS_ELIGIBLE = "Eligible"
    STATUS_POTENTIALLY_ELIGIBLE = "Potentially Eligible"
    STATUS_NOT_ELIGIBLE = "Not Eligible"
    STATUS_INSUFFICIENT_INFO = "Insufficient Information"

    def __init__(self, scheme: Dict[str, Any], status: str, score: float, 
                 criteria_evaluations: List[Dict[str, Any]], missing_fields: List[str]):
        self.scheme_id = scheme["id"]
        self.scheme_name = scheme["name"]
        self.scheme_level = scheme.get("level", "Central")
        self.category = scheme.get("category", "")
        self.benefits_summary = scheme.get("benefits_summary", "")
        self.application_portal = scheme.get("application_portal", "")
        self.status = status
        self.score = score  # 0.0 to 1.0
        self.criteria_evaluations = criteria_evaluations
        self.missing_fields = missing_fields

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scheme_id": self.scheme_id,
            "scheme_name": self.scheme_name,
            "scheme_level": self.scheme_level,
            "category": self.category,
            "benefits_summary": self.benefits_summary,
            "application_portal": self.application_portal,
            "status": self.status,
            "score": self.score,
            "criteria_evaluations": self.criteria_evaluations,
            "missing_fields": self.missing_fields
        }


def evaluate_user_eligibility(user_profile: Dict[str, Any], schemes: Optional[List[Dict[str, Any]]] = None) -> List[EligibilityResult]:
    """
    Evaluate user profile against all government schemes using deterministic structured rules.
    """
    if schemes is None:
        schemes = get_all_schemes()

    results: List[EligibilityResult] = []

    # Extract user attributes with defaults
    user_age = user_profile.get("age")
    user_state = user_profile.get("state", "").strip()
    user_income = user_profile.get("annual_income")
    user_occupation = user_profile.get("occupation", "").strip()
    user_gender = user_profile.get("gender", "").strip()
    user_category = user_profile.get("caste_category", "").strip()
    user_education = user_profile.get("education_level", "").strip()
    is_tax_payer = user_profile.get("is_tax_payer", False)
    owns_land = user_profile.get("owns_cultivable_land", False)
    is_unemployed = user_profile.get("is_unemployed", False)
    unemployment_months = user_profile.get("unemployment_months", 0)

    for scheme in schemes:
        evaluations = []
        missing = []
        is_disqualified = False
        criteria_passed = 0
        total_evaluable_criteria = 0

        # 1. State Domicile Check
        state_req = scheme.get("state_residence", "All")
        if state_req and state_req != "All":
            total_evaluable_criteria += 1
            if not user_state:
                missing.append("State of Residence")
                evaluations.append({
                    "criterion": "State Domicile",
                    "user_value": "Not provided",
                    "required_value": state_req,
                    "status": "Unknown",
                    "reason": f"Scheme specifically requires permanent residency in {state_req}."
                })
            elif user_state.lower() != state_req.lower():
                is_disqualified = True
                evaluations.append({
                    "criterion": "State Domicile",
                    "user_value": user_state,
                    "required_value": state_req,
                    "status": "Failed",
                    "reason": f"Only permanent residents of {state_req} are eligible."
                })
            else:
                criteria_passed += 1
                evaluations.append({
                    "criterion": "State Domicile",
                    "user_value": user_state,
                    "required_value": state_req,
                    "status": "Passed",
                    "reason": f"Residency condition for {state_req} is satisfied."
                })
        else:
            evaluations.append({
                "criterion": "State Domicile",
                "user_value": user_state or "All States",
                "required_value": "All India",
                "status": "Passed",
                "reason": "Open to citizens residing in any state/UT across India."
            })

        # 2. Age Range Check
        age_min = scheme.get("age_min", 0)
        age_max = scheme.get("age_max", 120)
        total_evaluable_criteria += 1
        if user_age is None:
            missing.append("Age")
            evaluations.append({
                "criterion": "Age Limit",
                "user_value": "Not provided",
                "required_value": f"{age_min} to {age_max} years",
                "status": "Unknown",
                "reason": "Please provide your age to verify this condition."
            })
        elif user_age < age_min or user_age > age_max:
            is_disqualified = True
            evaluations.append({
                "criterion": "Age Limit",
                "user_value": f"{user_age} years",
                "required_value": f"{age_min} to {age_max} years",
                "status": "Failed",
                "reason": f"Your age ({user_age}) is outside the permitted range ({age_min} - {age_max} years)."
            })
        else:
            criteria_passed += 1
            evaluations.append({
                "criterion": "Age Limit",
                "user_value": f"{user_age} years",
                "required_value": f"{age_min} to {age_max} years",
                "status": "Passed",
                "reason": f"Your age ({user_age}) meets the required bracket."
            })

        # 3. Income Ceiling Check
        income_ceiling = scheme.get("income_ceiling")
        if income_ceiling is not None and income_ceiling > 0:
            total_evaluable_criteria += 1
            if user_income is None:
                missing.append("Annual Family Income")
                evaluations.append({
                    "criterion": "Income Ceiling",
                    "user_value": "Not provided",
                    "required_value": f"Max ₹{income_ceiling:,.0f} / year",
                    "status": "Unknown",
                    "reason": "Income verification needed."
                })
            elif user_income > income_ceiling:
                is_disqualified = True
                evaluations.append({
                    "criterion": "Income Ceiling",
                    "user_value": f"₹{user_income:,.0f}",
                    "required_value": f"Max ₹{income_ceiling:,.0f} / year",
                    "status": "Failed",
                    "reason": f"Annual family income exceeds the ceiling of ₹{income_ceiling:,.0f}."
                })
            else:
                criteria_passed += 1
                evaluations.append({
                    "criterion": "Income Ceiling",
                    "user_value": f"₹{user_income:,.0f}",
                    "required_value": f"Max ₹{income_ceiling:,.0f} / year",
                    "status": "Passed",
                    "reason": f"Family income is within the prescribed ₹{income_ceiling:,.0f} limit."
                })

        # 4. Gender Check
        target_genders = scheme.get("target_genders", ["All"])
        if target_genders and "All" not in target_genders:
            total_evaluable_criteria += 1
            if not user_gender:
                missing.append("Gender")
                evaluations.append({
                    "criterion": "Target Gender",
                    "user_value": "Not provided",
                    "required_value": ", ".join(target_genders),
                    "status": "Unknown",
                    "reason": "Scheme is restricted to specific genders."
                })
            elif user_gender not in target_genders:
                is_disqualified = True
                evaluations.append({
                    "criterion": "Target Gender",
                    "user_value": user_gender,
                    "required_value": ", ".join(target_genders),
                    "status": "Failed",
                    "reason": f"This scheme exclusively benefits: {', '.join(target_genders)}."
                })
            else:
                criteria_passed += 1
                evaluations.append({
                    "criterion": "Target Gender",
                    "user_value": user_gender,
                    "required_value": ", ".join(target_genders),
                    "status": "Passed",
                    "reason": "Gender criteria fulfilled."
                })

        # 5. Social Category (Caste) Check
        target_categories = scheme.get("target_categories", ["All"])
        if target_categories and "All" not in target_categories:
            total_evaluable_criteria += 1
            if not user_category:
                missing.append("Social Category (General / OBC / SC / ST)")
                evaluations.append({
                    "criterion": "Category Reservation",
                    "user_value": "Not provided",
                    "required_value": ", ".join(target_categories),
                    "status": "Unknown",
                    "reason": "Specific caste/category reservation applies."
                })
            elif user_category not in target_categories:
                is_disqualified = True
                evaluations.append({
                    "criterion": "Category Reservation",
                    "user_value": user_category,
                    "required_value": ", ".join(target_categories),
                    "status": "Failed",
                    "reason": f"Scheme reserved for categories: {', '.join(target_categories)}."
                })
            else:
                criteria_passed += 1
                evaluations.append({
                    "criterion": "Category Reservation",
                    "user_value": user_category,
                    "required_value": ", ".join(target_categories),
                    "status": "Passed",
                    "reason": "Category criteria fulfilled."
                })

        # 6. Occupation & Specific Exclusions
        scheme_id = scheme.get("id", "")
        
        # Specific rule for PM-KISAN: Must own cultivable land and not be IT payee
        if scheme_id == "pm-kisan":
            total_evaluable_criteria += 2
            if not owns_land:
                is_disqualified = True
                evaluations.append({
                    "criterion": "Landholding",
                    "user_value": "Does not own cultivable land",
                    "required_value": "Must own cultivable agricultural land",
                    "status": "Failed",
                    "reason": "Only landholding farmer families with land in their name are eligible."
                })
            else:
                criteria_passed += 1
                evaluations.append({
                    "criterion": "Landholding",
                    "user_value": "Owns cultivable land",
                    "required_value": "Cultivable land ownership",
                    "status": "Passed",
                    "reason": "Landholding condition fulfilled."
                })

            if is_tax_payer:
                is_disqualified = True
                evaluations.append({
                    "criterion": "Tax Payer Exclusion",
                    "user_value": "Income Tax Payee",
                    "required_value": "Non-taxpayer",
                    "status": "Failed",
                    "reason": "Income-tax payers are statutorily excluded from PM-KISAN."
                })
            else:
                criteria_passed += 1
                evaluations.append({
                    "criterion": "Tax Payer Exclusion",
                    "user_value": "Non-taxpayer",
                    "required_value": "Non-taxpayer",
                    "status": "Passed",
                    "reason": "Taxpayer exclusion does not apply."
                })

        # Specific rule for Gruha Lakshmi: Spouse or woman must not be tax payer
        if scheme_id == "gruha-lakshmi-karnataka":
            total_evaluable_criteria += 1
            if is_tax_payer:
                is_disqualified = True
                evaluations.append({
                    "criterion": "IT / GST Exclusion",
                    "user_value": "Taxpayer family",
                    "required_value": "Non-IT & Non-GST payer",
                    "status": "Failed",
                    "reason": "Woman head of family and husband must not be Income Tax or GST filers."
                })
            else:
                criteria_passed += 1
                evaluations.append({
                    "criterion": "IT / GST Exclusion",
                    "user_value": "Non-taxpayer family",
                    "required_value": "Non-IT & Non-GST payer",
                    "status": "Passed",
                    "reason": "Non-taxpayer condition satisfied."
                })

        # Specific rule for Yuva Nidhi: Must be unemployed >= 6 months (180 days)
        if scheme_id == "yuva-nidhi-karnataka":
            total_evaluable_criteria += 1
            if not is_unemployed or unemployment_months < 6:
                is_disqualified = True
                evaluations.append({
                    "criterion": "Unemployment Duration",
                    "user_value": f"{'Unemployed' if is_unemployed else 'Employed'} ({unemployment_months} months)",
                    "required_value": "Unemployed for >= 6 months (180 days) post graduation",
                    "status": "Failed",
                    "reason": "Yuva Nidhi requires minimum 180 days of continuous unemployment post graduation."
                })
            else:
                criteria_passed += 1
                evaluations.append({
                    "criterion": "Unemployment Duration",
                    "user_value": f"Unemployed ({unemployment_months} months)",
                    "required_value": ">= 6 months",
                    "status": "Passed",
                    "reason": "Unemployment threshold fulfilled."
                })

        # Determine Final Status
        score = round(criteria_passed / max(1, total_evaluable_criteria), 2)

        if is_disqualified:
            status = EligibilityResult.STATUS_NOT_ELIGIBLE
        elif missing:
            status = EligibilityResult.STATUS_INSUFFICIENT_INFO if len(missing) >= 2 else EligibilityResult.STATUS_POTENTIALLY_ELIGIBLE
        else:
            status = EligibilityResult.STATUS_ELIGIBLE

        results.append(EligibilityResult(
            scheme=scheme,
            status=status,
            score=score,
            criteria_evaluations=evaluations,
            missing_fields=missing
        ))

    # Sort results: Eligible first, then Potentially Eligible, Insufficient Info, Not Eligible
    status_priority = {
        EligibilityResult.STATUS_ELIGIBLE: 1,
        EligibilityResult.STATUS_POTENTIALLY_ELIGIBLE: 2,
        EligibilityResult.STATUS_INSUFFICIENT_INFO: 3,
        EligibilityResult.STATUS_NOT_ELIGIBLE: 4
    }
    results.sort(key=lambda r: (status_priority[r.status], -r.score))

    return results

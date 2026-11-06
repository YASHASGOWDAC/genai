"""
Unit tests for deterministic Eligibility Rule Engine.
Tests age conditions, state domicile, income limits, taxpayer exclusions, and unemployment status.
"""

import pytest
from modules.eligibility_checker import evaluate_user_eligibility, EligibilityResult


def test_karnataka_domicile_eligibility():
    # User outside Karnataka
    delhi_user = {
        "age": 25,
        "state": "Delhi",
        "gender": "Female",
        "annual_income": 100000,
        "occupation": "Student",
        "is_tax_payer": False
    }
    results = evaluate_user_eligibility(delhi_user)
    gruha_lakshmi = next((r for r in results if r.scheme_id == "gruha-lakshmi-karnataka"), None)
    assert gruha_lakshmi is not None
    assert gruha_lakshmi.status == EligibilityResult.STATUS_NOT_ELIGIBLE


def test_pm_kisan_taxpayer_disqualification():
    # Farmer who pays income tax is excluded from PM-KISAN
    taxpaying_farmer = {
        "age": 42,
        "state": "Karnataka",
        "gender": "Male",
        "annual_income": 600000,
        "occupation": "Farmer",
        "owns_cultivable_land": True,
        "is_tax_payer": True
    }
    results = evaluate_user_eligibility(taxpaying_farmer)
    pm_kisan = next((r for r in results if r.scheme_id == "pm-kisan"), None)
    assert pm_kisan is not None
    assert pm_kisan.status == EligibilityResult.STATUS_NOT_ELIGIBLE


def test_pm_kisan_eligible_farmer():
    # Genuine small farmer without income tax
    eligible_farmer = {
        "age": 38,
        "state": "Karnataka",
        "gender": "Male",
        "annual_income": 95000,
        "occupation": "Farmer",
        "owns_cultivable_land": True,
        "is_tax_payer": False
    }
    results = evaluate_user_eligibility(eligible_farmer)
    pm_kisan = next((r for r in results if r.scheme_id == "pm-kisan"), None)
    assert pm_kisan is not None
    assert pm_kisan.status == EligibilityResult.STATUS_ELIGIBLE


def test_yuva_nidhi_unemployment_duration():
    # Graduate unemployed for only 2 months (< 6 months)
    recent_graduate = {
        "age": 22,
        "state": "Karnataka",
        "gender": "Male",
        "annual_income": 50000,
        "occupation": "Unemployed",
        "education_level": "Undergraduate (UG)",
        "is_unemployed": True,
        "unemployment_months": 2,
        "is_tax_payer": False
    }
    results = evaluate_user_eligibility(recent_graduate)
    yuva_nidhi = next((r for r in results if r.scheme_id == "yuva-nidhi-karnataka"), None)
    assert yuva_nidhi is not None
    assert yuva_nidhi.status == EligibilityResult.STATUS_NOT_ELIGIBLE

    # Graduate unemployed for 8 months (>= 6 months)
    eligible_graduate = dict(recent_graduate)
    eligible_graduate["unemployment_months"] = 8
    results_2 = evaluate_user_eligibility(eligible_graduate)
    yuva_nidhi_2 = next((r for r in results_2 if r.scheme_id == "yuva-nidhi-karnataka"), None)
    assert yuva_nidhi_2 is not None
    assert yuva_nidhi_2.status == EligibilityResult.STATUS_ELIGIBLE


def test_insufficient_information():
    # Blank user profile
    empty_user = {}
    results = evaluate_user_eligibility(empty_user)
    assert len(results) > 0
    # Should flag missing fields
    first_result = results[0]
    assert len(first_result.missing_fields) > 0

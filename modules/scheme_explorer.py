"""
Scheme Explorer module for Government Scheme Assistant.
Provides high-performance filtering, full-text searching, and categorization of indexed schemes.
"""

from typing import List, Dict, Any, Optional
from database.sqlite_db import get_all_schemes


def search_and_filter_schemes(
    query: Optional[str] = None,
    category: Optional[str] = None,
    level: Optional[str] = None,
    occupation: Optional[str] = None,
    target_gender: Optional[str] = None,
    all_schemes: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Search and filter schemes based on multiple criteria.
    """
    if all_schemes is None:
        all_schemes = get_all_schemes()

    results = []
    query_clean = query.strip().lower() if query else ""

    for scheme in all_schemes:
        # Category filter
        if category and category != "All Categories":
            if scheme.get("category", "").lower() != category.lower():
                continue

        # Level filter
        if level and level != "All":
            if scheme.get("level", "").lower() != level.lower():
                continue

        # Gender filter
        if target_gender and target_gender != "All":
            genders = [g.lower() for g in scheme.get("target_genders", ["all"])]
            if "all" not in genders and target_gender.lower() not in genders:
                continue

        # Occupation filter
        if occupation and occupation != "All":
            occupations = [o.lower() for o in scheme.get("target_occupations", ["all"])]
            if "all" not in occupations and occupation.lower() not in occupations:
                continue

        # Free text search across title, short name, description, benefits, department
        if query_clean:
            searchable_fields = [
                scheme.get("name", ""),
                scheme.get("short_name", ""),
                scheme.get("description", ""),
                scheme.get("benefits_summary", ""),
                scheme.get("department", ""),
                scheme.get("eligibility_summary", "")
            ]
            combined_search_text = " ".join(searchable_fields).lower()
            if query_clean not in combined_search_text:
                continue

        results.append(scheme)

    return results


def get_scheme_metrics(schemes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate statistical overview for dashboard display."""
    total = len(schemes)
    central_count = sum(1 for s in schemes if s.get("level") == "Central")
    karnataka_count = sum(1 for s in schemes if s.get("level") == "Karnataka")
    
    categories = {}
    for s in schemes:
        cat = s.get("category", "General")
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "total_schemes": total,
        "central_schemes": central_count,
        "karnataka_schemes": karnataka_count,
        "categories_breakdown": categories
    }

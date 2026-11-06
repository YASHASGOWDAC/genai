"""
Helper utility functions for UI rendering, badge styles, and text presentation.
"""

import re
from typing import Optional


def format_currency(amount: Optional[float]) -> str:
    """Format numbers into Indian currency style (e.g., ₹2,50,000)."""
    if amount is None:
        return "N/A"
    try:
        s = f"{int(amount)}"
        if len(s) <= 3:
            return f"₹{s}"
        last_three = s[-3:]
        remaining = s[:-3]
        # Group in pairs from right to left
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        return f"₹{','.join(groups)},{last_three}"
    except Exception:
        return f"₹{amount}"


def get_status_badge(status: str) -> str:
    """Return colored badge HTML based on eligibility status."""
    if status == "Eligible":
        return '<span style="background-color:#DEF7EC;color:#03543F;padding:4px 10px;border-radius:12px;font-weight:600;font-size:12px;">✅ Eligible</span>'
    elif status == "Potentially Eligible":
        return '<span style="background-color:#FEF08A;color:#713F12;padding:4px 10px;border-radius:12px;font-weight:600;font-size:12px;">⚠️ Potentially Eligible</span>'
    elif status == "Not Eligible":
        return '<span style="background-color:#FDE8E8;color:#9B1C1C;padding:4px 10px;border-radius:12px;font-weight:600;font-size:12px;">❌ Not Eligible</span>'
    else:
        return '<span style="background-color:#E1EFFE;color:#1E429F;padding:4px 10px;border-radius:12px;font-weight:600;font-size:12px;">ℹ️ Info Needed</span>'


def get_level_badge(level: str) -> str:
    """Return badge for Central vs Karnataka schemes."""
    if level == "Karnataka":
        return '<span style="background-color:#FFF4E5;color:#B43403;padding:3px 8px;border-radius:6px;font-weight:600;font-size:11px;border:1px solid #FED7AA;">🟡 Karnataka State</span>'
    else:
        return '<span style="background-color:#EBF5FF;color:#1E429F;padding:3px 8px;border-radius:6px;font-weight:600;font-size:11px;border:1px solid #BFDBFE;">🇮🇳 Central Govt</span>'

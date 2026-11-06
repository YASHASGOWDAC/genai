"""
Source Validator utility for Government Scheme Assistant.
Validates URLs against official government domains to prevent misinformation and untrusted links.
"""

from urllib.parse import urlparse
from typing import Tuple

try:
    from config import TRUSTED_GOV_DOMAINS
except ImportError:
    TRUSTED_GOV_DOMAINS = ["gov.in", "nic.in", "karnataka.gov.in", "myscheme.gov.in"]


def validate_government_url(url: str) -> Tuple[bool, str]:
    """
    Validate whether a URL belongs to a verified Indian government entity.
    Returns (is_valid, reason).
    """
    if not url or not isinstance(url, str):
        return False, "URL is empty or invalid."

    url = url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        return False, "URL must start with http:// or https://."

    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False, "Could not extract valid hostname from URL."

        hostname = hostname.lower()

        # Check against trusted government domain extensions and whitelisted hosts
        is_trusted = any(
            hostname == domain or hostname.endswith("." + domain)
            for domain in TRUSTED_GOV_DOMAINS
        )

        if is_trusted:
            return True, f"Verified official government domain: {hostname}"
        else:
            return False, f"Domain '{hostname}' is not in the official whitelisted government domains."
    except Exception as e:
        return False, f"URL parsing error: {e}"

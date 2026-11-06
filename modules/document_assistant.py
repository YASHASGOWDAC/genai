"""
Document Requirement Assistant module for Government Scheme Assistant.
Generates structured verification checklists, issuing authority directories, and procedural steps.
"""

from typing import List, Dict, Any, Optional
from database.sqlite_db import get_scheme_by_id, get_all_schemes


# Directory of common authorities where citizens can obtain required certificates
DOCUMENT_ISSUING_AUTHORITIES = {
    "Aadhaar Card": {
        "authority": "Unique Identification Authority of India (UIDAI)",
        "portal": "https://myaadhaar.uidai.gov.in/",
        "verification_method": "Aadhaar e-KYC / OTP / Biometrics"
    },
    "Caste Certificate": {
        "authority": "Revenue Department (Karnataka: Nadakacheri Atalji Janasnehi Kendra)",
        "portal": "https://nadakacheri.karnataka.gov.in/",
        "verification_method": "Online RD Number Verification"
    },
    "Income Certificate": {
        "authority": "Revenue Department / Tahsildar (Karnataka: Nadakacheri)",
        "portal": "https://nadakacheri.karnataka.gov.in/",
        "verification_method": "Nadakacheri RD Barcode / Number"
    },
    "Ration Card": {
        "authority": "Food, Civil Supplies & Consumer Affairs Department",
        "portal": "https://ahara.kar.nic.in/",
        "verification_method": "Ration Card RC Number"
    },
    "Land Ownership Documents": {
        "authority": "Revenue Dept / Bhoomi Portal / FRUITS Portal",
        "portal": "https://landrecords.karnataka.gov.in/",
        "verification_method": "Pahani / RTC / Record of Rights"
    },
    "Bank Passbook": {
        "authority": "Scheduled Commercial Banks / Postal Payment Bank (IPPB)",
        "portal": "https://www.npci.org.in/",
        "verification_method": "Aadhaar Seeding / NPCI Mapper Linkage"
    },
    "Farmer ID (FID)": {
        "authority": "Karnataka Agriculture Department (FRUITS Portal)",
        "portal": "https://fruits.karnataka.gov.in/",
        "verification_method": "FID Number Linked to Land and Aadhaar"
    },
    "Student SSP ID": {
        "authority": "Karnataka State Scholarship Portal (SSP)",
        "portal": "https://ssp.postmatric.karnataka.gov.in/",
        "verification_method": "Student SATS / College Registration ID"
    }
}


def get_scheme_document_details(scheme_id: str) -> Optional[Dict[str, Any]]:
    """Get complete document requirement and application guide for a given scheme."""
    scheme = get_scheme_by_id(scheme_id)
    if not scheme:
        return None

    raw_docs = scheme.get("required_documents", [])
    enriched_docs = []

    for doc_name in raw_docs:
        authority_info = None
        for key, val in DOCUMENT_ISSUING_AUTHORITIES.items():
            if key.lower() in doc_name.lower():
                authority_info = val
                break

        enriched_docs.append({
            "name": doc_name,
            "is_mandatory": "mandatory" in doc_name.lower() or "primary" in doc_name.lower(),
            "issuing_authority": authority_info["authority"] if authority_info else "Competent Issuing Authority",
            "verification_portal": authority_info["portal"] if authority_info else scheme.get("application_portal"),
            "verification_method": authority_info["verification_method"] if authority_info else "Physical / Online verification"
        })

    return {
        "scheme_id": scheme["id"],
        "scheme_name": scheme["name"],
        "department": scheme.get("department"),
        "level": scheme.get("level"),
        "application_portal": scheme.get("application_portal"),
        "deadline": scheme.get("deadline", "Ongoing"),
        "documents": enriched_docs,
        "application_steps": scheme.get("application_steps", []),
        "source_url": scheme.get("source_url")
    }

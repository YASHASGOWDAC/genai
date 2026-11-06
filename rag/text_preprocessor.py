"""
Text Preprocessor for cleaning and normalizing government documents.
Handles whitespace normalization, header/footer elimination, and unicode cleaning.
"""

import re
import unicodedata
from typing import List, Dict, Any


def clean_text(text: str) -> str:
    """Clean and normalize raw extracted text from PDFs or web sources."""
    if not text:
        return ""

    # Normalize unicode characters (accents, curly quotes, dashes)
    text = unicodedata.normalize("NFKC", text)

    # Standardize currency and common abbreviations
    text = text.replace("Rs.", "₹").replace("INR", "₹")

    # Replace smart quotes and dashes
    text = re.sub(r'[\u2018\u2019]', "'", text)
    text = re.sub(r'[\u201C\u201D]', '"', text)
    text = re.sub(r'[\u2013\u2014]', '-', text)

    # Remove non-printable control characters except standard whitespace
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', ' ', text)

    # Remove inline page numbers like "Page 1 of 5"
    text = re.sub(r'\bpage\s+\d+\s+of\s+\d+\b', '', text, flags=re.IGNORECASE)

    # Strip repeated headers / footers common in gov gazettes
    lines = text.split("\n")
    cleaned_lines = []
    
    header_patterns = [
        r'^\s*page\s+\d+\s+of\s+\d+\s*$',
        r'^\s*\d+\s*$',
        r'^\s*official\s+gazette\s*$'
    ]

    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append("")
            continue

        # Check if line matches a trivial repetitive page number pattern
        is_repetitive = any(re.match(p, stripped, re.IGNORECASE) for p in header_patterns)
        if not is_repetitive:
            cleaned_lines.append(stripped)

    # Reassemble and collapse multiple empty lines into at most two
    processed = "\n".join(cleaned_lines)
    processed = re.sub(r'\n{3,}', '\n\n', processed)
    processed = re.sub(r'[ \t]{2,}', ' ', processed)

    return processed.strip()


def extract_headings(text: str) -> List[Dict[str, Any]]:
    """Detect numbered or prominent headings in the document text."""
    heading_pattern = re.compile(
        r'^(?:(?:\d+\.|\([a-z0-9]+\)|[A-Z0-9\.\s]{4,})\s+)([A-Z][A-Za-z0-9\s,\-–—]{3,60})$',
        re.MULTILINE
    )
    matches = []
    for match in heading_pattern.finditer(text):
        matches.append({
            "heading": match.group(0).strip(),
            "start": match.start(),
            "end": match.end()
        })
    return matches

"""
Multilingual module for Government Scheme Assistant.
Supports English, Kannada (ಕನ್ನಡ), and Hindi (हिंदी).
Handles UI localization, language detection, and entity preservation for official terms.
"""

import re
from typing import Dict, Any

# UI Localization Dictionary
UI_TRANSLATIONS = {
    "English": {
        "app_title": "AI Government Scheme Assistant",
        "app_tagline": "Discover Central & Karnataka Government Schemes with Grounded AI Retrieval",
        "nav_home": "Home Dashboard",
        "nav_chat": "Ask AI Assistant",
        "nav_explore": "Explore Schemes",
        "nav_eligibility": "Eligibility Checker",
        "nav_documents": "Required Documents",
        "nav_saved": "My Saved Schemes",
        "nav_evaluation": "RAG Evaluation",
        "nav_admin": "Admin Dashboard",
        "search_placeholder": "Search schemes by keyword, benefit, or department...",
        "eligible": "Eligible",
        "potentially_eligible": "Potentially Eligible",
        "not_eligible": "Not Eligible",
        "insufficient_info": "Insufficient Information",
        "apply_now": "Apply on Official Portal",
        "view_details": "View Full Details",
        "citations": "Verified Sources & Citations",
        "disclaimer_title": "Official Advisory",
        "karnataka_schemes": "Karnataka State Schemes",
        "central_schemes": "Central Government Schemes"
    },
    "Kannada": {
        "app_title": "ಸರ್ಕಾರಿ ಯೋಜನೆ ಮಾಹಿತಿ ಸಹಾಯಕ",
        "app_tagline": "ಕೇಂದ್ರ ಮತ್ತು ಕರ್ನಾಟಕ ಸರ್ಕಾರದ ಯೋಜನೆಗಳನ್ನು ಸುಲಭವಾಗಿ ತಿಳಿದುಕೊಳ್ಳಿ",
        "nav_home": "ಮುಖಪುಟ",
        "nav_chat": "AI ಸಹಾಯಕರನ್ನು ಕೇಳಿ",
        "nav_explore": "ಯೋಜನೆಗಳ ಪರಿಶೋಧನೆ",
        "nav_eligibility": "ಅರ್ಹತೆ ಪರಿಶೀಲನೆ",
        "nav_documents": "ಅಗತ್ಯ ದಾಖಲೆಗಳು",
        "nav_saved": "ಉಳಿಸಿದ ಯೋಜನೆಗಳು",
        "nav_evaluation": "RAG ಮೌಲ್ಯಮಾಪನ",
        "nav_admin": "ನಿರ್ವಾಹಕ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್",
        "search_placeholder": "ಯೋಜನೆಯ ಹೆಸರು ಅಥವಾ ಇಲಾಖೆ ಹುಡುಕಿ...",
        "eligible": "ಅರ್ಹರು",
        "potentially_eligible": "ಸಾಧ್ಯತೆ ಇದೆ",
        "not_eligible": "ಅನರ್ಹರು",
        "insufficient_info": "ಮಾಹಿತಿ ಅಪೂರ್ಣ",
        "apply_now": "ಅಧಿಕೃತ ಪೋರ್ಟಲ್‌ನಲ್ಲಿ ಅರ್ಜಿ ಸಲ್ಲಿಸಿ",
        "view_details": "ಸಂಪೂರ್ಣ ವಿವರ ವೀಕ್ಷಿಸಿ",
        "citations": "ಪರಿಶೀಲಿಸಿದ ಸರ್ಕಾರಿ ಮೂಲಗಳು",
        "disclaimer_title": "ಅಧಿಕೃತ ಸೂಚನೆ",
        "karnataka_schemes": "ಕರ್ನಾಟಕ ರಾಜ್ಯ ಯೋಜನೆಗಳು",
        "central_schemes": "ಕೇಂದ್ರ ಸರ್ಕಾರಿ ಯೋಜನೆಗಳು"
    },
    "Hindi": {
        "app_title": "सरकारी योजना सूचना सहायक",
        "app_tagline": "केंद्र और कर्नाटक सरकार की योजनाओं की प्रामाणिक जानकारी",
        "nav_home": "होम डैशबोर्ड",
        "nav_chat": "AI सहायक से पूछें",
        "nav_explore": "योजना निर्देशिका",
        "nav_eligibility": "पात्रता जांच",
        "nav_documents": "आवश्यक दस्तावेज",
        "nav_saved": "सहेजी गई योजनाएं",
        "nav_evaluation": "RAG मूल्यांकन",
        "nav_admin": "व्यवस्थापक डैशबोर्ड",
        "search_placeholder": "योजना का नाम, लाभ या विभाग खोजें...",
        "eligible": "पात्र",
        "potentially_eligible": "संभावित रूप से पात्र",
        "not_eligible": "अपात्र",
        "insufficient_info": "अधूरी जानकारी",
        "apply_now": "आधिकारिक पोर्टल पर आवेदन करें",
        "view_details": "पूरा विवरण देखें",
        "citations": "सत्यापित स्रोत और उद्धरण",
        "disclaimer_title": "आधिकारिक सलाह",
        "karnataka_schemes": "कर्नाटक राज्य योजनाएं",
        "central_schemes": "केंद्र सरकारी योजनाएं"
    }
}


def detect_language(text: str) -> str:
    """
    Detect the primary language of the text.
    Kannada Unicode range: U+0C80 to U+0CFF.
    Devanagari (Hindi) Unicode range: U+0900 to U+097F.
    """
    if not text:
        return "English"

    kannada_count = len(re.findall(r'[\u0C80-\u0CFF]', text))
    hindi_count = len(re.findall(r'[\u0900-\u097F]', text))

    if kannada_count > 3:
        return "Kannada"
    elif hindi_count > 3:
        return "Hindi"
    return "English"


def get_ui_text(key: str, lang: str = "English") -> str:
    """Retrieve localized UI label."""
    lang_dict = UI_TRANSLATIONS.get(lang, UI_TRANSLATIONS["English"])
    return lang_dict.get(key, UI_TRANSLATIONS["English"].get(key, key))

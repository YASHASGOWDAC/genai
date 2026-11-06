"""
Unit tests for multilingual detection and entity preservation.
"""

import pytest
from modules.multilingual import detect_language, get_ui_text


def test_language_detection():
    english_text = "What scholarships are available for post-matric students?"
    kannada_text = "ಕರ್ನಾಟಕದ ಗೃಹಲಕ್ಷ್ಮಿ ಯೋಜನೆಗೆ ಯಾರು ಅರ್ಹರು?"
    hindi_text = "पीएम किसान योजना के लिए कौन से दस्तावेज चाहिए?"

    assert detect_language(english_text) == "English"
    assert detect_language(kannada_text) == "Kannada"
    assert detect_language(hindi_text) == "Hindi"


def test_ui_translation():
    assert get_ui_text("eligible", "English") == "Eligible"
    assert get_ui_text("eligible", "Kannada") == "ಅರ್ಹರು"
    assert get_ui_text("eligible", "Hindi") == "पात्र"

    assert get_ui_text("nav_chat", "Kannada") == "AI ಸಹಾಯಕರನ್ನು ಕೇಳಿ"
    assert get_ui_text("nav_chat", "Hindi") == "AI सहायक से पूछें"

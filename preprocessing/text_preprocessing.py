"""
Text Modality Preprocessor
"""

import re

def clean_text_content(text: str, lower: bool = True, remove_html: bool = True) -> str:
    if not isinstance(text, str):
        return ""
    if remove_html:
        text = re.sub(r'<[^>]+>', '', text)
    if lower:
        text = text.lower()
    text = re.sub(r'\s+', ' ', text).strip()
    return text
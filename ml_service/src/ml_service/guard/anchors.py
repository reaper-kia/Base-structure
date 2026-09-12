import re
from typing import Dict, List, Any

DATE_PATTERN = re.compile(r'\b\d{1,2}[\./-]\d{1,2}[\./-]\d{2,4}\b|\b\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4}\b', re.IGNORECASE)
AMOUNT_PATTERN = re.compile(r'\b\d+(?:[\.,\s]\d+)*(?:\s*(?:тыс\.|млн\.|млрд\.|руб\.|долл\.|евро|%|процентов))\b', re.IGNORECASE)
NAME_PATTERN = re.compile(r'\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.\s*[А-ЯЁ]\.', re.IGNORECASE)

def get_context_window(text: str, match: re.Match, window_size: int = 7) -> str:
    """Возвращает окно из N слов вокруг найденного факта для проверки условий."""
    words = text.split()
    
    prefix = text[:match.start()].split()
    start_idx = max(0, len(prefix) - window_size)
    
    match_len_words = len(match.group().split())
    end_idx = min(len(words), len(prefix) + match_len_words + window_size)
    
    return " ".join(words[start_idx:end_idx]).lower()

def extract(text: str) -> Dict[str, List[Dict[str, Any]]]:
    if not text:
        return {"dates": [], "amounts": [], "names": []}
        
    anchors = {"dates": [], "amounts": [], "names": []}
    
    for match in DATE_PATTERN.finditer(text):
        anchors["dates"].append({
            "value": match.group(),
            "context": get_context_window(text, match)
        })
        
    for match in AMOUNT_PATTERN.finditer(text):
        anchors["amounts"].append({
            "value": match.group(),
            "context": get_context_window(text, match)
        })
        
    for match in NAME_PATTERN.finditer(text):
        anchors["names"].append({
            "value": match.group(),
            "context": get_context_window(text, match)
        })
        
    return anchors

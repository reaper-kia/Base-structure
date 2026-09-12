import re
from typing import Dict, List, Any

MONTHS = {
    "января": "01", "февраля": "02", "марта": "03", "апреля": "04",
    "мая": "05", "июня": "06", "июля": "07", "августа": "08",
    "сентября": "09", "октября": "10", "ноября": "11", "декабря": "12"
}

DATE_PATTERN = re.compile(r'\b\d{1,2}[\./-]\d{1,2}[\./-]\d{2,4}\b|\b\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)(?:\s+\d{4})?\b', re.IGNORECASE)
# Единицы могут кончаться точкой ("руб.", "тыс.") или символом "%" — поэтому
# завершающего \b тут быть НЕ должно (после "." или "%" границы слова нет,
# и весь паттерн переставал матчиться на реальных суммах). Точка после
# сокращения необязательна, единица масштаба (тыс./млн.) может стоять перед
# валютой ("5 млн. руб.").
AMOUNT_PATTERN = re.compile(
    r'\b\d+(?:[\.,\s]\d+)*'
    r'(?:\s*(?:тыс|млн|млрд)\.?)?'
    r'\s*(?:руб\.?|долл\.?|евро|%|процент(?:ов|а)?|рабочих\s+дней|календарных\s+дней|тыс\.?|млн\.?|млрд\.?)',
    re.IGNORECASE,
)
NAME_PATTERN = re.compile(r'\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.\s*[А-ЯЁ]\.', re.IGNORECASE)

def normalize_date(val: str) -> str:
    val = val.lower().replace("-", ".").replace("/", ".")
    for m_name, m_num in MONTHS.items():
        if m_name in val:
            parts = val.split()
            if len(parts) >= 3:
                day = parts[0].zfill(2)
                year = parts[2]
                return f"{day}.{m_num}.{year}"
    parts = val.split(".")
    if len(parts) == 3:
        return f"{parts[0].zfill(2)}.{parts[1].zfill(2)}.{parts[2]}"
    return val

def normalize_amount(val: str) -> str:
    val = val.lower()
    # Отсекаем всё, начиная с первой буквы или знака процента, чтобы собрать целое число
    prefix = re.split(r'[а-яa-z%]', val)[0]
    num_str = re.sub(r'[^\d]', '', prefix)
    
    if not num_str: return val
    
    num = int(num_str)
    if "тыс" in val: num *= 1000
    elif "млн" in val: num *= 1000000
    elif "млрд" in val: num *= 1000000000
    
    modifier = ""
    if "рабоч" in val: modifier = " work_days"
    elif "календар" in val: modifier = " cal_days"
    elif "руб" in val: modifier = " rub"
    
    return f"{num}{modifier}"

def get_context_window(text: str, match: re.Match, window_size: int = 7) -> str:
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
        val = match.group()
        anchors["dates"].append({"value": val, "norm": normalize_date(val), "context": get_context_window(text, match)})
        
    for match in AMOUNT_PATTERN.finditer(text):
        val = match.group()
        anchors["amounts"].append({"value": val, "norm": normalize_amount(val), "context": get_context_window(text, match)})
        
    for match in NAME_PATTERN.finditer(text):
        anchors["names"].append({"value": match.group(), "norm": match.group().lower(), "context": get_context_window(text, match)})
        
    return anchors

import hashlib
import re
from typing import List, Dict

def get_doc_hash(text: str) -> str:
    """ML-09: Хеш содержимого для проверки идемпотентности."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def split_into_sentences(text: str) -> List[str]:
    """Разбивает текст на предложения, не разрывая их."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

def chunk_document(text: str, doc_id: str, default_section: str = "") -> List[Dict]:
    """
    ML-09: Нарезка документа на чанки 400-800 символов.
    - Не режет посреди предложения.
    - Перекрытие в одно предложение.
    - Сохраняет позицию и заголовок раздела.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    
    current_text = ""
    current_sentences = []
    position = 0
    section_title = default_section

    for para in paragraphs:
        if len(para) < 100 and not re.search(r'[.!?]$', para):
            section_title = para
            continue

        sentences = split_into_sentences(para)
        
        for sentence in sentences:
            if len(current_text) + len(sentence) > 800 and len(current_text) >= 400:
                chunks.append({
                    "doc_id": doc_id,
                    "position": position,
                    "section_title": section_title,
                    "text": current_text.strip(),
                    "doc_hash": get_doc_hash(text)
                })
                position += 1
                
                overlap = current_sentences[-1] if current_sentences else ""
                current_sentences = [overlap, sentence] if overlap else [sentence]
                current_text = overlap + " " + sentence if overlap else sentence
            else:
                current_sentences.append(sentence)
                current_text = (current_text + " " + sentence).strip()

    if current_text:
        chunks.append({
            "doc_id": doc_id,
            "position": position,
            "section_title": section_title,
            "text": current_text.strip(),
            "doc_hash": get_doc_hash(text)
        })

    return chunks

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class TaskType(str, Enum):
    classification = "classification"
    extraction = "extraction"
    summarization = "summarization"
    processing = "processing"


class Prediction(BaseModel):
    label: str
    score: float


class PredictRequest(BaseModel):
    request_id: str
    task: TaskType
    subject_id: Optional[str] = None
    text: str


class PredictResponse(BaseModel):
    request_id: str
    task: TaskType
    predictions: List[Prediction]
    model_version: str
    is_fallback: bool
    latency_ms: float


class ModelHealth(BaseModel):
    model_loaded: bool
    model_version: str
    fallback_enabled: bool
    supported_tasks: List[str]


# ML-10: Формат фрагмента базы знаний
class KnowledgeChunk(BaseModel):
    doc_id: str
    section_title: str
    text: str


class ProcessRequest(BaseModel):
    draft: str
    doc_type: str
    doc_type_name: str
    structure_hint: str
    requisite_keys: List[str]
    request_id: str
    # ML-10: Новые поля для RAG-контекста
    terminology_context: str = ""
    retrieved_chunks: List[KnowledgeChunk] = []


class FactGuardResult(BaseModel):
    verdict: str = "clean"
    preserved: List[str] = []
    lost: List[str] = []
    added: List[str] = []
    source_count: int = 0
    preserved_count: int = 0


class ProcessResponse(BaseModel):
    request_id: str
    improved_text: str
    requisites: Dict[str, Any]
    fact_guard: FactGuardResult
    is_fallback: bool = False
    reason_code: Optional[str] = None
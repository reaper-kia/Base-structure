from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


# --- Схемы для старого эндпоинта /predict и Fallback (от тимлида) ---
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


# --- Новые схемы для нашего эндпоинта /api/v1/process и Fact Guard ---
class ProcessRequest(BaseModel):
    draft: str
    doc_type: str
    doc_type_name: str
    structure_hint: str
    requisite_keys: List[str]
    request_id: str


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
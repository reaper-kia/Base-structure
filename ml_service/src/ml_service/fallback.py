from typing import List
import random
from ml_service.schemas import PredictRequest, Prediction, TaskType

FALLBACK_VERSION = "1.0.0-fallback"

def predict_fallback(request: PredictRequest) -> List[Prediction]:
    """Возвращает заглушку для любого типа задачи, не требуя старых полей."""
    
    # Для детерминированного теста используем hash от текста (или request_id) как seed
    seed = hash(request.text) if request.text else 42
    random.seed(seed)
    
    if request.task == TaskType.processing:
        return [
            Prediction(label="processed_item_1", score=round(random.uniform(0.7, 0.99), 2)),
            Prediction(label="processed_item_2", score=round(random.uniform(0.5, 0.69), 2))
        ]
        
    # Базовый ответ для любых других задач
    return [
        Prediction(label="fallback_1", score=0.9),
        Prediction(label="fallback_2", score=0.8)
    ]

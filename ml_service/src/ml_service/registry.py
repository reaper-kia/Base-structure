"""Загрузка модели и безопасный вызов инференса.

Три правила, которые тут зашиты:
1. Сервис стартует даже если модели нет.
2. Любое исключение внутри модели -> заглушка, а не 500.
3. Инференс дольше таймаута -> заглушка, а не зависшее демо.

Тебе (ML) нужно менять ТОЛЬКО файлы в models/. Этот файл - оркестрация.
"""

import asyncio
import logging
from typing import Any, Protocol

from ml_service.config import settings
from ml_service.fallback import FALLBACK_VERSION, predict_fallback
from ml_service.schemas import Prediction, PredictRequest, TaskType

logger = logging.getLogger(__name__)


class Predictor(Protocol):
    """Интерфейс, которому должна соответствовать любая твоя модель."""

    version: str
    supported_tasks: list[TaskType]

    def predict(self, request: PredictRequest) -> list[Prediction]: ...


class ModelRegistry:
    def __init__(self) -> None:
        self._predictor: Predictor | None = None

    @property
    def is_loaded(self) -> bool:
        return self._predictor is not None

    @property
    def version(self) -> str:
        return self._predictor.version if self._predictor else FALLBACK_VERSION

    @property
    def supported_tasks(self) -> list[TaskType]:
        if self._predictor:
            return self._predictor.supported_tasks
        return list(TaskType)

    def load(self) -> None:
        """Вызывается один раз на старте приложения.

        Никогда не бросает исключение наружу - иначе контейнер
        уйдёт в рестарт-луп посреди хакатона.
        """
        if not settings.model_path.exists():
            logger.warning(
                "Артефакт модели не найден по пути %s. Работаем на заглушке. "
                "Обучи модель: python -m training.train_recommender",
                settings.model_path,
            )
            return

        try:
            import joblib

            artifact: dict[str, Any] = joblib.load(settings.model_path)
            predictor_type = artifact["predictor_type"]

            if predictor_type == "recommender":
                from ml_service.models.recommender import CosineRecommender

                self._predictor = CosineRecommender.from_artifact(artifact)
            elif predictor_type == "anomaly":
                from ml_service.models.anomaly import IsolationForestDetector

                self._predictor = IsolationForestDetector.from_artifact(artifact)
            else:
                logger.error("Неизвестный predictor_type: %s", predictor_type)
                return

            logger.info("Модель загружена: %s", self._predictor.version)
        # Артефакт может содержать произвольную стороннюю модель/сериализацию.
        except Exception:
            logger.exception("Не удалось загрузить модель, остаёмся на заглушке")
            self._predictor = None

    async def predict(self, request: PredictRequest) -> tuple[list[Prediction], bool]:
        """Возвращает (предсказания, is_fallback)."""
        if self._predictor is None:
            return predict_fallback(request), True

        if request.task not in self._predictor.supported_tasks:
            logger.warning(
                "Задача %s не поддерживается моделью %s, отдаём заглушку",
                request.task,
                self._predictor.version,
            )
            return predict_fallback(request), True

        try:
            predictions = await asyncio.wait_for(
                asyncio.to_thread(self._predictor.predict, request),
                timeout=settings.predict_timeout_seconds,
            )
        except TimeoutError:
            logger.warning("Инференс превысил таймаут, отдаём заглушку")
            return predict_fallback(request), True
        # Predictor является подключаемым кодом; его сбой переводит сервис на fallback.
        except Exception:
            logger.exception("Ошибка внутри модели, отдаём заглушку")
            return predict_fallback(request), True

        if not predictions:
            return predict_fallback(request), True

        return predictions, False


registry = ModelRegistry()

"""Детерминированная защита от галлюцинаций.

Сверяет якоря исходного текста с якорями результата. Промпт просит модель
не выдумывать, Fact Guard это проверяет.
"""

from dataclasses import dataclass, field
from ml_service.guard.anchors import normalize


@dataclass
class GuardResult:
    preserved: list[str] = field(default_factory=list)
    lost: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    verdict: str = "clean"  # clean | warning | blocked
    source_count: int = 0
    preserved_count: int = 0

    def as_dict(self) -> dict:
        return {
            "preserved": self.preserved,
            "lost": self.lost,
            "added": self.added,
            "verdict": self.verdict,
            "source_count": self.source_count,
            "preserved_count": self.preserved_count,
        }


def check(source_anchors: dict[str, list[str]], result_anchors: dict[str, list[str]]) -> GuardResult:
    """
    Сравнивает извлеченные факты до и после обработки нейросетью.
    """
    preserved = []
    lost = []
    added = []
    
    # 1. Собираем все факты из исходного черновика в нормализованном виде
    source_norm_map = {}
    for category, anchors in source_anchors.items():
        for anchor in anchors:
            source_norm_map[normalize(anchor)] = anchor
            
    # 2. Собираем все факты из ответа ИИ
    result_norm_map = {}
    for category, anchors in result_anchors.items():
        for anchor in anchors:
            result_norm_map[normalize(anchor)] = anchor
            
    # 3. Ищем сохраненные и потерянные факты
    for norm_val, orig_val in source_norm_map.items():
        if norm_val in result_norm_map:
            preserved.append(orig_val)
        else:
            lost.append(orig_val)
            
    # 4. Ищем галлюцинации (добавленные факты)
    for norm_val, orig_val in result_norm_map.items():
        if norm_val not in source_norm_map:
            added.append(orig_val)
            
    # 5. Выносим вердикт согласно ТЗ
    if added:
        verdict = "blocked"
    elif lost:
        verdict = "warning"
    else:
        verdict = "clean"
        
    # 6. Возвращаем объект GuardResult
    return GuardResult(
        preserved=preserved,
        lost=lost,
        added=added,
        verdict=verdict,
        source_count=len(source_norm_map),
        preserved_count=len(preserved)
    )
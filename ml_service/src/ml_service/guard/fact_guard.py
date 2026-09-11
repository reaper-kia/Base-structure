"""Детерминированная защита от галлюцинаций.

Сверяет якоря исходного текста с якорями результата. Промпт просит модель
не выдумывать, Fact Guard это проверяет.
"""

from dataclasses import dataclass, field


@dataclass
class GuardResult:
    preserved: list[str] = field(default_factory=list)
    lost: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    verdict: str = "clean"  # clean | warning | blocked

    def as_dict(self) -> dict:
        return {
            "preserved": self.preserved,
            "lost": self.lost,
            "added": self.added,
            "verdict": self.verdict,
        }


def check(source_anchors: dict, result_anchors: dict) -> GuardResult:
    raise NotImplementedError("TODO(ML)")

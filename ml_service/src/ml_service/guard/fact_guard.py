from typing import Dict, List, Any
from dataclasses import dataclass, field

@dataclass
class GuardResult:
    verdict: str = "clean"
    preserved: List[str] = field(default_factory=list)
    lost: List[str] = field(default_factory=list)
    added: List[str] = field(default_factory=list)
    source_count: int = 0
    preserved_count: int = 0
    
    def as_dict(self):
        return {
            "verdict": self.verdict,
            "preserved": self.preserved,
            "lost": self.lost,
            "added": self.added,
            "source_count": self.source_count,
            "preserved_count": self.preserved_count
        }

INVERSIONS = [
    ({"после", "позднее", "не ранее"}, {"до", "не позднее", "не позднее чем", "ранее"}),
    ({"не"}, {"только", "исключительно"}),
    ({"без"}, {"с", "включительно"})
]

def check_inversion(src_ctx: str, res_ctx: str) -> bool:
    """Проверяет, не перевернулся ли смысл."""
    for group1, group2 in INVERSIONS:
        has_g1_src = any(w in src_ctx for w in group1)
        has_g2_src = any(w in src_ctx for w in group2)
        has_g1_res = any(w in res_ctx for w in group1)
        has_g2_res = any(w in res_ctx for w in group2)
        
        if (has_g1_src and has_g2_res and not has_g1_res) or (has_g2_src and has_g1_res and not has_g2_res):
            return True
    return False

def check(source_anchors: Dict[str, List[Dict[str, Any]]], result_anchors: Dict[str, List[Dict[str, Any]]]) -> GuardResult:
    lost = []
    preserved = []
    added = []
    blocked = False
    
    for category in ["dates", "amounts", "names"]:
        src_items = source_anchors.get(category, [])
        res_items = result_anchors.get(category, [])
        
        src_vals = {item["value"] for item in src_items}
        res_vals = {item["value"] for item in res_items}
        
        for item in src_items:
            if item["value"] not in res_vals:
                lost.append(item["value"])
                # Строгий запрет на потерю сумм и дат
                if category in ["amounts", "dates"]: 
                    blocked = True
            else:
                preserved.append(item["value"])
                res_item = next(r for r in res_items if r["value"] == item["value"])
                
                # Если факт на месте, но условие поменялось
                if check_inversion(item["context"], res_item["context"]):
                    blocked = True
                    
        for item in res_items:
            if item["value"] not in src_vals:
                added.append(item["value"])

    verdict = "clean"
    if blocked:
        verdict = "blocked"
    elif lost or added:
        verdict = "warning"
        
    return GuardResult(
        verdict=verdict,
        preserved=preserved,
        lost=lost,
        added=added,
        source_count=sum(len(v) for v in source_anchors.values()),
        preserved_count=len(preserved)
    )

from dataclasses import dataclass, asdict
from typing import Literal, Dict, Any

InsightLevel = Literal["success", "warning", "error", "info"]

@dataclass(frozen=True)
class InsightMetric:
    """DTO for a single business insight/alert."""
    type: str
    message: str
    level: InsightLevel

    def to_legacy_dict(self) -> Dict[str, Any]:
        """Convert to legacy dictionary format for compatibility."""
        return asdict(self)

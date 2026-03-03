import json
from datetime import date, datetime

def build_selection_signature(venue: str, period_mode: str, start_date, end_date, compare_mode: str) -> str:
    """
    Builds a deterministic, JSON-serializable signature of global filters.
    Used for rigorous caching across views to prevent stale UI.
    """
    def _format_date(d):
        if isinstance(d, (date, datetime)):
            return d.isoformat()
        return str(d) if d else "None"

    return json.dumps({
        "venue": str(venue),
        "period_mode": str(period_mode),
        "start_date": _format_date(start_date),
        "end_date": _format_date(end_date),
        "compare_mode": str(compare_mode) if compare_mode else "None"
    }, sort_keys=True)

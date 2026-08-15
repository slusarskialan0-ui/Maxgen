"""Auto-recovery helpers: health-check state per source and pipeline-level alerting."""
import logging
import time
from datetime import datetime, timezone
from typing import Dict

logger = logging.getLogger(__name__)

# In-process health registry: source_type -> health info dict
_source_health: Dict[str, dict] = {}


def record_source_success(source_type: str, count: int) -> None:
    """Mark a source as healthy after a successful fetch."""
    _source_health[source_type] = {
        "status": "ok",
        "last_success": datetime.now(timezone.utc).isoformat(),
        "last_count": count,
        "consecutive_failures": 0,
    }


def record_source_failure(source_type: str, error: str) -> None:
    """Mark a source as degraded/down after a failed fetch."""
    entry = _source_health.get(source_type, {"consecutive_failures": 0})
    failures = entry.get("consecutive_failures", 0) + 1
    _source_health[source_type] = {
        "status": "error" if failures >= 2 else "degraded",
        "last_error": error,
        "last_failure": datetime.now(timezone.utc).isoformat(),
        "consecutive_failures": failures,
        "last_success": entry.get("last_success"),
        "last_count": entry.get("last_count", 0),
    }
    if failures >= 2:
        _alert_source_down(source_type, error, failures)


def _alert_source_down(source_type: str, error: str, failures: int) -> None:
    """Log an alert when a source is persistently down.

    In production this could push to Slack / PagerDuty / email.
    """
    logger.error(
        "ALERT: source '%s' has failed %d consecutive times. Last error: %s",
        source_type,
        failures,
        error,
    )


def get_health_summary() -> dict:
    """Return overall pipeline health and per-source status."""
    statuses = {k: v["status"] for k, v in _source_health.items()}
    degraded = [k for k, v in statuses.items() if v in ("degraded", "error")]
    if not degraded:
        overall = "ok"
    elif any(statuses[k] == "error" for k in degraded):
        overall = "error"
    else:
        overall = "degraded"
    return {
        "overall": overall,
        "sources": _source_health,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

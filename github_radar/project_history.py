"""Rolling repository observations and confidence-aware growth for Project Radar."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from github_radar.project_common import Project, SCHEMA_VERSION, days_since

LOGGER = logging.getLogger("project_radar")


def load_history(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "days": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        LOGGER.warning("History is unreadable; starting a new history")
        return {"schema_version": SCHEMA_VERSION, "days": {}}
    if not isinstance(payload, dict) or not isinstance(payload.get("days"), dict):
        return {"schema_version": SCHEMA_VERSION, "days": {}}
    return payload


def _history_baseline(
    history: dict[str, Any], full_name: str, target: date, today: date
) -> tuple[Optional[date], Optional[dict[str, Any]]]:
    candidates: list[tuple[date, dict[str, Any]]] = []
    for key, records in history.get("days", {}).items():
        try:
            day = date.fromisoformat(key)
        except (TypeError, ValueError):
            continue
        if day >= today or day > target or not isinstance(records, dict):
            continue
        record = records.get(full_name)
        if isinstance(record, dict):
            candidates.append((day, record))
    return max(candidates, key=lambda pair: pair[0]) if candidates else (None, None)


def _observation_days(history: dict[str, Any], full_name: str, today: date) -> list[date]:
    observed: list[date] = []
    for key, records in history.get("days", {}).items():
        if not isinstance(records, dict) or full_name not in records:
            continue
        try:
            day = date.fromisoformat(key)
        except (TypeError, ValueError):
            continue
        if day < today:
            observed.append(day)
    return sorted(set(observed))


def _first_seen(history: dict[str, Any], full_name: str, today: date) -> str:
    observed = _observation_days(history, full_name, today)
    return min(observed).isoformat() if observed else today.isoformat()


def _measurement_confidence(
    observed: list[date],
    *,
    has_one_day: bool,
    has_seven_day: bool,
    today: date,
) -> tuple[float, str]:
    """Return a conservative confidence for observed or estimated momentum.

    A lifetime stars/age estimate is useful for discovery but is not equivalent
    to velocity measured by this radar. It therefore starts at 0.25. Confidence
    rises as independent daily observations accumulate and reaches 1.0 only when
    a seven-day baseline exists.
    """
    if has_seven_day:
        return 1.0, "measured-7d"
    if has_one_day:
        span = max((today - min(observed)).days, 1) if observed else 1
        confidence = min(0.85, 0.48 + 0.045 * min(len(observed), 7) + 0.025 * min(span, 7))
        return round(confidence, 3), "measured-short-window"
    return 0.25, "provisional-lifetime"


def calculate_growth(project: Project, history: dict[str, Any], now: datetime) -> dict[str, Any]:
    today = now.date()
    observed = _observation_days(history, project.full_name, today)
    result: dict[str, Any] = {
        "delta_1d": None,
        "delta_7d": None,
        "delta_30d": None,
        "fork_delta_7d": None,
        "watcher_delta_7d": None,
        "stars_per_day": 0.0,
        "acceleration": 0.0,
        "relative_7d": None,
        "signal_source": "lifetime-estimate",
        "signal_confidence": 0.25,
        "confidence_label": "provisional-lifetime",
        "is_provisional": True,
        "history_observations": len(observed),
        "measurement_window_days": 0,
        "first_seen": _first_seen(history, project.full_name, today),
    }
    baselines: dict[int, tuple[Optional[date], Optional[dict[str, Any]]]] = {
        window: _history_baseline(history, project.full_name, today - timedelta(days=window), today)
        for window in (1, 7, 14, 30)
    }
    for window in (1, 7, 30):
        baseline_day, baseline = baselines[window]
        if baseline_day is None or baseline is None:
            continue
        elapsed = max((today - baseline_day).days, 1)
        result[f"delta_{window}d"] = project.stars - int(baseline.get("stars") or 0)
        result[f"actual_days_{window}d"] = elapsed

    seven_day, seven = baselines[7]
    fourteen_day, fourteen = baselines[14]
    if seven_day is not None and seven is not None:
        elapsed = max((today - seven_day).days, 1)
        delta = project.stars - int(seven.get("stars") or 0)
        result["stars_per_day"] = max(delta / elapsed, 0.0)
        previous_stars = max(int(seven.get("stars") or 0), 1)
        result["relative_7d"] = delta / previous_stars
        result["fork_delta_7d"] = project.forks - int(seven.get("forks") or 0)
        result["watcher_delta_7d"] = project.watchers - int(seven.get("watchers") or 0)
        result["signal_source"] = "observed-history"
        result["measurement_window_days"] = elapsed
        if fourteen_day is not None and fourteen is not None and fourteen_day < seven_day:
            previous_elapsed = max((seven_day - fourteen_day).days, 1)
            previous_velocity = (
                int(seven.get("stars") or 0) - int(fourteen.get("stars") or 0)
            ) / previous_elapsed
            result["acceleration"] = result["stars_per_day"] - previous_velocity
    elif result["delta_1d"] is not None:
        elapsed = max(int(result.get("actual_days_1d") or 1), 1)
        result["stars_per_day"] = max(float(result["delta_1d"]) / elapsed, 0.0)
        result["signal_source"] = "observed-history"
        result["measurement_window_days"] = elapsed
    else:
        age = max(days_since(project.created_at, now, default=3650), 7)
        result["stars_per_day"] = project.stars / age
        result["measurement_window_days"] = age

    confidence, label = _measurement_confidence(
        observed,
        has_one_day=result["delta_1d"] is not None,
        has_seven_day=result["delta_7d"] is not None,
        today=today,
    )
    result["signal_confidence"] = confidence
    result["confidence_label"] = label
    result["is_provisional"] = confidence < 0.999
    return result


def update_history(
    history: dict[str, Any], projects: list[Project], now: datetime, keep_days: int
) -> dict[str, Any]:
    days = history.setdefault("days", {})
    today = now.date()
    days[today.isoformat()] = {
        project.full_name: {
            "stars": project.stars,
            "forks": project.forks,
            "watchers": project.watchers,
            "pushed_at": project.pushed_at,
        }
        for project in projects
    }
    cutoff = today - timedelta(days=keep_days)
    for key in list(days):
        try:
            if date.fromisoformat(key) < cutoff:
                del days[key]
        except (TypeError, ValueError):
            del days[key]
    history["schema_version"] = SCHEMA_VERSION
    history["updated_at"] = now.replace(microsecond=0).isoformat()
    return history

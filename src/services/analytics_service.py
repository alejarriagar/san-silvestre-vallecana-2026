"""Cálculos transparentes de métricas deportivas."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from src.database import (
    get_activity_sessions_between,
    get_completion_summary,
    get_last_activity_session,
    get_weekly_planned_distance,
)


def calculate_session_load(session: dict[str, Any]) -> float | None:
    """Calcula carga orientativa como duración en minutos × RPE.

    No calcula carga si falta duración o RPE, para evitar inventar datos.
    """
    duration = session.get("duration_minutes")
    rpe = session.get("rpe")

    if duration is None or rpe is None:
        return None

    return float(duration) * float(rpe)


def calculate_dashboard_metrics(today: date) -> dict[str, Any]:
    """Calcula las métricas disponibles para el dashboard."""
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    sessions_this_week = get_activity_sessions_between(week_start, today)
    sessions_this_month = get_activity_sessions_between(month_start, today)
    sessions_last_28_days = get_activity_sessions_between(
        today - timedelta(days=27),
        today,
    )

    weekly_running_km = sum(
        float(session["distance_km"] or 0)
        for session in sessions_this_week
        if session["sport"] == "Carrera"
    )

    monthly_running_km = sum(
        float(session["distance_km"] or 0)
        for session in sessions_this_month
        if session["sport"] == "Carrera"
    )

    weekly_load_by_sport: dict[str, float] = defaultdict(float)

    for session in sessions_this_week:
        session_load = calculate_session_load(session)

        if session_load is not None:
            weekly_load_by_sport[session["sport"]] += session_load

    total_weekly_load = sum(weekly_load_by_sport.values())
    completion_summary = get_completion_summary()

    return {
        "sessions_this_week": sessions_this_week,
        "sessions_this_month": sessions_this_month,
        "sessions_last_28_days": sessions_last_28_days,
        "weekly_running_km": weekly_running_km,
        "monthly_running_km": monthly_running_km,
        "planned_weekly_running_km": get_weekly_planned_distance(today),
        "weekly_load_by_sport": dict(weekly_load_by_sport),
        "total_weekly_load": total_weekly_load,
        "completion_summary": completion_summary,
        "last_activity_session": get_last_activity_session(),
    }

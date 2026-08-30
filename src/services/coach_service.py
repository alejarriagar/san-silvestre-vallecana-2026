"""Preparación de contexto y ejecución segura del entrenador deportivo."""

from __future__ import annotations

from datetime import date
from typing import Any

from src.database import (
    get_competitions,
    get_next_training,
    get_profile,
    get_training_plan,
)
from src.services.analytics_service import calculate_dashboard_metrics
from src.services.llm_service import (
    CoachAnalysis,
    ProviderConfiguration,
    get_coach_analysis_provider,
)
from src.services.safety_rules import evaluate_training_state


def build_coach_context(today: date) -> dict[str, Any]:
    """Construye el contexto mínimo necesario para un análisis útil.

    No incluye claves API, identificadores internos ni datos ajenos
    al seguimiento deportivo.
    """
    profile = get_profile()
    metrics = calculate_dashboard_metrics(today)

    recent_sessions = metrics["sessions_last_28_days"]

    safety_assessment = evaluate_training_state(
        recent_sessions,
        today,
    )

    next_training = get_next_training(today)

    upcoming_plan = [
        {
            "fecha": training["planned_date"],
            "deporte": training["sport"],
            "tipo": training["session_type"],
            "descripcion": training["description"],
            "rpe_objetivo": training["target_rpe"],
            "estado": training["status"],
            "descarga": bool(training["is_deload"]),
        }
        for training in get_training_plan()
        if training["planned_date"] >= today.isoformat()
        and training["status"] != "Cancelado"
    ][:8]

    recent_session_summary = [
        {
            "fecha": session["session_date"],
            "deporte": session["sport"],
            "tipo": session["session_type"],
            "duracion_min": session["duration_minutes"],
            "distancia_km": session["distance_km"],
            "ritmo_segundos_km": session["average_pace_seconds_per_km"],
            "fc_media": session["average_heart_rate"],
            "rpe": session["rpe"],
            "sueno_horas": session["sleep_hours"],
            "fatiga": session["fatigue"],
            "dolor_durante": session["pain_during"],
            "dolor_despues": session["pain_after"],
            "dolor_dia_siguiente": session["pain_next_day"],
        }
        for session in recent_sessions[:12]
    ]

    competition_summary = [
        {
            "nombre": competition["name"],
            "fecha": competition["competition_date"],
            "distancia_km": competition["distance_km"],
            "objetivo_segundos": competition["goal_time_seconds"],
            "tiempo_oficial_segundos": competition["official_time_seconds"],
        }
        for competition in get_competitions()
    ]

    context = {
        "fecha_analisis": today.isoformat(),
        "perfil": {
            "sexo": profile.get("sex"),
            "edad": profile.get("age"),
            "altura_cm": profile.get("height_cm"),
            "peso_kg": profile.get("weight_kg"),
            "preferencias_entrenamiento": profile.get(
                "training_preferences"
            ),
            "observaciones_salud_relevantes": profile.get("health_notes"),
        },
        "objetivo": {
            "competicion_principal": "San Silvestre Vallecana 2026",
            "distancia_km": 10,
            "objetivo_principal": "Bajar de 50:00",
            "ritmo_referencia": "4:59 min/km",
        },
        "metricas": {
            "km_carrera_semana": metrics["weekly_running_km"],
            "km_carrera_mes": metrics["monthly_running_km"],
            "km_planificados_semana": metrics["planned_weekly_running_km"],
            "carga_semanal": metrics["total_weekly_load"],
            "carga_por_deporte": metrics["weekly_load_by_sport"],
            "sesiones_ultimos_28_dias": len(recent_sessions),
            "cumplimiento_plan_porcentaje": metrics[
                "completion_summary"
            ]["percentage"],
        },
        "evaluacion_determinista": safety_assessment,
        "proximo_entrenamiento": (
            {
                "fecha": next_training["planned_date"],
                "tipo": next_training["session_type"],
                "descripcion": next_training["description"],
                "rpe_objetivo": next_training["target_rpe"],
            }
            if next_training
            else None
        ),
        "plan_proximo": upcoming_plan,
        "sesiones_recientes": recent_session_summary,
        "competiciones": competition_summary,
    }

    return context


def generate_coach_analysis(
    today: date,
) -> tuple[CoachAnalysis, ProviderConfiguration, dict[str, Any]]:
    """Genera análisis mediante modo demo o proveedor configurado."""
    context = build_coach_context(today)
    provider = get_coach_analysis_provider()
    analysis = provider.generate(context)

    return analysis, provider.configuration, context

"""Reglas deterministas para adaptar recomendaciones de entrenamiento."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any


def _session_date(session: dict[str, Any]) -> date:
    """Convierte la fecha almacenada de una sesión a objeto date."""
    return date.fromisoformat(session["session_date"])


def _add_unique(values: list[str], new_value: str) -> None:
    """Añade un mensaje solo si todavía no existe."""
    if new_value not in values:
        values.append(new_value)


def evaluate_training_state(
    sessions: list[dict[str, Any]],
    today: date,
) -> dict[str, Any]:
    """Evalúa el estado deportivo usando reglas explícitas y trazables.

    Esta función no diagnostica lesiones ni inventa métricas ausentes.
    """
    if not sessions:
        return {
            "estado": "amarillo",
            "resumen": (
                "Estado provisional: todavía no hay sesiones registradas "
                "suficientes para valorar carga, recuperación o rodilla."
            ),
            "alertas": [],
            "recomendaciones": [
                "Registra duración, RPE, sueño y dolor de rodilla tras las próximas sesiones."
            ],
            "preguntas_pendientes": [
                "RPE de las sesiones.",
                "Dolor durante, después y al día siguiente.",
                "Horas de sueño y sensación de fatiga.",
            ],
            "confianza": 0.20,
            "restringir_calidad": False,
        }

    sessions_last_7_days = [
        session
        for session in sessions
        if _session_date(session) >= today - timedelta(days=6)
    ]

    sessions_last_14_days = [
        session
        for session in sessions
        if _session_date(session) >= today - timedelta(days=13)
    ]

    sessions_last_48_hours = [
        session
        for session in sessions
        if _session_date(session) >= today - timedelta(days=2)
    ]

    alerts: list[str] = []
    recommendations: list[str] = []
    pending_questions: list[str] = []
    estado = "verde"
    restrict_quality = False

    pain_values = [
        pain_value
        for session in sessions_last_7_days
        for pain_value in [
            session.get("pain_during"),
            session.get("pain_after"),
            session.get("pain_next_day"),
        ]
        if pain_value is not None
    ]

    if pain_values:
        max_pain = max(pain_values)

        if max_pain >= 6:
            estado = "rojo"
            restrict_quality = True
            _add_unique(
                alerts,
                f"Se ha registrado dolor de rodilla alto ({max_pain}/10).",
            )
            _add_unique(
                recommendations,
                "Reduce la carga de carrera y evita calidad, cuestas y sprints.",
            )
            _add_unique(
                recommendations,
                "Considera una valoración profesional antes de progresar la carga.",
            )
        elif max_pain >= 4:
            if estado != "rojo":
                estado = "amarillo"

            restrict_quality = True
            _add_unique(
                alerts,
                f"Se ha registrado dolor de rodilla de {max_pain}/10.",
            )
            _add_unique(
                recommendations,
                "No programes calidad ni cuestas hasta que el dolor esté controlado.",
            )
            _add_unique(
                recommendations,
                "Si el dolor dura más de 24-48 horas, empeora o reaparece, valora fisioterapia o consulta médica.",
            )
        elif max_pain > 3:
            if estado != "rojo":
                estado = "amarillo"

            restrict_quality = True
            _add_unique(
                alerts,
                f"El dolor de rodilla supera el umbral de precaución ({max_pain}/10).",
            )
            _add_unique(
                recommendations,
                "Sustituye temporalmente la calidad por rodaje muy fácil o recuperación.",
            )
    else:
        pending_questions.append("No hay datos recientes de dolor de rodilla.")

    easy_runs_high_rpe = [
        session
        for session in sessions_last_14_days
        if session["sport"] == "Carrera"
        and session.get("session_type") in {"Rodaje fácil", "Tirada larga"}
        and session.get("rpe") is not None
        and session["rpe"] > 5
    ]

    if len(easy_runs_high_rpe) >= 2:
        if estado != "rojo":
            estado = "amarillo"

        _add_unique(
            alerts,
            "Dos o más rodajes fáciles recientes tienen RPE superior a 5/10.",
        )
        _add_unique(
            recommendations,
            "Reduce ritmo o volumen en los rodajes fáciles y prioriza una intensidad conversacional.",
        )

    hard_external_sessions = [
        session
        for session in sessions_last_48_hours
        if session["sport"] in {"Gimnasio", "Jiu-jitsu", "Bicicleta"}
        and session.get("rpe") is not None
        and session["rpe"] >= 7
    ]

    if len(hard_external_sessions) >= 2:
        if estado != "rojo":
            estado = "amarillo"

        _add_unique(
            alerts,
            "Hay dos o más sesiones duras de otros deportes en las últimas 48 horas.",
        )
        _add_unique(
            recommendations,
            "Adapta la próxima sesión de calidad: reduce volumen, baja intensidad o sustitúyela por recuperación.",
        )

    low_sleep_high_fatigue = [
        session
        for session in sessions_last_7_days
        if session.get("sleep_hours") is not None
        and session["sleep_hours"] < 6
        and session.get("fatigue") in {"Alta", "Muy alta"}
    ]

    if low_sleep_high_fatigue:
        if estado != "rojo":
            estado = "amarillo"

        _add_unique(
            alerts,
            "Se ha registrado sueño inferior a seis horas junto a fatiga alta.",
        )
        _add_unique(
            recommendations,
            "Evita sesiones intensas hasta recuperar sueño y reducir la fatiga.",
        )

    if not any(session.get("rpe") is not None for session in sessions_last_7_days):
        pending_questions.append("Falta RPE en las sesiones recientes.")

    if not any(session.get("sleep_hours") is not None for session in sessions_last_7_days):
        pending_questions.append("Faltan horas de sueño recientes.")

    if not any(session.get("fatigue") for session in sessions_last_7_days):
        pending_questions.append("Falta sensación de fatiga reciente.")

    available_data_groups = sum(
        [
            any(session.get("rpe") is not None for session in sessions_last_7_days),
            any(session.get("sleep_hours") is not None for session in sessions_last_7_days),
            any(session.get("fatigue") for session in sessions_last_7_days),
            bool(pain_values),
            any(session.get("duration_minutes") is not None for session in sessions_last_7_days),
        ]
    )

    confidence = min(0.95, 0.25 + available_data_groups * 0.14)

    if estado == "verde":
        summary = (
            "No aparecen señales deterministas de alerta en los datos registrados. "
            "Mantén una progresión gradual y continúa registrando recuperación."
        )
    elif estado == "amarillo":
        summary = (
            "Conviene actuar con precaución. Revisa las alertas antes de hacer "
            "una sesión de calidad o aumentar la carga."
        )
    else:
        summary = (
            "Se recomienda reducir carga y evitar intensidad hasta que mejoren "
            "las señales de dolor o recuperación."
        )

    return {
        "estado": estado,
        "resumen": summary,
        "alertas": alerts,
        "recomendaciones": recommendations,
        "preguntas_pendientes": pending_questions,
        "confianza": confidence,
        "restringir_calidad": restrict_quality,
    }

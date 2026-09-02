"""Evaluación determinista de una sesión concreta y su siguiente paso."""

from __future__ import annotations

from typing import Any


def get_max_knee_pain(session: dict[str, Any]) -> int | None:
    """Obtiene el máximo dolor de rodilla disponible para una sesión."""
    pain_values = [
        session.get("pain_during"),
        session.get("pain_after"),
        session.get("pain_next_day"),
    ]

    available_values = [
        int(value)
        for value in pain_values
        if value is not None
    ]

    return max(available_values) if available_values else None


def evaluate_selected_session(
    activity_session: dict[str, Any] | None,
    planned_training: dict[str, Any] | None,
    global_state: dict[str, Any],
) -> dict[str, Any]:
    """Evalúa una sesión sin modificar automáticamente el plan."""
    if activity_session is None:
        return {
            "estado": global_state.get("estado", "amarillo"),
            "resumen": (
                "No hay un entrenamiento realizado registrado para el día "
                "seleccionado. La recomendación se basa en el estado global."
            ),
            "decision_siguiente": "Mantener el plan con seguimiento",
            "recomendacion": (
                "Registra duración, RPE, sueño, fatiga y dolor de rodilla "
                "después de completar la sesión."
            ),
        }

    pain = get_max_knee_pain(activity_session)
    actual_rpe = activity_session.get("rpe")
    target_rpe = (
        planned_training.get("target_rpe")
        if planned_training
        else None
    )

    if pain is not None and pain >= 6:
        return {
            "estado": "rojo",
            "resumen": (
                f"La sesión presenta dolor de rodilla alto ({pain}/10)."
            ),
            "decision_siguiente": "Reducir carga y evitar intensidad",
            "recomendacion": (
                "No realices calidad, cuestas o sprints. Reduce la carga "
                "y considera una valoración profesional antes de progresar."
            ),
        }

    if pain is not None and pain >= 4:
        return {
            "estado": "amarillo",
            "resumen": (
                f"La sesión presenta dolor de rodilla de {pain}/10."
            ),
            "decision_siguiente": "Adaptar la siguiente sesión",
            "recomendacion": (
                "Sustituye temporalmente calidad o cuestas por rodaje fácil "
                "o recuperación. Si el dolor dura más de 24-48 horas, "
                "empeora o reaparece, valora consulta profesional."
            ),
        }

    if (
        actual_rpe is not None
        and target_rpe is not None
        and actual_rpe >= target_rpe + 2
    ):
        return {
            "estado": "amarillo",
            "resumen": (
                f"El RPE real ({actual_rpe}/10) fue superior al objetivo "
                f"({target_rpe}/10)."
            ),
            "decision_siguiente": "Mantener o reducir la siguiente carga",
            "recomendacion": (
                "No intentes recuperar carga perdida. Mantén la siguiente "
                "sesión fácil o reduce volumen e intensidad."
            ),
        }

    if (
        actual_rpe is not None
        and target_rpe is not None
        and actual_rpe <= target_rpe - 2
        and (pain is None or pain <= 2)
        and global_state.get("estado") == "verde"
    ):
        return {
            "estado": "verde",
            "resumen": (
                "La sesión se completó con un esfuerzo percibido menor "
                "que el previsto y sin alerta relevante de rodilla."
            ),
            "decision_siguiente": "Mantener el plan y valorar progresión gradual",
            "recomendacion": (
                "No aumentes automáticamente carga ni días de carrera. "
                "Si se mantienen buenas sensaciones varias semanas, puedes "
                "valorar progresar solo una variable: volumen o intensidad."
            ),
        }

    return {
        "estado": global_state.get("estado", "verde"),
        "resumen": (
            "No aparecen desviaciones relevantes entre los datos disponibles "
            "de esta sesión y el plan actual."
        ),
        "decision_siguiente": "Mantener la planificación prevista",
        "recomendacion": (
            "Continúa registrando RPE, sueño, fatiga y dolor de rodilla "
            "para mejorar la adaptación semanal."
        ),
    }

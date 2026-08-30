"""Validación y reglas deterministas relacionadas con competiciones."""

from __future__ import annotations

from typing import Any


class CompetitionValidationError(ValueError):
    """Error controlado al validar datos de una competición."""


def seconds_to_time(total_seconds: int | None) -> str:
    """Convierte segundos a formato M:SS o H:MM:SS."""
    if total_seconds is None:
        return "—"

    hours, remaining_seconds = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remaining_seconds, 60)

    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"

    return f"{minutes}:{seconds:02d}"


def parse_race_time(value: str) -> int:
    """Convierte M:SS o H:MM:SS a segundos."""
    cleaned_value = value.strip()

    if not cleaned_value:
        raise CompetitionValidationError(
            "El tiempo oficial es obligatorio."
        )

    parts = cleaned_value.split(":")

    if len(parts) not in {2, 3}:
        raise CompetitionValidationError(
            "Usa el formato M:SS o H:MM:SS. Ejemplo: 49:58."
        )

    try:
        numbers = [int(part) for part in parts]
    except ValueError as error:
        raise CompetitionValidationError(
            "El tiempo oficial debe contener solo números y dos puntos."
        ) from error

    if any(number < 0 for number in numbers):
        raise CompetitionValidationError(
            "El tiempo oficial no puede ser negativo."
        )

    if len(numbers) == 2:
        minutes, seconds = numbers

        if seconds >= 60:
            raise CompetitionValidationError(
                "Los segundos deben estar entre 0 y 59."
            )

        total_seconds = minutes * 60 + seconds
    else:
        hours, minutes, seconds = numbers

        if minutes >= 60 or seconds >= 60:
            raise CompetitionValidationError(
                "Los minutos y segundos deben estar entre 0 y 59."
            )

        total_seconds = hours * 3600 + minutes * 60 + seconds

    if total_seconds <= 0:
        raise CompetitionValidationError(
            "El tiempo oficial debe ser mayor que cero."
        )

    return total_seconds


def parse_optional_positive_integer(
    value: str,
    field_name: str,
) -> int | None:
    """Convierte un entero opcional positivo."""
    cleaned_value = value.strip()

    if not cleaned_value:
        return None

    try:
        parsed_value = int(cleaned_value)
    except ValueError as error:
        raise CompetitionValidationError(
            f"«{field_name}» debe ser un número entero."
        ) from error

    if parsed_value <= 0:
        raise CompetitionValidationError(
            f"«{field_name}» debe ser mayor que cero."
        )

    return parsed_value


def calculate_average_pace(
    official_time_seconds: int,
    distance_km: float,
) -> int:
    """Calcula ritmo medio redondeado a segundos por kilómetro."""
    if distance_km <= 0:
        raise CompetitionValidationError(
            "La distancia debe ser mayor que cero."
        )

    return round(official_time_seconds / distance_km)


def compare_result_with_goal(
    official_time_seconds: int | None,
    goal_time_seconds: int | None,
) -> dict[str, Any]:
    """Compara un tiempo oficial con el objetivo declarado."""
    if official_time_seconds is None:
        return {
            "available": False,
            "message": "Todavía no hay un tiempo oficial registrado.",
        }

    if goal_time_seconds is None:
        return {
            "available": False,
            "message": (
                "No hay un objetivo temporal definido para esta competición."
            ),
        }

    difference = official_time_seconds - goal_time_seconds

    if difference < 0:
        return {
            "available": True,
            "achieved": True,
            "difference_seconds": difference,
            "message": (
                f"Objetivo superado por {seconds_to_time(abs(difference))}."
            ),
        }

    if difference == 0:
        return {
            "available": True,
            "achieved": True,
            "difference_seconds": 0,
            "message": "Objetivo cumplido exactamente.",
        }

    return {
        "available": True,
        "achieved": False,
        "difference_seconds": difference,
        "message": (
            f"El resultado quedó a {seconds_to_time(difference)} del objetivo."
        ),
    }


def build_derby_plan_proposal(
    derby_competition: dict[str, Any],
) -> dict[str, Any]:
    """Genera una propuesta conservadora posterior al Derbi.

    La propuesta no modifica sesiones, objetivos ni plan existente.
    Requiere aceptación explícita del usuario.
    """
    official_time = derby_competition.get("official_time_seconds")

    if official_time is None:
        raise CompetitionValidationError(
            "Registra primero el tiempo oficial del Derbi."
        )

    sub_50_seconds = 50 * 60
    proposal: dict[str, Any] = {
        "competition": derby_competition["name"],
        "competition_date": derby_competition["competition_date"],
        "derby_time_seconds": official_time,
        "derby_time": seconds_to_time(official_time),
        "automatic_plan_change": False,
    }

    if official_time <= 48 * 60 + 30:
        proposal.update(
            {
                "proposed_san_silvestre_target": "49:00",
                "target_time_seconds": 49 * 60,
                "confidence": "Media",
                "rationale": (
                    "El resultado del Derbi está claramente por debajo de "
                    "50 minutos. Puede valorarse un objetivo más ambicioso, "
                    "pero la San Silvestre tiene contexto, desnivel y "
                    "masificación diferentes."
                ),
                "training_focus": [
                    "Mantener dos sesiones de carrera semanales salvo confirmación expresa.",
                    "Introducir de forma gradual bloques a ritmo de competición.",
                    "Priorizar recuperación tras jiu-jitsu, gimnasio y bicicleta.",
                    "No aumentar simultáneamente volumen e intensidad.",
                ],
            }
        )
    elif official_time < sub_50_seconds:
        proposal.update(
            {
                "proposed_san_silvestre_target": "Sub 50:00",
                "target_time_seconds": 49 * 60 + 59,
                "confidence": "Alta",
                "rationale": (
                    "El objetivo principal está respaldado por el resultado "
                    "del Derbi. Conviene consolidar el rendimiento en lugar "
                    "de aumentar carga de forma agresiva."
                ),
                "training_focus": [
                    "Conservar el objetivo sub-50.",
                    "Practicar bloques cortos y controlados a ritmo de 10 km.",
                    "Mantener rodajes fáciles realmente conversacionales.",
                    "Vigilar dolor de rodilla, sueño y fatiga.",
                ],
            }
        )
    elif official_time <= 51 * 60 + 30:
        proposal.update(
            {
                "proposed_san_silvestre_target": "Sub 50:00, sujeto a evolución",
                "target_time_seconds": 49 * 60 + 59,
                "confidence": "Media",
                "rationale": (
                    "El objetivo sub-50 sigue siendo posible, pero debe "
                    "priorizarse consistencia, salud de rodilla y calidad "
                    "bien distribuida antes de endurecer el plan."
                ),
                "training_focus": [
                    "No añadir automáticamente días de carrera.",
                    "Mejorar tolerancia al umbral y al ritmo de 10 km de forma gradual.",
                    "Evitar recuperar sesiones canceladas acumulando carga.",
                    "Revisar datos de rodajes fáciles y recuperación cada semana.",
                ],
            }
        )
    else:
        proposal.update(
            {
                "proposed_san_silvestre_target": "Reevaluar tras nuevas sesiones de control",
                "target_time_seconds": None,
                "confidence": "Baja",
                "rationale": (
                    "El resultado del Derbi no permite sostener con confianza "
                    "un objetivo más exigente sin revisar carga, salud, "
                    "recuperación y evolución de las siguientes semanas."
                ),
                "training_focus": [
                    "Priorizar continuidad y rodajes fáciles.",
                    "Revisar RPE, sueño, fatiga y dolor de rodilla.",
                    "Mantener calidad solo si la recuperación lo permite.",
                    "Definir el objetivo final tras nuevos datos de entrenamiento.",
                ],
            }
        )

    return proposal

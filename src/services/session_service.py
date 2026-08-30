"""Validación y normalización de entrenamientos realizados."""

from __future__ import annotations

from datetime import date
from typing import Any


class SessionValidationError(ValueError):
    """Error controlado al validar una sesión deportiva."""


def optional_float(value: str, field_name: str) -> float | None:
    """Convierte un texto decimal opcional en número, aceptando coma decimal."""
    cleaned_value = value.strip().replace(",", ".")

    if not cleaned_value:
        return None

    try:
        converted_value = float(cleaned_value)
    except ValueError as error:
        raise SessionValidationError(
            f"El campo «{field_name}» debe contener un número válido."
        ) from error

    if converted_value < 0:
        raise SessionValidationError(
            f"El campo «{field_name}» no puede ser negativo."
        )

    return converted_value


def optional_positive_integer(value: str, field_name: str) -> int | None:
    """Convierte un texto opcional a entero positivo."""
    cleaned_value = value.strip()

    if not cleaned_value:
        return None

    try:
        converted_value = int(cleaned_value)
    except ValueError as error:
        raise SessionValidationError(
            f"El campo «{field_name}» debe ser un número entero."
        ) from error

    if converted_value <= 0:
        raise SessionValidationError(
            f"El campo «{field_name}» debe ser mayor que cero."
        )

    return converted_value


def optional_pace_to_seconds(value: str) -> int | None:
    """Convierte un ritmo opcional MM:SS min/km a segundos por kilómetro."""
    cleaned_value = value.strip()

    if not cleaned_value:
        return None

    parts = cleaned_value.split(":")

    if len(parts) != 2:
        raise SessionValidationError(
            "El ritmo debe tener el formato MM:SS, por ejemplo «5:45»."
        )

    try:
        minutes = int(parts[0])
        seconds = int(parts[1])
    except ValueError as error:
        raise SessionValidationError(
            "El ritmo debe tener el formato MM:SS, por ejemplo «5:45»."
        ) from error

    if minutes < 0 or seconds < 0 or seconds >= 60:
        raise SessionValidationError("Introduce un ritmo válido en formato MM:SS.")

    total_seconds = minutes * 60 + seconds

    if total_seconds <= 0:
        raise SessionValidationError("El ritmo debe ser mayor que cero.")

    return total_seconds


def optional_score(value: str | int, field_name: str, minimum: int, maximum: int) -> int | None:
    """Convierte una puntuación opcional y comprueba su rango."""
    if value in ("Sin dato", "", None):
        return None

    try:
        converted_value = int(value)
    except (TypeError, ValueError) as error:
        raise SessionValidationError(
            f"El campo «{field_name}» debe ser un número entre {minimum} y {maximum}."
        ) from error

    if not minimum <= converted_value <= maximum:
        raise SessionValidationError(
            f"El campo «{field_name}» debe estar entre {minimum} y {maximum}."
        )

    return converted_value


def build_activity_session(
    *,
    session_date: date,
    sport: str,
    session_type: str,
    duration_minutes: str,
    distance_km: str,
    average_pace: str,
    average_heart_rate: str,
    max_heart_rate: str,
    elevation_gain_m: str,
    rpe: str | int,
    surface: str,
    shoes: str,
    pain_during: str | int,
    pain_after: str | int,
    pain_next_day: str | int,
    sleep_hours: str,
    fatigue: str,
    comments: str,
) -> dict[str, Any]:
    """Construye un registro limpio y validado para almacenar en SQLite."""
    if not sport:
        raise SessionValidationError("Debes seleccionar un deporte.")

    if not session_type:
        raise SessionValidationError("Debes seleccionar un tipo de sesión.")

    parsed_duration = optional_float(duration_minutes, "Duración")
    parsed_distance = optional_float(distance_km, "Distancia")

    if parsed_duration is not None and parsed_duration <= 0:
        raise SessionValidationError("La duración debe ser mayor que cero.")

    return {
        "session_date": session_date.isoformat(),
        "sport": sport,
        "session_type": session_type,
        "duration_minutes": parsed_duration,
        "distance_km": parsed_distance,
        "average_pace_seconds_per_km": optional_pace_to_seconds(average_pace),
        "average_heart_rate": optional_positive_integer(
            average_heart_rate,
            "Frecuencia cardiaca media",
        ),
        "max_heart_rate": optional_positive_integer(
            max_heart_rate,
            "Frecuencia cardiaca máxima",
        ),
        "elevation_gain_m": optional_float(elevation_gain_m, "Desnivel positivo"),
        "rpe": optional_score(rpe, "RPE", 1, 10),
        "surface": None if surface == "Sin dato" else surface,
        "shoes": shoes.strip() or None,
        "pain_during": optional_score(pain_during, "Dolor durante", 0, 10),
        "pain_after": optional_score(pain_after, "Dolor después", 0, 10),
        "pain_next_day": optional_score(
            pain_next_day,
            "Dolor al día siguiente",
            0,
            10,
        ),
        "sleep_hours": optional_float(sleep_hours, "Horas de sueño"),
        "fatigue": None if fatigue == "Sin dato" else fatigue,
        "comments": comments.strip() or None,
        "source": "Manual",
    }

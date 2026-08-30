"""Lectura, validación y normalización de archivos CSV y Excel."""

from __future__ import annotations

import re
import unicodedata
from datetime import time, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd


COLUMN_ALIASES = {
    "session_date": [
        "fecha",
        "date",
        "activity date",
        "start date",
        "fecha de actividad",
        "fecha de inicio",
    ],
    "sport": [
        "deporte",
        "sport",
        "activity type",
        "tipo de actividad",
        "actividad",
        "activity",
    ],
    "session_type": [
        "tipo de sesion",
        "session type",
        "workout type",
        "training type",
        "tipo entrenamiento",
    ],
    "duration_minutes": [
        "duracion",
        "duration",
        "elapsed time",
        "moving time",
        "tiempo",
        "tiempo transcurrido",
        "duracion minutos",
    ],
    "distance_km": [
        "distancia",
        "distance",
        "distance km",
        "kilometros",
        "km",
    ],
    "average_pace": [
        "ritmo",
        "pace",
        "average pace",
        "avg pace",
        "ritmo medio",
    ],
    "average_heart_rate": [
        "frecuencia cardiaca media",
        "fc media",
        "average heart rate",
        "avg heart rate",
        "heart rate",
    ],
    "max_heart_rate": [
        "frecuencia cardiaca maxima",
        "fc maxima",
        "max heart rate",
        "maximum heart rate",
    ],
    "elevation_gain_m": [
        "desnivel positivo",
        "elevation gain",
        "elevation",
        "elev gain",
        "ascenso",
    ],
    "rpe": [
        "rpe",
        "esfuerzo percibido",
        "perceived effort",
    ],
    "surface": [
        "superficie",
        "surface",
        "terrain",
        "terreno",
    ],
    "shoes": [
        "zapatillas",
        "shoes",
        "shoe",
        "calzado",
    ],
    "pain_during": [
        "dolor durante",
        "pain during",
    ],
    "pain_after": [
        "dolor despues",
        "dolor después",
        "pain after",
    ],
    "pain_next_day": [
        "dolor dia siguiente",
        "dolor día siguiente",
        "pain next day",
    ],
    "sleep_hours": [
        "horas de sueno",
        "horas de sueño",
        "sleep hours",
        "sleep",
    ],
    "fatigue": [
        "fatiga",
        "fatigue",
    ],
    "comments": [
        "comentarios",
        "comments",
        "notas",
        "notes",
        "descripcion",
        "description",
    ],
}

SPORT_MAPPING = {
    "run": "Carrera",
    "running": "Carrera",
    "carrera": "Carrera",
    "trail run": "Carrera",
    "ride": "Bicicleta",
    "cycling": "Bicicleta",
    "bike": "Bicicleta",
    "bici": "Bicicleta",
    "bicicleta": "Bicicleta",
    "weight training": "Gimnasio",
    "strength training": "Gimnasio",
    "gym": "Gimnasio",
    "gimnasio": "Gimnasio",
    "jiu jitsu": "Jiu-jitsu",
    "bjj": "Jiu-jitsu",
    "jiu-jitsu": "Jiu-jitsu",
    "rest": "Descanso",
    "descanso": "Descanso",
}

DEFAULT_SESSION_TYPE = {
    "Carrera": "Otro",
    "Gimnasio": "Otro",
    "Jiu-jitsu": "Otro",
    "Bicicleta": "Otro",
    "Descanso": "Descanso completo",
}


class ImportValidationError(ValueError):
    """Error controlado al validar una fila importada."""


def normalize_text(value: Any) -> str:
    """Normaliza textos para comparar encabezados de columnas."""
    normalized = unicodedata.normalize("NFD", str(value))
    normalized = "".join(
        character
        for character in normalized
        if unicodedata.category(character) != "Mn"
    )
    normalized = normalized.lower().strip()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)

    return normalized.strip()


def is_empty(value: Any) -> bool:
    """Indica si una celda no contiene un valor útil."""
    if value is None:
        return True

    if isinstance(value, str) and not value.strip():
        return True

    return bool(pd.isna(value))


def suggest_column_mapping(columns: list[str]) -> dict[str, str | None]:
    """Propone columnas para cada campo usando alias en español e inglés."""
    normalized_columns = {
        column: normalize_text(column)
        for column in columns
    }

    suggestions: dict[str, str | None] = {}

    for field_name, aliases in COLUMN_ALIASES.items():
        normalized_aliases = [normalize_text(alias) for alias in aliases]
        suggestion = None

        for column, normalized_column in normalized_columns.items():
            if normalized_column in normalized_aliases:
                suggestion = column
                break

        if suggestion is None:
            for column, normalized_column in normalized_columns.items():
                if any(
                    alias in normalized_column
                    or normalized_column in alias
                    for alias in normalized_aliases
                ):
                    suggestion = column
                    break

        suggestions[field_name] = suggestion

    return suggestions


def read_uploaded_dataframe(uploaded_file: Any) -> pd.DataFrame:
    """Lee un archivo CSV o Excel cargado desde Streamlit."""
    file_name = uploaded_file.name
    suffix = Path(file_name).suffix.lower()
    raw_content = uploaded_file.getvalue()

    if suffix == ".csv":
        encodings = ["utf-8-sig", "utf-8", "latin-1"]

        for encoding in encodings:
            try:
                return pd.read_csv(
                    BytesIO(raw_content),
                    encoding=encoding,
                    sep=None,
                    engine="python",
                )
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue

        raise ImportValidationError(
            "No se pudo leer el CSV. Comprueba la codificación o el separador."
        )

    if suffix in {".xlsx", ".xls"}:
        try:
            return pd.read_excel(BytesIO(raw_content))
        except Exception as error:
            raise ImportValidationError(
                "No se pudo leer el archivo Excel."
            ) from error

    raise ImportValidationError(
        "Formato no compatible. Usa CSV, XLSX o XLS."
    )


def parse_optional_float(value: Any, field_name: str) -> float | None:
    """Convierte un valor opcional a decimal."""
    if is_empty(value):
        return None

    if isinstance(value, (int, float)) and not pd.isna(value):
        parsed_value = float(value)
    else:
        cleaned_value = str(value).strip().replace(",", ".")

        try:
            parsed_value = float(cleaned_value)
        except ValueError as error:
            raise ImportValidationError(
                f"«{field_name}» debe ser numérico."
            ) from error

    if parsed_value < 0:
        raise ImportValidationError(
            f"«{field_name}» no puede ser negativo."
        )

    return parsed_value


def parse_optional_integer(value: Any, field_name: str) -> int | None:
    """Convierte un valor opcional a entero positivo."""
    parsed_value = parse_optional_float(value, field_name)

    if parsed_value is None:
        return None

    if not parsed_value.is_integer() or parsed_value <= 0:
        raise ImportValidationError(
            f"«{field_name}» debe ser un entero mayor que cero."
        )

    return int(parsed_value)


def parse_optional_score(
    value: Any,
    field_name: str,
    minimum: int,
    maximum: int,
) -> int | None:
    """Valida una escala numérica opcional."""
    parsed_value = parse_optional_float(value, field_name)

    if parsed_value is None:
        return None

    if not parsed_value.is_integer():
        raise ImportValidationError(
            f"«{field_name}» debe ser un número entero."
        )

    score = int(parsed_value)

    if not minimum <= score <= maximum:
        raise ImportValidationError(
            f"«{field_name}» debe estar entre {minimum} y {maximum}."
        )

    return score


def parse_date(value: Any) -> str:
    """Convierte una fecha a formato ISO YYYY-MM-DD."""
    if is_empty(value):
        raise ImportValidationError("La fecha es obligatoria.")

    parsed_date = pd.to_datetime(
        value,
        errors="coerce",
        dayfirst=True,
    )

    if pd.isna(parsed_date):
        raise ImportValidationError("La fecha no tiene un formato válido.")

    return parsed_date.date().isoformat()


def parse_optional_duration_minutes(value: Any) -> float | None:
    """Convierte duraciones en minutos o formatos HH:MM:SS a minutos."""
    if is_empty(value):
        return None

    if isinstance(value, timedelta):
        return value.total_seconds() / 60

    if isinstance(value, time):
        return (
            value.hour * 60
            + value.minute
            + value.second / 60
        )

    if isinstance(value, (int, float)) and not pd.isna(value):
        duration = float(value)
    else:
        cleaned_value = str(value).strip()

        if ":" in cleaned_value:
            parts = cleaned_value.split(":")

            try:
                numbers = [int(part) for part in parts]
            except ValueError as error:
                raise ImportValidationError(
                    "La duración debe ser numérica o tener formato HH:MM:SS."
                ) from error

            if len(numbers) == 3:
                hours, minutes, seconds = numbers
                duration = hours * 60 + minutes + seconds / 60
            elif len(numbers) == 2:
                minutes, seconds = numbers
                duration = minutes + seconds / 60
            else:
                raise ImportValidationError(
                    "La duración debe tener formato MM:SS o HH:MM:SS."
                )
        else:
            duration = parse_optional_float(cleaned_value, "Duración")

    if duration is not None and duration <= 0:
        raise ImportValidationError("La duración debe ser mayor que cero.")

    return duration


def parse_optional_pace(value: Any) -> int | None:
    """Convierte ritmo MM:SS min/km a segundos por kilómetro."""
    if is_empty(value):
        return None

    if isinstance(value, (int, float)) and not pd.isna(value):
        pace_seconds = round(float(value) * 60)
    else:
        cleaned_value = str(value).strip()

        if ":" not in cleaned_value:
            try:
                pace_seconds = round(float(cleaned_value.replace(",", ".")) * 60)
            except ValueError as error:
                raise ImportValidationError(
                    "El ritmo debe ser MM:SS o minutos decimales por km."
                ) from error
        else:
            parts = cleaned_value.split(":")

            if len(parts) != 2:
                raise ImportValidationError(
                    "El ritmo debe tener formato MM:SS."
                )

            try:
                minutes = int(parts[0])
                seconds = int(parts[1])
            except ValueError as error:
                raise ImportValidationError(
                    "El ritmo debe tener formato MM:SS."
                ) from error

            if minutes < 0 or seconds < 0 or seconds >= 60:
                raise ImportValidationError(
                    "El ritmo debe tener formato MM:SS válido."
                )

            pace_seconds = minutes * 60 + seconds

    if pace_seconds <= 0:
        raise ImportValidationError("El ritmo debe ser mayor que cero.")

    return pace_seconds


def normalize_sport(value: Any, default_sport: str) -> str:
    """Normaliza nombres frecuentes de deporte al vocabulario de la app."""
    if is_empty(value):
        return default_sport

    normalized_value = normalize_text(value)

    return SPORT_MAPPING.get(normalized_value, str(value).strip())


def normalize_optional_text(value: Any) -> str | None:
    """Convierte una celda opcional a texto limpio."""
    if is_empty(value):
        return None

    return str(value).strip()


def session_signature(session: dict[str, Any]) -> tuple[Any, ...]:
    """Genera una firma práctica para detectar duplicados de importación."""
    duration = session.get("duration_minutes")
    distance = session.get("distance_km")

    return (
        session["session_date"],
        session["sport"].strip().lower(),
        session["session_type"].strip().lower(),
        round(float(duration), 2) if duration is not None else None,
        round(float(distance), 3) if distance is not None else None,
    )


def validate_import_dataframe(
    dataframe: pd.DataFrame,
    mapping: dict[str, str | None],
    source: str,
    default_sport: str,
    existing_sessions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Valida filas de un archivo y separa sesiones válidas y errores."""
    date_column = mapping.get("session_date")

    if not date_column:
        raise ImportValidationError(
            "Debes asignar una columna de fecha antes de validar."
        )

    existing_signatures = {
        session_signature(session)
        for session in existing_sessions
    }

    imported_signatures: set[tuple[Any, ...]] = set()
    valid_sessions: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    def get_value(row: pd.Series, field_name: str) -> Any:
        column_name = mapping.get(field_name)

        if not column_name:
            return None

        return row[column_name]

    for dataframe_index, row in dataframe.iterrows():
        row_number = int(dataframe_index) + 2

        try:
            sport = normalize_sport(
                get_value(row, "sport"),
                default_sport,
            )
            session_type = (
                normalize_optional_text(get_value(row, "session_type"))
                or DEFAULT_SESSION_TYPE.get(sport, "Otro")
            )

            session = {
                "session_date": parse_date(get_value(row, "session_date")),
                "sport": sport,
                "session_type": session_type,
                "duration_minutes": parse_optional_duration_minutes(
                    get_value(row, "duration_minutes")
                ),
                "distance_km": parse_optional_float(
                    get_value(row, "distance_km"),
                    "Distancia",
                ),
                "average_pace_seconds_per_km": parse_optional_pace(
                    get_value(row, "average_pace")
                ),
                "average_heart_rate": parse_optional_integer(
                    get_value(row, "average_heart_rate"),
                    "Frecuencia cardiaca media",
                ),
                "max_heart_rate": parse_optional_integer(
                    get_value(row, "max_heart_rate"),
                    "Frecuencia cardiaca máxima",
                ),
                "elevation_gain_m": parse_optional_float(
                    get_value(row, "elevation_gain_m"),
                    "Desnivel positivo",
                ),
                "rpe": parse_optional_score(
                    get_value(row, "rpe"),
                    "RPE",
                    1,
                    10,
                ),
                "surface": normalize_optional_text(
                    get_value(row, "surface")
                ),
                "shoes": normalize_optional_text(
                    get_value(row, "shoes")
                ),
                "pain_during": parse_optional_score(
                    get_value(row, "pain_during"),
                    "Dolor durante",
                    0,
                    10,
                ),
                "pain_after": parse_optional_score(
                    get_value(row, "pain_after"),
                    "Dolor después",
                    0,
                    10,
                ),
                "pain_next_day": parse_optional_score(
                    get_value(row, "pain_next_day"),
                    "Dolor al día siguiente",
                    0,
                    10,
                ),
                "sleep_hours": parse_optional_float(
                    get_value(row, "sleep_hours"),
                    "Horas de sueño",
                ),
                "fatigue": normalize_optional_text(
                    get_value(row, "fatigue")
                ),
                "comments": normalize_optional_text(
                    get_value(row, "comments")
                ),
                "source": source,
            }

            signature = session_signature(session)

            if signature in existing_signatures:
                raise ImportValidationError(
                    "Posible duplicado: ya existe una sesión con fecha, "
                    "deporte, tipo, duración y distancia coincidentes."
                )

            if signature in imported_signatures:
                raise ImportValidationError(
                    "Posible duplicado dentro del archivo importado."
                )

            imported_signatures.add(signature)
            valid_sessions.append(session)

        except ImportValidationError as error:
            errors.append(
                {
                    "Fila": row_number,
                    "Error": str(error),
                }
            )

    return valid_sessions, errors

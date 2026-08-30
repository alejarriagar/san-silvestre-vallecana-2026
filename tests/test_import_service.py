"""Pruebas básicas de importación de datos."""

import pandas as pd

from src.services.import_service import (
    suggest_column_mapping,
    validate_import_dataframe,
)


def test_suggest_column_mapping_recognizes_spanish_columns():
    suggestions = suggest_column_mapping(
        ["Fecha", "Deporte", "Distancia", "Duración", "Ritmo"]
    )

    assert suggestions["session_date"] == "Fecha"
    assert suggestions["sport"] == "Deporte"
    assert suggestions["distance_km"] == "Distancia"


def test_import_validation_normalizes_a_running_session():
    dataframe = pd.DataFrame(
        [
            {
                "Fecha": "29/08/2026",
                "Deporte": "Running",
                "Distancia": "6,0",
                "Duración": "35:12",
                "Ritmo": "5:52",
            }
        ]
    )

    mapping = {
        "session_date": "Fecha",
        "sport": "Deporte",
        "session_type": None,
        "duration_minutes": "Duración",
        "distance_km": "Distancia",
        "average_pace": "Ritmo",
        "average_heart_rate": None,
        "max_heart_rate": None,
        "elevation_gain_m": None,
        "rpe": None,
        "surface": None,
        "shoes": None,
        "pain_during": None,
        "pain_after": None,
        "pain_next_day": None,
        "sleep_hours": None,
        "fatigue": None,
        "comments": None,
    }

    valid_sessions, errors = validate_import_dataframe(
        dataframe=dataframe,
        mapping=mapping,
        source="CSV",
        default_sport="Carrera",
        existing_sessions=[],
    )

    assert not errors
    assert len(valid_sessions) == 1
    assert valid_sessions[0]["sport"] == "Carrera"
    assert valid_sessions[0]["distance_km"] == 6.0
    assert valid_sessions[0]["average_pace_seconds_per_km"] == 352


def test_import_validation_rejects_existing_duplicates():
    dataframe = pd.DataFrame(
        [
            {
                "Fecha": "2026-08-29",
                "Deporte": "Carrera",
                "Distancia": 6.0,
                "Duración": 35,
            }
        ]
    )

    mapping = {
        "session_date": "Fecha",
        "sport": "Deporte",
        "session_type": None,
        "duration_minutes": "Duración",
        "distance_km": "Distancia",
        "average_pace": None,
        "average_heart_rate": None,
        "max_heart_rate": None,
        "elevation_gain_m": None,
        "rpe": None,
        "surface": None,
        "shoes": None,
        "pain_during": None,
        "pain_after": None,
        "pain_next_day": None,
        "sleep_hours": None,
        "fatigue": None,
        "comments": None,
    }

    existing_sessions = [
        {
            "session_date": "2026-08-29",
            "sport": "Carrera",
            "session_type": "Otro",
            "duration_minutes": 35.0,
            "distance_km": 6.0,
        }
    ]

    valid_sessions, errors = validate_import_dataframe(
        dataframe=dataframe,
        mapping=mapping,
        source="CSV",
        default_sport="Carrera",
        existing_sessions=existing_sessions,
    )

    assert not valid_sessions
    assert len(errors) == 1
    assert "duplicado" in errors[0]["Error"].lower()

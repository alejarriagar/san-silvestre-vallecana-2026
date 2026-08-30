"""Pruebas de las reglas deterministas de seguridad."""

from datetime import date

from src.services.safety_rules import evaluate_training_state

TODAY = date(2026, 8, 30)


def make_session(**changes):
    """Crea una sesión mínima para pruebas."""
    session = {
        "session_date": "2026-08-30",
        "sport": "Carrera",
        "session_type": "Rodaje fácil",
        "duration_minutes": 40,
        "rpe": 4,
        "sleep_hours": 7.5,
        "fatigue": "Baja",
        "pain_during": 0,
        "pain_after": 0,
        "pain_next_day": 0,
    }
    session.update(changes)
    return session


def test_without_sessions_returns_provisional_yellow_state():
    state = evaluate_training_state([], TODAY)

    assert state["estado"] == "amarillo"
    assert state["confianza"] == 0.20


def test_knee_pain_of_four_restricts_quality_training():
    state = evaluate_training_state(
        [make_session(pain_after=4)],
        TODAY,
    )

    assert state["estado"] == "amarillo"
    assert state["restringir_calidad"] is True


def test_severe_knee_pain_returns_red_state():
    state = evaluate_training_state(
        [make_session(pain_next_day=6)],
        TODAY,
    )

    assert state["estado"] == "rojo"
    assert state["restringir_calidad"] is True


def test_two_high_rpe_easy_runs_create_warning():
    sessions = [
        make_session(session_date="2026-08-25", rpe=6),
        make_session(session_date="2026-08-28", rpe=7),
    ]

    state = evaluate_training_state(sessions, TODAY)

    assert state["estado"] == "amarillo"
    assert any("RPE superior a 5/10" in alert for alert in state["alertas"])

"""Pruebas de evaluación de una sesión concreta."""

from src.services.session_evaluation_service import (
    evaluate_selected_session,
)


def test_high_knee_pain_recommends_reducing_load():
    evaluation = evaluate_selected_session(
        activity_session={
            "rpe": 6,
            "pain_during": 0,
            "pain_after": 5,
            "pain_next_day": 4,
        },
        planned_training={
            "target_rpe": 5,
        },
        global_state={
            "estado": "verde",
        },
    )

    assert evaluation["estado"] == "amarillo"
    assert evaluation["decision_siguiente"] == "Adaptar la siguiente sesión"


def test_high_rpe_against_plan_recommends_caution():
    evaluation = evaluate_selected_session(
        activity_session={
            "rpe": 8,
            "pain_during": 0,
            "pain_after": 0,
            "pain_next_day": 0,
        },
        planned_training={
            "target_rpe": 5,
        },
        global_state={
            "estado": "verde",
        },
    )

    assert evaluation["estado"] == "amarillo"
    assert "reducir" in evaluation["decision_siguiente"].lower()


def test_good_session_does_not_automatically_increase_plan():
    evaluation = evaluate_selected_session(
        activity_session={
            "rpe": 3,
            "pain_during": 0,
            "pain_after": 0,
            "pain_next_day": 0,
        },
        planned_training={
            "target_rpe": 5,
        },
        global_state={
            "estado": "verde",
        },
    )

    assert evaluation["estado"] == "verde"
    assert "Mantener" in evaluation["decision_siguiente"]

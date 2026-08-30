"""Pruebas de tiempos, ritmo y propuestas posteriores al Derbi."""

from src.services.competition_service import (
    build_derby_plan_proposal,
    calculate_average_pace,
    parse_race_time,
)


def test_parse_race_time_supports_minutes_and_seconds():
    assert parse_race_time("49:58") == 2998


def test_parse_race_time_supports_hours_minutes_and_seconds():
    assert parse_race_time("1:02:30") == 3750


def test_average_pace_for_ten_kilometres():
    assert calculate_average_pace(3000, 10.0) == 300


def test_fast_derby_creates_more_ambitious_proposal():
    proposal = build_derby_plan_proposal(
        {
            "name": "XVI Derbi de las Aficiones 2026",
            "competition_date": "2026-10-25",
            "official_time_seconds": 2890,
        }
    )

    assert proposal["proposed_san_silvestre_target"] == "49:00"
    assert proposal["automatic_plan_change"] is False

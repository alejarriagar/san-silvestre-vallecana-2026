"""Pruebas de validación de sesiones deportivas."""

import pytest

from src.services.session_service import (
    SessionValidationError,
    optional_duration_to_minutes,
)


def test_duration_accepts_plain_minutes():
    assert optional_duration_to_minutes("45") == 45.0


def test_duration_accepts_minutes_and_seconds():
    assert optional_duration_to_minutes("45:23") == pytest.approx(
        45 + 23 / 60
    )


def test_duration_accepts_hours_minutes_and_seconds():
    assert optional_duration_to_minutes("1:45:23") == pytest.approx(
        105 + 23 / 60
    )


def test_duration_rejects_invalid_seconds():
    with pytest.raises(SessionValidationError):
        optional_duration_to_minutes("45:75")


def test_duration_rejects_invalid_format():
    with pytest.raises(SessionValidationError):
        optional_duration_to_minutes("45:2.36")

"""Navegación principal de la aplicación."""

from __future__ import annotations

from datetime import date

import streamlit as st

from src.services.analytics_service import calculate_dashboard_metrics
from src.services.safety_rules import evaluate_training_state

PRIMARY_SECTIONS = [
    "Inicio",
    "Progreso",
    "Plan completo",
    "Competiciones",
    "Más",
]

SECONDARY_SECTIONS = [
    "Importar datos",
    "Perfil",
]

STATUS_CHIP_STYLES = {
    "verde": ("#33e0a1", "Carga adecuada"),
    "amarillo": ("#ffb547", "Precaución"),
    "rojo": ("#ff5d7d", "Reducir carga"),
}


def _get_live_status() -> tuple[str, str]:
    """Calcula el estado determinista global para el chip de estado.

    Reutiliza las mismas reglas del dashboard. No llama a ningún LLM ni
    proveedor externo: es un cálculo local a partir de los datos guardados.
    """
    today = date.today()
    metrics = calculate_dashboard_metrics(today)
    state = evaluate_training_state(
        metrics["sessions_last_28_days"],
        today,
    )

    return STATUS_CHIP_STYLES.get(
        state["estado"],
        STATUS_CHIP_STYLES["amarillo"],
    )


def render_navigation() -> str:
    """Renderiza la marca, el chip de estado y la navegación principal."""
    chip_color, chip_label = _get_live_status()

    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
            <div style="width:26px;height:26px;border-radius:8px;
                        background:linear-gradient(135deg, #22e5ff, #8a5cff);">
            </div>
            <div style="font-family:'Space Grotesk',sans-serif;font-weight:700;
                        color:#eef2fb;font-size:1.05rem;">
                Preparación 2026
            </div>
        </div>
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:16px;">
            <span style="width:8px;height:8px;border-radius:50%;
                         background:{chip_color};display:inline-block;
                         box-shadow:0 0 6px {chip_color};"></span>
            <span style="color:{chip_color};font-size:0.76rem;font-weight:700;
                         letter-spacing:0.04em;text-transform:uppercase;">
                {chip_label}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    primary_section = st.radio(
        "Sección principal",
        options=PRIMARY_SECTIONS,
        label_visibility="collapsed",
    )

    if primary_section == "Más":
        return st.selectbox(
            "Herramientas adicionales",
            options=SECONDARY_SECTIONS,
        )

    return primary_section

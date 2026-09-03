"""Navegación principal de la aplicación."""

from __future__ import annotations

import streamlit as st


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


def render_navigation() -> str:
    """Renderiza la navegación y devuelve la sección activa."""
    st.markdown("### Preparación 2026")

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

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
    st.markdown(
        """
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">
            <div style="width:26px;height:26px;border-radius:8px;
                        background:linear-gradient(135deg, #22e5ff, #8a5cff);">
            </div>
            <div style="font-family:'Space Grotesk',sans-serif;font-weight:700;
                        color:#eef2fb;font-size:1.05rem;">
                Preparación 2026
            </div>
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

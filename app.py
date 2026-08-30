"""Aplicación Streamlit para preparar la San Silvestre Vallecana 2026."""

from __future__ import annotations

import os
from datetime import date

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

APP_TITLE = "Preparación San Silvestre Vallecana 2026"
DERBI_DATE = date(2026, 10, 25)
SAN_SILVESTRE_DATE = date(2026, 12, 31)


def days_until(target_date: date) -> int:
    """Calcula los días restantes hasta una fecha."""
    return max((target_date - date.today()).days, 0)


def render_coach_panel() -> None:
    """Muestra el primer panel de entrenador en modo demostración."""
    llm_provider = os.getenv("LLM_PROVIDER", "demo")
    openai_api_key = os.getenv("OPENAI_API_KEY", "")

    st.subheader("🧠 Entrenador de preparación")

    if llm_provider == "demo" or not openai_api_key:
        st.info(
            "Modo demo activo: añade una clave de modelo para activar "
            "el análisis personalizado."
        )

    st.success("Estado general inicial: verde")

    left_column, right_column = st.columns(2)

    with left_column:
        st.markdown("#### Resumen")
        st.write(
            "El objetivo principal es correr 10 km por debajo de 50 minutos "
            "en la San Silvestre Vallecana 2026. La planificación inicial "
            "mantendrá dos sesiones de carrera por semana."
        )

        st.markdown("#### Aspectos positivos")
        st.markdown(
            "- Buena base deportiva general.\n"
            "- Objetivo claro y medible.\n"
            "- Inicio progresivo y conservador."
        )

    with right_column:
        st.markdown("#### Alertas y ajustes")
        st.markdown(
            "- Registrar dolor de rodilla durante, después y al día siguiente.\n"
            "- No añadir días de carrera automáticamente.\n"
            "- Evitar calidad o cuestas si el dolor supera 3/10."
        )

        st.markdown("#### Datos pendientes")
        st.markdown(
            "- Entrenamientos realizados.\n"
            "- Sueño y fatiga.\n"
            "- Evolución del dolor de rodilla.\n"
            "- Resultado del Derbi de las Aficiones."
        )


def main() -> None:
    """Configura y muestra la pantalla inicial."""
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="🏃",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("🏃 Preparación San Silvestre Vallecana 2026")
    st.caption("Planificación, registro y análisis de entrenamiento")

    with st.sidebar:
        st.header("Navegación")
        st.radio(
            "Sección",
            options=[
                "Dashboard",
                "Plan semanal y mensual",
                "Registrar entrenamiento",
                "Importar datos",
                "Competiciones",
                "Análisis y estadísticas",
                "Perfil",
            ],
            disabled=True,
            help="Las secciones se habilitarán progresivamente.",
        )

        st.divider()
        st.markdown("#### Objetivo principal")
        st.write("10 km por debajo de 50:00")
        st.write("Ritmo de referencia: 4:59 min/km")

    render_coach_panel()

    st.divider()
    st.subheader("Resumen de preparación")

    metric_1, metric_2, metric_3, metric_4 = st.columns(4)

    metric_1.metric("Próxima competición", "Derbi de las Aficiones")
    metric_2.metric("Días para el Derbi", days_until(DERBI_DATE))
    metric_3.metric(
        "Días para la San Silvestre",
        days_until(SAN_SILVESTRE_DATE),
    )
    metric_4.metric("Estado de rodilla", "Sin datos")

    st.divider()
    st.subheader("Siguiente incremento")
    st.write(
        "Añadiremos una base de datos SQLite, el perfil editable, "
        "las competiciones precargadas y el plan inicial."
    )


if __name__ == "__main__":
    main()

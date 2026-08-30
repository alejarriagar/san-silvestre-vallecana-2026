"""Aplicación Streamlit para preparar la San Silvestre Vallecana 2026."""

from __future__ import annotations

import os
from datetime import date

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from src.ui.training_log import render_training_log
from src.services.analytics_service import calculate_dashboard_metrics
from src.services.safety_rules import evaluate_training_state



from src.database import (
    TRAINING_STATUSES,
    get_competitions,
    get_completion_summary,
    get_next_competition,
    get_next_training,
    get_profile,
    get_training_plan,
    get_weekly_planned_distance,
    init_database,
    update_profile,
    update_training_status,
)

load_dotenv()

APP_TITLE = "Preparación San Silvestre Vallecana 2026"


def seconds_to_time(total_seconds: int | None) -> str:
    """Convierte segundos a formato horas:minutos:segundos."""
    if total_seconds is None:
        return "—"

    hours, remaining_seconds = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remaining_seconds, 60)

    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"

    return f"{minutes}:{seconds:02d}"


def render_coach_panel() -> None:
    """Muestra la versión inicial del entrenador en modo demo."""
    llm_provider = os.getenv("LLM_PROVIDER", "demo")
    openai_api_key = os.getenv("OPENAI_API_KEY", "")

    st.subheader("🧠 Entrenador de preparación")

    if llm_provider == "demo" or not openai_api_key:
        st.info(
            "Modo demo activo: añade una clave de modelo para activar "
            "el análisis personalizado."
        )

    st.caption(
        "El dashboard aplica reglas deterministas basadas en dolor, sueño, "
        "fatiga, RPE y carga disponible."
    )


    left_column, right_column = st.columns(2)

    with left_column:
        st.markdown("#### Resumen")
        st.write(
            "La planificación inicial mantiene dos sesiones de carrera por "
            "semana y prioriza progresar sin agravar la molestia de rodilla."
        )

        st.markdown("#### Aspectos positivos")
        st.markdown(
            "- Buena base deportiva general.\n"
            "- Objetivo concreto: 10 km por debajo de 50:00.\n"
            "- Inicio progresivo y controlado."
        )

    with right_column:
        st.markdown("#### Alertas y ajustes")
        st.markdown(
            "- Registrar el dolor de rodilla durante, después y al día siguiente.\n"
            "- No recuperar automáticamente sesiones canceladas.\n"
            "- Evitar calidad o cuestas si el dolor supera 3/10."
        )

        st.markdown("#### Datos que faltan")
        st.markdown(
            "- Entrenamientos realizados.\n"
            "- Sueño, fatiga y RPE.\n"
            "- Evolución del dolor de rodilla."
        )


def render_dashboard() -> None:
    """Renderiza la pantalla principal con datos reales y reglas de seguridad."""
    today = date.today()

    metrics = calculate_dashboard_metrics(today)
    training_state = evaluate_training_state(
        metrics["sessions_last_28_days"],
        today,
    )

    next_training = get_next_training(today)
    next_competition = get_next_competition(today)
    completion_summary = metrics["completion_summary"]

    st.title("🏃 Preparación San Silvestre Vallecana 2026")
    st.caption("Planificación, registro y análisis de entrenamiento")

    render_coach_panel()

    state_message = (
        f"Estado general: **{training_state['estado'].upper()}** · "
        f"Confianza del análisis: {training_state['confianza']:.0%}"
    )

    if training_state["estado"] == "verde":
        st.success(state_message)
    elif training_state["estado"] == "amarillo":
        st.warning(state_message)
    else:
        st.error(state_message)

    st.write(training_state["resumen"])

    st.divider()
    st.subheader("Resumen de carga")

    col_1, col_2, col_3, col_4, col_5 = st.columns(5)

    col_1.metric(
        "Km carrera esta semana",
        f"{metrics['weekly_running_km']:.1f} km",
    )
    col_2.metric(
        "Km carrera este mes",
        f"{metrics['monthly_running_km']:.1f} km",
    )
    col_3.metric(
        "Carga estimada semanal",
        f"{metrics['total_weekly_load']:.0f}",
    )
    col_4.metric(
        "Sesiones completadas",
        f"{completion_summary['percentage']:.0f}%",
    )

    if next_competition:
        days_to_competition = max(
            (
                date.fromisoformat(next_competition["competition_date"]) - today
            ).days,
            0,
        )
        col_5.metric("Días hasta competición", days_to_competition)
    else:
        col_5.metric("Días hasta competición", "—")

    st.caption(
        "Kilómetros semanales: "
        f"{metrics['weekly_running_km']:.1f} km reales / "
        f"{metrics['planned_weekly_running_km']:.1f} km previstos."
    )
    st.caption(
        "Carga estimada = duración en minutos × RPE. "
        "Solo se incluye cuando ambos datos están disponibles."
    )

    if metrics["weekly_load_by_sport"]:
        st.subheader("Carga semanal por deporte")

        load_rows = [
            {
                "Deporte": sport,
                "Carga estimada": round(load, 1),
            }
            for sport, load in metrics["weekly_load_by_sport"].items()
        ]

        st.dataframe(
            pd.DataFrame(load_rows),
            use_container_width=True,
            hide_index=True,
        )

    st.divider()
    st.subheader("Alertas y recomendaciones")

    if training_state["alertas"]:
        for alert in training_state["alertas"]:
            st.warning(alert)
    else:
        st.info("No hay alertas deterministas activas en los datos disponibles.")

    for recommendation in training_state["recomendaciones"]:
        st.write(f"- {recommendation}")

    if training_state["preguntas_pendientes"]:
        with st.expander("Datos que faltan para mejorar la recomendación"):
            for question in training_state["preguntas_pendientes"]:
                st.write(f"- {question}")

    st.divider()
    st.subheader("Último entrenamiento realizado")

    last_session = metrics["last_activity_session"]

    if last_session:
        st.write(
            f"**{last_session['session_date']} · {last_session['sport']} · "
            f"{last_session['session_type']}**"
        )
        st.write(
            f"Distancia: {last_session['distance_km'] or '—'} km · "
            f"Duración: {last_session['duration_minutes'] or '—'} min · "
            f"RPE: {last_session['rpe'] if last_session['rpe'] is not None else '—'}"
        )
    else:
        st.info("Todavía no hay entrenamientos realizados registrados.")

    if next_training:
        st.divider()
        st.subheader("Próximo entrenamiento planificado")

        st.markdown(
            f"### {next_training['session_type']} · "
            f"{next_training['planned_date']}"
        )
        st.write(next_training["description"])
        st.write(f"**RPE objetivo:** {next_training['target_rpe']}/10")
        st.write(f"**Terreno recomendado:** {next_training['terrain']}")

        if training_state["restringir_calidad"]:
            st.warning(
                "Las reglas actuales recomiendan no realizar calidad ni cuestas "
                "hasta revisar dolor y recuperación."
            )

    st.divider()
    st.warning(
        "La aplicación no sustituye la valoración de un profesional sanitario. "
        "Si aparece hinchazón, bloqueo, inestabilidad o sensación de fallo en "
        "la rodilla, reduce carga y consulta a un profesional."
    )




def render_plan() -> None:
    """Muestra el bloque inicial de entrenamientos y permite cambiar su estado."""
    st.title("📅 Plan semanal y mensual")
    st.caption(
        "Las fechas de carrera se han propuesto en martes y domingo para "
        "evitar los días habituales de jiu-jitsu. Podrán editarse más adelante."
    )

    plan = get_training_plan()

    if not plan:
        st.info("No hay entrenamientos planificados.")
        return

    rows = [
        {
            "Fecha": training["planned_date"],
            "Deporte": training["sport"],
            "Tipo": training["session_type"],
            "Descripción": training["description"],
            "Km objetivo": training["target_distance_km"],
            "RPE": training["target_rpe"],
            "Estado": training["status"],
            "Descarga": "Sí" if training["is_deload"] else "No",
        }
        for training in plan
    ]

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Detalle de las sesiones")

    for training in plan:
        label = (
            f"{training['planned_date']} · {training['session_type']} "
            f"({training['status']})"
        )

        with st.expander(label):
            st.write(training["description"])
            st.write(f"**Intensidad:** {training['target_intensity']}")
            st.write(f"**RPE objetivo:** {training['target_rpe']}/10")
            st.write(f"**Ritmo orientativo:** {training['target_pace']}")
            st.write(f"**Terreno recomendado:** {training['terrain']}")
            st.write(f"**Calentamiento:** {training['warmup']}")
            st.write(f"**Parte principal:** {training['main_set']}")
            st.write(f"**Vuelta a la calma:** {training['cooldown']}")
            st.write(f"**Razonamiento:** {training['rationale']}")

    st.divider()
    st.subheader("Actualizar estado de una sesión")

    training_options = {
        training["id"]: (
            f"{training['planned_date']} · {training['session_type']} · "
            f"{training['description']}"
        )
        for training in plan
    }

    selected_training_id = st.selectbox(
        "Entrenamiento",
        options=list(training_options),
        format_func=lambda training_id: training_options[training_id],
    )

    selected_training = next(
        training for training in plan if training["id"] == selected_training_id
    )

    new_status = st.selectbox(
        "Nuevo estado",
        options=TRAINING_STATUSES,
        index=TRAINING_STATUSES.index(selected_training["status"]),
    )

    if st.button("Guardar estado", type="primary"):
        update_training_status(selected_training_id, new_status)
        st.success("Estado actualizado correctamente.")
        st.rerun()


def render_profile() -> None:
    """Permite editar el perfil deportivo inicial."""
    profile = get_profile()

    st.title("👤 Perfil deportivo")
    st.caption("Estos datos se usarán más adelante para contextualizar el plan y el entrenador.")

    with st.form("profile_form"):
        col_1, col_2 = st.columns(2)

        with col_1:
            sex = st.selectbox(
                "Sexo",
                options=["Hombre", "Mujer", "Otro", "Prefiero no indicarlo"],
                index=["Hombre", "Mujer", "Otro", "Prefiero no indicarlo"].index(
                    profile.get("sex", "Hombre")
                ),
            )
            age = st.number_input(
                "Edad",
                min_value=14,
                max_value=100,
                value=int(profile.get("age", 31)),
            )
            height_cm = st.number_input(
                "Altura (cm)",
                min_value=100.0,
                max_value=230.0,
                value=float(profile.get("height_cm") or 178.0),
                step=0.5,
            )
            weight_kg = st.number_input(
                "Peso (kg)",
                min_value=30.0,
                max_value=250.0,
                value=float(profile.get("weight_kg") or 80.0),
                step=0.1,
            )

        with col_2:
            diet = st.text_input(
                "Alimentación",
                value=profile.get("diet", "Omnívora"),
            )
            alcohol_consumption = st.selectbox(
                "Consumo de alcohol",
                options=["No consume alcohol", "Ocasional", "Regular"],
                index=["No consume alcohol", "Ocasional", "Regular"].index(
                    profile.get("alcohol_consumption", "No consume alcohol")
                ),
            )
            coffee_per_day = st.number_input(
                "Cafés diarios aproximados",
                min_value=0,
                max_value=20,
                value=int(profile.get("coffee_per_day") or 0),
            )
            sleep_hours_baseline = st.number_input(
                "Horas habituales de sueño",
                min_value=0.0,
                max_value=24.0,
                value=float(profile.get("sleep_hours_baseline") or 7.5),
                step=0.25,
            )

        supplements = st.text_area(
            "Suplementos actuales",
            value=profile.get("supplements", ""),
        )
        training_preferences = st.text_area(
            "Deportes, disponibilidad y preferencias",
            value=profile.get("training_preferences", ""),
        )
        health_notes = st.text_area(
            "Salud, molestias y observaciones",
            value=profile.get("health_notes", ""),
        )

        submitted = st.form_submit_button("Guardar perfil", type="primary")

    if submitted:
        update_profile(
            {
                "sex": sex,
                "age": age,
                "height_cm": height_cm,
                "weight_kg": weight_kg,
                "health_notes": health_notes,
                "diet": diet,
                "alcohol_consumption": alcohol_consumption,
                "coffee_per_day": coffee_per_day,
                "sleep_hours_baseline": sleep_hours_baseline,
                "supplements": supplements,
                "training_preferences": training_preferences,
            }
        )
        st.success("Perfil guardado correctamente.")


def render_competitions() -> None:
    """Muestra las competiciones que se han precargado."""
    st.title("🏁 Competiciones")
    st.caption("Los formularios para registrar resultados se añadirán en el siguiente incremento.")

    competitions = get_competitions()

    for competition in competitions:
        with st.container(border=True):
            left_column, right_column = st.columns([2, 1])

            with left_column:
                st.subheader(competition["name"])
                st.write(f"**Fecha:** {competition['competition_date']}")
                st.write(f"**Distancia:** {competition['distance_km']} km")
                st.write(competition["comments"])

            with right_column:
                st.metric(
                    "Objetivo",
                    seconds_to_time(competition["goal_time_seconds"]),
                )
                st.metric(
                    "Tiempo oficial",
                    seconds_to_time(competition["official_time_seconds"]),
                )


def render_pending_section(title: str) -> None:
    """Muestra una pantalla temporal para módulos no implementados aún."""
    st.title(title)
    st.info(
        "Esta sección se habilitará después de implementar el formulario de "
        "registro de entrenamientos y la importación de archivos CSV y Excel."
    )


def main() -> None:
    """Configura la aplicación y dirige a cada sección."""
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="🏃",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_database()

    with st.sidebar:
        st.header("Navegación")
        page = st.radio(
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
        )

        st.divider()
        st.markdown("#### Objetivo principal")
        st.write("10 km por debajo de 50:00")
        st.write("Ritmo de referencia: 4:59 min/km")

    if page == "Dashboard":
        render_dashboard()
    elif page == "Plan semanal y mensual":
        render_plan()
    elif page == "Registrar entrenamiento":
        render_training_log()
    elif page == "Competiciones":
        render_competitions()
    elif page == "Perfil":
        render_profile()
    else:
        render_pending_section(page)



if __name__ == "__main__":
    main()

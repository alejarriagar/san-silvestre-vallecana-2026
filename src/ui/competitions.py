"""Interfaz Streamlit para competiciones y versiones de plan."""

from __future__ import annotations

import json
from datetime import date

import pandas as pd
import streamlit as st
from src.ui.styles import render_status_tag


from src.database import (
    create_competition,
    create_plan_version,
    get_competition_by_id,
    get_competitions,
    get_plan_versions,
    set_plan_version_decision,
    update_competition_result,
)
from src.services.competition_service import (
    CompetitionValidationError,
    build_derby_plan_proposal,
    calculate_average_pace,
    compare_result_with_goal,
    parse_optional_positive_integer,
    parse_race_time,
    seconds_to_time,
)

import html

def get_plan_version_status(accepted_value: int) -> str:
    """Convierte el estado numérico de SQLite a una etiqueta legible."""
    if accepted_value == 1:
        return "Aceptada"

    if accepted_value == -1:
        return "Rechazada"

    return "Pendiente"


def render_competition_list() -> None:
    """Muestra las competiciones guardadas como tarjetas de resultado."""
    competitions = get_competitions()

    if not competitions:
        st.info("Todavía no hay competiciones registradas.")
        return

    for index, competition in enumerate(competitions, start=1):
        comparison = compare_result_with_goal(
            competition["official_time_seconds"],
            competition["goal_time_seconds"],
        )

        if not comparison["available"]:
            status_label = "Sin resultado"
            status_tone = "neutral"
        elif comparison.get("achieved"):
            status_label = "Objetivo cumplido"
            status_tone = "success"
        else:
            status_label = "Objetivo pendiente"
            status_tone = "warning"

        distance_label = f"{competition['distance_km']:g} km"

        tags_html = "".join(
            [
                render_status_tag(status_label, status_tone),
                render_status_tag(distance_label, "neutral"),
            ]
        )

        badge_text = (
            seconds_to_time(competition["official_time_seconds"])
            if competition["official_time_seconds"] is not None
            else "Pendiente"
        )

        description_text = (
            competition["comments"] or "Sin comentarios sobre el circuito."
        )

        average_pace_text = (
            f"{seconds_to_time(competition['average_pace_seconds_per_km'])} min/km"
            if competition["average_pace_seconds_per_km"] is not None
            else "—"
        )

        average_heart_rate_text = (
            f"{competition['average_heart_rate']} ppm"
            if competition["average_heart_rate"] is not None
            else "—"
        )

        st.markdown(
            f"""
            <div class="qi-card">
                <div class="qi-card-header">
                    <div>
                        <div class="qi-card-title">
                            <span class="qi-rank">{index:02d}</span>
                            {html.escape(competition["name"])}
                        </div>
                        <div class="qi-card-subtitle">
                            {html.escape(competition["competition_date"])}
                        </div>
                    </div>
                    <span class="qi-match">{html.escape(badge_text)}</span>
                </div>
                <div class="qi-tags">{tags_html}</div>
                <div class="qi-description">
                    {html.escape(description_text)}
                </div>
                <div class="qi-metadata-grid">
                    <div>
                        <div class="qi-metadata-label">Objetivo</div>
                        <div class="qi-metadata-value">
                            {html.escape(
                                seconds_to_time(competition["goal_time_seconds"])
                            )}
                        </div>
                    </div>
                    <div>
                        <div class="qi-metadata-label">Tiempo oficial</div>
                        <div class="qi-metadata-value">
                            {html.escape(
                                seconds_to_time(
                                    competition["official_time_seconds"]
                                )
                            )}
                        </div>
                    </div>
                    <div>
                        <div class="qi-metadata-label">Ritmo medio</div>
                        <div class="qi-metadata-value">
                            {html.escape(average_pace_text)}
                        </div>
                    </div>
                    <div>
                        <div class="qi-metadata-label">FC media</div>
                        <div class="qi-metadata-value">
                            {html.escape(average_heart_rate_text)}
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if comparison["available"]:
            if comparison.get("achieved"):
                st.caption(f"✔ {comparison['message']}")
            else:
                st.caption(comparison["message"])
        else:
            st.caption(comparison["message"])



def render_result_form() -> None:
    """Muestra el formulario para registrar o corregir un resultado."""
    competitions = get_competitions()

    if not competitions:
        st.info("Añade primero una competición.")
        return

    competition_options = {
        competition["id"]: (
            f"{competition['competition_date']} · {competition['name']}"
        )
        for competition in competitions
    }

    selected_competition_id = st.selectbox(
        "Selecciona la competición",
        options=list(competition_options),
        format_func=lambda competition_id: competition_options[competition_id],
    )

    competition = get_competition_by_id(selected_competition_id)

    if competition is None:
        st.error("No se ha encontrado la competición seleccionada.")
        return

    default_time = seconds_to_time(competition["official_time_seconds"])
    if default_time == "—":
        default_time = ""

    with st.form("competition_result_form"):
        st.write(
            f"**{competition['name']}** · "
            f"{competition['distance_km']} km"
        )

        official_time = st.text_input(
            "Tiempo oficial *",
            value=default_time,
            placeholder="Ejemplo: 49:58",
        )

        average_heart_rate = st.text_input(
            "Frecuencia cardiaca media (ppm)",
            value=(
                str(competition["average_heart_rate"])
                if competition["average_heart_rate"] is not None
                else ""
            ),
            placeholder="Ejemplo: 172",
        )

        comments = st.text_area(
            "Comentarios sobre el circuito, sensaciones y estrategia",
            value=competition["comments"] or "",
        )

        submitted = st.form_submit_button(
            "Guardar resultado",
            type="primary",
        )

    if not submitted:
        return

    try:
        official_time_seconds = parse_race_time(official_time)
        average_pace_seconds = calculate_average_pace(
            official_time_seconds,
            float(competition["distance_km"]),
        )
        average_heart_rate_value = parse_optional_positive_integer(
            average_heart_rate,
            "Frecuencia cardiaca media",
        )

        update_competition_result(
            competition_id=selected_competition_id,
            official_time_seconds=official_time_seconds,
            average_pace_seconds_per_km=average_pace_seconds,
            average_heart_rate=average_heart_rate_value,
            comments=comments.strip() or None,
        )

        st.success(
            "Resultado guardado. El ritmo medio se ha calculado automáticamente."
        )
        st.rerun()

    except CompetitionValidationError as error:
        st.error(str(error))


def render_add_competition_form() -> None:
    """Muestra el formulario para añadir una competición."""
    with st.form("add_competition_form"):
        name = st.text_input(
            "Nombre de la competición *",
            placeholder="Ejemplo: Carrera de Navidad 2026",
        )
        competition_date = st.date_input(
            "Fecha *",
            value=date.today(),
        )
        distance_km = st.number_input(
            "Distancia (km) *",
            min_value=0.1,
            max_value=500.0,
            value=10.0,
            step=0.1,
        )
        goal_time = st.text_input(
            "Objetivo de tiempo",
            placeholder="Ejemplo: 49:59",
        )
        comments = st.text_area(
            "Comentarios del circuito u objetivo",
        )

        submitted = st.form_submit_button(
            "Añadir competición",
            type="primary",
        )

    if not submitted:
        return

    if not name.strip():
        st.error("El nombre de la competición es obligatorio.")
        return

    try:
        goal_time_seconds = (
            parse_race_time(goal_time)
            if goal_time.strip()
            else None
        )

        competition_id = create_competition(
            {
                "name": name.strip(),
                "competition_date": competition_date.isoformat(),
                "distance_km": distance_km,
                "goal_time_seconds": goal_time_seconds,
                "comments": comments.strip() or None,
            }
        )

        st.success(
            f"Competición añadida correctamente con identificador {competition_id}."
        )
        st.rerun()

    except CompetitionValidationError as error:
        st.error(str(error))
    except Exception:
        st.error(
            "No se pudo crear la competición. Comprueba que no existe "
            "otra con el mismo nombre y fecha."
        )


def render_derby_plan_proposal() -> None:
    """Permite crear una propuesta no automática tras el Derbi."""
    competitions = get_competitions()

    derby_competitions = [
        competition
        for competition in competitions
        if "derbi" in competition["name"].lower()
    ]

    if not derby_competitions:
        st.info("No se ha encontrado ninguna competición identificada como Derbi.")
        return

    derby = derby_competitions[0]

    if derby["official_time_seconds"] is None:
        st.info(
            "Registra el tiempo oficial del Derbi antes de crear una propuesta."
        )
        return

    st.write(
        f"Resultado usado: **{derby['name']} — "
        f"{seconds_to_time(derby['official_time_seconds'])}**"
    )

    user_notes = st.text_area(
        "Notas opcionales para esta versión del plan",
        placeholder=(
            "Ejemplo: la rodilla respondió bien, pero hubo fatiga por "
            "jiu-jitsu durante la semana."
        ),
    )

    if st.button("Generar propuesta posterior al Derbi", type="primary"):
        try:
            proposal = build_derby_plan_proposal(derby)
            proposal["notas_usuario"] = user_notes.strip() or None

            plan_version_id = create_plan_version(
                reason=f"Propuesta tras {derby['name']}",
                snapshot_json=json.dumps(
                    proposal,
                    ensure_ascii=False,
                ),
            )

            st.success(
                f"Se ha creado la propuesta de plan #{plan_version_id}. "
                "No se ha modificado ningún entrenamiento."
            )
            st.rerun()

        except CompetitionValidationError as error:
            st.error(str(error))


def render_plan_version_history() -> None:
    """Muestra el historial y permite aceptar o rechazar propuestas."""
    versions = get_plan_versions()

    if not versions:
        st.info("Todavía no hay propuestas de versiones del plan.")
        return

    for version in versions:
        status = get_plan_version_status(version["accepted"])

        with st.expander(
            f"Versión #{version['id']} · {status} · {version['created_at']}"
        ):
            st.write(f"**Motivo:** {version['reason']}")

            try:
                proposal = json.loads(version["snapshot_json"])
                st.write(
                    "**Objetivo propuesto para San Silvestre:** "
                    f"{proposal.get('proposed_san_silvestre_target', '—')}"
                )
                st.write(
                    f"**Confianza:** {proposal.get('confidence', '—')}"
                )
                st.write(
                    f"**Razonamiento:** {proposal.get('rationale', '—')}"
                )

                training_focus = proposal.get("training_focus", [])

                if training_focus:
                    st.write("**Foco propuesto:**")

                    for item in training_focus:
                        st.write(f"- {item}")

                if proposal.get("notas_usuario"):
                    st.write(
                        f"**Notas del usuario:** {proposal['notas_usuario']}"
                    )

            except json.JSONDecodeError:
                st.code(version["snapshot_json"])

            if status == "Pendiente":
                accept_column, reject_column = st.columns(2)

                with accept_column:
                    if st.button(
                        "Aceptar propuesta",
                        key=f"accept_version_{version['id']}",
                        type="primary",
                    ):
                        set_plan_version_decision(
                            version["id"],
                            "Aceptada",
                        )
                        st.rerun()

                with reject_column:
                    if st.button(
                        "Rechazar propuesta",
                        key=f"reject_version_{version['id']}",
                    ):
                        set_plan_version_decision(
                            version["id"],
                            "Rechazada",
                        )
                        st.rerun()


def render_competitions() -> None:
    """Renderiza todo el módulo de competiciones."""
    st.title("🏁 Competiciones")
    st.caption(
        "Los resultados alimentan el análisis, pero ninguna propuesta "
        "modifica automáticamente el plan."
    )

    tab_1, tab_2, tab_3, tab_4, tab_5 = st.tabs(
        [
            "Competiciones",
            "Registrar resultado",
            "Añadir competición",
            "Propuesta tras Derbi",
            "Historial de planes",
        ]
    )

    with tab_1:
        render_competition_list()

    with tab_2:
        render_result_form()

    with tab_3:
        render_add_competition_form()

    with tab_4:
        render_derby_plan_proposal()

    with tab_5:
        render_plan_version_history()

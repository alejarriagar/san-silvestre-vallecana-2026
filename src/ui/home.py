"""Landing operativa con calendario, detalle de sesión y entrenador local."""

from __future__ import annotations

import html
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import streamlit as st

from src.database import (
    delete_planned_training,
    get_activity_sessions_between,
    get_linked_planned_training,
    get_session_attachments,
    get_session_nutrition,
    get_training_plan,
    move_planned_training,
    update_planned_training,
)


from src.services.attachment_service import (
    delete_activity_session_with_attachments,
)

from src.services.analytics_service import calculate_dashboard_metrics
from src.services.safety_rules import evaluate_training_state
from src.services.session_evaluation_service import (
    evaluate_selected_session,
)
from src.ui.training_log import render_training_log
from src.ui.drag_calendar import render_drag_calendar
from src.ui.styles import render_hero, render_status_tag
from src.services.session_service import SessionValidationError
from src.ui.planner import build_training_payload, render_training_fields



DAY_NAMES = [
    "Lun",
    "Mar",
    "Mié",
    "Jue",
    "Vie",
    "Sáb",
    "Dom",
]


def format_value(value: Any, suffix: str = "") -> str:
    """Muestra valores opcionales de forma legible."""
    if value is None:
        return "—"

    return f"{value}{suffix}"


def format_pace(seconds: int | None) -> str:
    """Convierte segundos por km a formato M:SS."""
    if seconds is None:
        return "—"

    minutes, remaining_seconds = divmod(int(seconds), 60)

    return f"{minutes}:{remaining_seconds:02d} min/km"


def status_class(status: str) -> str:
    """Convierte un estado a una clase CSS visual."""
    return {
        "Pendiente": "pending",
        "Completado": "completed",
        "Modificado": "modified",
        "Cancelado": "cancelled",
    }.get(status, "pending")


def get_default_selected_date(
    trainings: list[dict[str, Any]],
) -> date:
    """Devuelve la primera sesión activa futura o el día actual."""
    today = date.today()

    future_dates = sorted(
        date.fromisoformat(training["planned_date"])
        for training in trainings
        if training["planned_date"] >= today.isoformat()
        and training["status"] != "Cancelado"
    )

    if future_dates:
        return future_dates[0]

    return today


def initialise_home_state(trainings: list[dict[str, Any]]) -> None:
    """Inicializa el estado de navegación de la landing."""
    default_date = get_default_selected_date(trainings)
    default_week_start = (
        default_date - timedelta(days=default_date.weekday())
    )

    if "home_selected_date" not in st.session_state:
        st.session_state["home_selected_date"] = default_date.isoformat()

    if "home_week_start" not in st.session_state:
        st.session_state["home_week_start"] = default_week_start.isoformat()

    if "home_selected_activity_id" not in st.session_state:
        st.session_state["home_selected_activity_id"] = None
    
    if "home_panel_open" not in st.session_state:
        st.session_state["home_panel_open"] = True



def group_by_date(
    records: list[dict[str, Any]],
    date_field: str,
) -> dict[str, list[dict[str, Any]]]:
    """Agrupa registros por fecha ISO."""
    grouped_records: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for record in records:
        grouped_records[record[date_field]].append(record)

    return grouped_records


def select_day(selected_day: date) -> None:
    """Guarda el día seleccionado en la sesión de Streamlit."""
    st.session_state["home_selected_date"] = selected_day.isoformat()
    st.session_state["home_selected_activity_id"] = None


def render_week_navigation() -> date:
    """Muestra controles de navegación de semana."""
    week_start = date.fromisoformat(
        st.session_state["home_week_start"]
    )

    previous_column, title_column, next_column = st.columns([1, 2, 1])

    with previous_column:
        if st.button(
            "Semana anterior",
            key="home_previous_week",
            use_container_width=True,
        ):
            new_week = week_start - timedelta(days=7)
            st.session_state["home_week_start"] = new_week.isoformat()
            select_day(new_week)
            st.rerun()

    with title_column:
        st.markdown(
            f"""
            <div style="text-align:center;">
                <strong>Semana del {week_start.strftime('%d/%m')}</strong><br>
                <span class="section-caption">
                    al {(week_start + timedelta(days=6)).strftime('%d/%m/%Y')}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "Ir a hoy",
            key="home_go_today",
            use_container_width=True,
        ):
            today = date.today()
            new_week = today - timedelta(days=today.weekday())
            st.session_state["home_week_start"] = new_week.isoformat()
            select_day(today)
            st.rerun()

    with next_column:
        if st.button(
            "Semana siguiente",
            key="home_next_week",
            use_container_width=True,
        ):
            new_week = week_start + timedelta(days=7)
            st.session_state["home_week_start"] = new_week.isoformat()
            select_day(new_week)
            st.rerun()

    return week_start


def render_week_calendar(
    plan_by_date: dict[str, list[dict[str, Any]]],
    activities_by_date: dict[str, list[dict[str, Any]]],
) -> None:
    """Muestra una semana clicable con sesiones previstas y realizadas."""
    week_start = render_week_navigation()
    today = date.today()

    st.subheader("Calendario")

    day_columns = st.columns(7)

    for index, column in enumerate(day_columns):
        current_day = week_start + timedelta(days=index)
        date_key = current_day.isoformat()
        planned_sessions = plan_by_date.get(date_key, [])
        completed_sessions = activities_by_date.get(date_key, [])
        is_selected = (
            st.session_state["home_selected_date"] == date_key
        )

        with column:
            column.caption(DAY_NAMES[index])

            label = str(current_day.day)

            if current_day == today:
                label = f"Hoy · {current_day.day}"

            if st.button(
                label,
                key=f"home_day_{date_key}",
                type="primary" if is_selected else "secondary",
                use_container_width=True,
            ):
                select_day(current_day)
                st.rerun()

            if planned_sessions:
                for training in planned_sessions:
                    css_class = status_class(training["status"])
                    session_type = html.escape(training["session_type"])

                    st.markdown(
                        f"""
                        <div class="calendar-session {css_class}">
                            <strong>Plan</strong><br>
                            {session_type}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            if completed_sessions:
                for activity in completed_sessions:
                    activity_type = html.escape(
                        activity["session_type"] or activity["sport"]
                    )

                    st.markdown(
                        f"""
                        <div class="calendar-session completed">
                            <strong>Registrado</strong><br>
                            {activity_type}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            if not planned_sessions and not completed_sessions:
                st.caption("Sin actividad")


def render_planned_training_detail(
    trainings: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Muestra los entrenamientos planificados para el día seleccionado."""
    if not trainings:
        st.info("No hay entrenamiento planificado para este día.")
        return None

    if len(trainings) == 1:
        training = trainings[0]
    else:
        training_ids = [training["id"] for training in trainings]

        selected_training_id = st.selectbox(
            "Entrenamiento planificado",
            options=training_ids,
            format_func=lambda training_id: next(
                training["session_type"]
                for training in trainings
                if training["id"] == training_id
            ),
            key="home_selected_training",
        )

        training = next(
            item
            for item in trainings
            if item["id"] == selected_training_id
        )

    status_tone = {
        "Pendiente": "warning",
        "Completado": "success",
        "Modificado": "warning",
        "Cancelado": "danger",
    }.get(training["status"], "neutral")

    tags_html = "".join(
        [
            render_status_tag(training["status"], status_tone),
            render_status_tag(training["sport"], "neutral"),
            render_status_tag(
                "Descarga",
                "neutral",
            )
            if training["is_deload"]
            else "",
        ]
    )

    rpe_badge = (
        f'{training["target_rpe"]}/10 RPE'
        if training["target_rpe"] is not None
        else "Sin RPE objetivo"
    )

    st.markdown(
        f"""
        <div class="qi-card">
            <div class="qi-card-header">
                <div>
                    <div class="qi-card-title">
                        {html.escape(training["session_type"])}
                    </div>
                    <div class="qi-card-subtitle">
                        Planificado · {html.escape(training["planned_date"])}
                    </div>
                </div>
                <span class="qi-match">{html.escape(rpe_badge)}</span>
            </div>
            <div class="qi-tags">{tags_html}</div>
            <div class="qi-description">
                {html.escape(training["description"])}
            </div>
            <div class="qi-metadata-grid">
                <div>
                    <div class="qi-metadata-label">Distancia</div>
                    <div class="qi-metadata-value">
                        {format_value(training["target_distance_km"], " km")}
                    </div>
                </div>
                <div>
                    <div class="qi-metadata-label">Duración</div>
                    <div class="qi-metadata-value">
                        {format_value(training["target_duration_min"], " min")}
                    </div>
                </div>
                <div>
                    <div class="qi-metadata-label">Terreno</div>
                    <div class="qi-metadata-value">
                        {html.escape(training["terrain"] or "—")}
                    </div>
                </div>
                <div>
                    <div class="qi-metadata-label">Ritmo</div>
                    <div class="qi-metadata-value">
                        {html.escape(training["target_pace"] or "—")}
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Ver planificación completa"):
        st.write(f"**Intensidad:** {training['target_intensity'] or '—'}")
        st.write(f"**Calentamiento:** {training['warmup'] or '—'}")
        st.write(f"**Parte principal:** {training['main_set'] or '—'}")
        st.write(f"**Vuelta a la calma:** {training['cooldown'] or '—'}")
        st.write(f"**Razonamiento:** {training['rationale'] or '—'}")

    st.divider()

    with st.expander("Mover este entrenamiento"):
        st.caption(
            "Mover una sesión cambia únicamente su fecha. "
            "No modifica la distancia, intensidad ni el contenido."
        )

        current_date = date.fromisoformat(
            training["planned_date"]
        )

        new_training_date = st.date_input(
            "Nueva fecha",
            value=current_date,
            key=f"home_move_date_{training['id']}",
        )

        if st.button(
            "Confirmar movimiento",
            key=f"home_move_button_{training['id']}",
            type="primary",
            use_container_width=True,
        ):
            if new_training_date == current_date:
                st.info(
                    "La sesión ya está planificada para esa fecha."
                )
            else:
                move_planned_training(
                    training_id=training["id"],
                    new_date=new_training_date,
                )
                st.success(
                    f"Sesión movida al {new_training_date.strftime('%d/%m/%Y')}."
                )
                st.rerun()

    return training



def render_activity_detail(
    activities: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Muestra el entrenamiento registrado, su nutrición y sus adjuntos."""
    if not activities:
        st.info("No hay entrenamiento registrado para este día.")
        return None

    activity_ids = [activity["id"] for activity in activities]
    selected_activity_id = st.session_state.get(
        "home_selected_activity_id"
    )

    if selected_activity_id not in activity_ids:
        selected_activity_id = activity_ids[0]

    if len(activities) > 1:
        selected_activity_id = st.selectbox(
            "Entrenamiento realizado",
            options=activity_ids,
            index=activity_ids.index(selected_activity_id),
            format_func=lambda activity_id: next(
                f"{activity['sport']} · {activity['session_type']}"
                for activity in activities
                if activity["id"] == activity_id
            ),
            key="home_selected_activity",
        )

    st.session_state["home_selected_activity_id"] = selected_activity_id

    activity = next(
        item
        for item in activities
        if item["id"] == selected_activity_id
    )

    rpe_badge = (
        f'{activity["rpe"]}/10 RPE'
        if activity["rpe"] is not None
        else "Sin RPE"
    )

    tags_html = "".join(
        [
            render_status_tag(activity["sport"], "neutral"),
            render_status_tag(
                activity["session_type"] or "Sin tipo",
                "neutral",
            ),
            render_status_tag(activity["source"], "neutral"),
        ]
    )

    description_text = activity["comments"] or "Sin comentarios registrados."

    st.markdown(
        f"""
        <div class="qi-card">
            <div class="qi-card-header">
                <div>
                    <div class="qi-card-title">
                        {html.escape(activity["sport"])} ·
                        {html.escape(activity["session_type"] or "")}
                    </div>
                    <div class="qi-card-subtitle">
                        Registrado · {html.escape(activity["session_date"])}
                    </div>
                </div>
                <span class="qi-match">{html.escape(rpe_badge)}</span>
            </div>
            <div class="qi-tags">{tags_html}</div>
            <div class="qi-description">
                {html.escape(description_text)}
            </div>
            <div class="qi-metadata-grid">
                <div>
                    <div class="qi-metadata-label">Distancia</div>
                    <div class="qi-metadata-value">
                        {format_value(activity["distance_km"], " km")}
                    </div>
                </div>
                <div>
                    <div class="qi-metadata-label">Duración</div>
                    <div class="qi-metadata-value">
                        {format_value(activity["duration_minutes"], " min")}
                    </div>
                </div>
                <div>
                    <div class="qi-metadata-label">Ritmo medio</div>
                    <div class="qi-metadata-value">
                        {format_pace(activity["average_pace_seconds_per_km"])}
                    </div>
                </div>
                <div>
                    <div class="qi-metadata-label">FC media</div>
                    <div class="qi-metadata-value">
                        {format_value(activity["average_heart_rate"], " ppm")}
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Ver dolor, sueño y comida previa"):
        st.write(
            f"**Dolor durante:** "
            f"{format_value(activity['pain_during'], '/10')}"
        )
        st.write(
            f"**Dolor después:** "
            f"{format_value(activity['pain_after'], '/10')}"
        )
        st.write(
            f"**Dolor al día siguiente:** "
            f"{format_value(activity['pain_next_day'], '/10')}"
        )
        st.write(
            f"**Desnivel positivo:** "
            f"{format_value(activity['elevation_gain_m'], ' m')}"
        )

        nutrition = get_session_nutrition(activity["id"])

        if nutrition:
            st.write(
                f"**Comida previa:** "
                f"{nutrition['pre_workout_food'] or '—'}"
            )
            st.write(
                f"**Tiempo antes:** "
                f"{nutrition['minutes_before'] or 0} minutos"
            )

    attachments = get_session_attachments(activity["id"])

    if attachments:
        st.subheader("Captura de actividad")

        for attachment in attachments:
            image_path = Path(attachment["stored_path"])

            if image_path.exists():
                st.image(
                    str(image_path),
                    caption=attachment["original_file_name"],
                    use_container_width=True,
                )
            else:
                st.warning(
                    "No se encuentra el archivo local del adjunto."
                )

    st.divider()

    with st.popover(
        "Eliminar registro",
        icon=":material/delete:",
    ):
        st.warning(
            "Esta acción elimina permanentemente el entrenamiento "
            "realizado y sus imágenes asociadas. No elimina la sesión "
            "planificada."
        )

        delete_confirmed = st.checkbox(
            "Confirmo que quiero eliminarlo.",
            key=f"home_delete_confirm_{activity['id']}",
        )

        if st.button(
            "Eliminar definitivamente",
            key=f"home_delete_button_{activity['id']}",
            disabled=not delete_confirmed,
            type="primary",
        ):
            delete_activity_session_with_attachments(
                activity["id"]
            )
            st.success("Registro eliminado correctamente.")
            st.rerun()


    return activity



def render_home() -> None:
    """Renderiza la landing principal de trabajo diario."""
    trainings = get_training_plan()
    initialise_home_state(trainings)

    today = date.today()
    metrics = calculate_dashboard_metrics(today)
    global_state = evaluate_training_state(
        metrics["sessions_last_28_days"],
        today,
    )

    selected_date = st.session_state["home_selected_date"]
    activities = get_activity_sessions_between(
        date(2000, 1, 1),
        today,
    )

    

    plan_by_date = group_by_date(trainings, "planned_date")
    activities_by_date = group_by_date(activities, "session_date")

    render_hero(
        eyebrow="Panel operativo de entrenamiento",
        title="Encuentra la señal detrás de cada sesión.",
        description=(
            "Consulta el plan, registra tu actividad y revisa la "
            "recomendación para la siguiente sesión."
        ),
    )


    metric_1, metric_2, metric_3, metric_4 = st.columns(4)

    metric_1.metric(
        "Km de carrera esta semana",
        f"{metrics['weekly_running_km']:.1f}",
    )
    metric_2.metric(
        "Carga semanal",
        f"{metrics['total_weekly_load']:.0f}",
    )
    metric_3.metric(
        "Km planificados esta semana",
        f"{metrics['planned_weekly_running_km']:.1f}",
    )
    metric_4.metric(
        "Estado general",
        global_state["estado"].upper(),
    )

    st.caption(
        "Carga estimada: duración en minutos × RPE. "
        "Solo se calcula cuando ambos datos están disponibles."
    )

    st.divider()



    st.divider()
    st.caption(f"Día seleccionado: {selected_date}")

    selected_plan = plan_by_date.get(selected_date, [])
    selected_activities = activities_by_date.get(selected_date, [])

    calendar_column, side_column = st.columns([2, 1])

    with calendar_column:
        render_drag_calendar(
            trainings=trainings,
            activities=activities,
        )

    with side_column:

        if not st.session_state.get("home_panel_open", True):
            planned_training = None
            activity = None
            st.info(
                "Panel cerrado. Haz clic en un entrenamiento del "
                "calendario para ver o editar su detalle."
            )
        else:
            st.subheader("Planificación del día")
            planned_training = render_planned_training_detail(selected_plan)


        if planned_training is not None:
            icon_col_1, icon_col_2 = st.columns(2)

            with icon_col_1:
                with st.popover(
                    "Editar",
                    icon=":material/edit:",
                    use_container_width=True,
                ):
                    with st.form(
                        f"home_edit_plan_form_{planned_training['id']}"
                    ):
                        edit_fields = render_training_fields(
                            f"home_edit_plan_{planned_training['id']}",
                            defaults=planned_training,
                        )
                        edit_submitted = st.form_submit_button(
                            "Guardar cambios",
                            type="primary",
                        )

                    if edit_submitted:
                        try:
                            updated_training = build_training_payload(
                                training_id=planned_training["id"],
                                **edit_fields,
                            )
                            update_planned_training(updated_training)
                            st.success(
                                "Entrenamiento actualizado correctamente."
                            )
                            st.rerun()
                        except SessionValidationError as error:
                            st.error(str(error))

            with icon_col_2:
                with st.popover(
                    "Eliminar",
                    icon=":material/delete:",
                    use_container_width=True,
                ):
                    st.warning(
                        "Esta acción elimina permanentemente la sesión "
                        "planificada. Si solo no vas a poder hacerla, "
                        "es preferible moverla de fecha o cancelarla."
                    )

                    confirm_delete_plan = st.checkbox(
                        "Confirmo que quiero eliminarla.",
                        key=(
                            f"home_delete_plan_confirm_"
                            f"{planned_training['id']}"
                        ),
                    )

                    if st.button(
                        "Eliminar definitivamente",
                        key=(
                            f"home_delete_plan_button_"
                            f"{planned_training['id']}"
                        ),
                        disabled=not confirm_delete_plan,
                        type="primary",
                    ):
                        delete_planned_training(planned_training["id"])
                        st.success("Sesión planificada eliminada.")
                        st.rerun()


        st.divider()
        st.subheader("Actividad realizada")
        activity = render_activity_detail(selected_activities)

        with st.expander(
            "Registrar entrenamiento",
            expanded=(len(selected_activities) == 0),
        ):
            render_training_log(show_title=False)


    st.divider()

    render_session_evaluation(

        activity=activity,
        planned_training=planned_training,
        global_state=global_state,
    )

    st.divider()
    st.subheader("Resumen de recuperación")

    st.write(
        f"**Confianza de la evaluación global:** "
        f"{global_state['confianza']:.0%}"
    )

    if global_state.get("preguntas_pendientes"):
        st.write("**Datos que ayudarían a mejorar la recomendación:**")

        for question in global_state["preguntas_pendientes"]:
            st.write(f"- {question}")

    st.warning(
        "Si aparecen hinchazón, bloqueo, inestabilidad o sensación de "
        "fallo en la rodilla, reduce carga y consulta a un profesional."
    )

    st.divider()


def render_session_evaluation(
    activity: dict[str, Any] | None,
    planned_training: dict[str, Any] | None,
    global_state: dict[str, Any],
) -> None:
    """Muestra la evaluación local del entrenador para el día seleccionado."""
    evaluation = evaluate_selected_session(
        activity_session=activity,
        planned_training=planned_training,
        global_state=global_state,
    )

    st.subheader("Evaluación del entrenador")

    if evaluation["estado"] == "verde":
        st.success(
            f"Estado: {evaluation['estado'].upper()}"
        )
    elif evaluation["estado"] == "amarillo":
        st.warning(
            f"Estado: {evaluation['estado'].upper()}"
        )
    else:
        st.error(
            f"Estado: {evaluation['estado'].upper()}"
        )

    st.write(evaluation["resumen"])
    st.write(
        f"**Decisión para la siguiente sesión:** "
        f"{evaluation['decision_siguiente']}"
    )
    st.write(
        f"**Recomendación:** {evaluation['recomendacion']}"
    )

    if global_state.get("alertas"):
        with st.expander("Alertas globales activas"):
            for alert in global_state["alertas"]:
                st.write(f"- {alert}")


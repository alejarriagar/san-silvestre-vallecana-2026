"""Landing operativa con calendario, detalle de sesión y entrenador local."""

from __future__ import annotations

import html
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import streamlit as st

from src.database import (
    get_activity_sessions_between,
    get_session_attachments,
    get_training_plan,
    get_session_nutrition,
    move_planned_training,
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

    css_class = status_class(training["status"])

    st.markdown(
        f"""
        <div class="planner-detail">
            <div class="status-badge status-{css_class}">
                {html.escape(training["status"])}
            </div>
            <h3>{html.escape(training["session_type"])}</h3>
            <p>{html.escape(training["description"])}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metric_1, metric_2, metric_3 = st.columns(3)

    metric_1.metric(
        "Distancia",
        format_value(training["target_distance_km"], " km"),
    )
    metric_2.metric(
        "Duración",
        format_value(training["target_duration_min"], " min"),
    )
    metric_3.metric(
        "RPE objetivo",
        format_value(training["target_rpe"], "/10"),
    )

    with st.expander("Ver planificación completa"):
        st.write(f"**Intensidad:** {training['target_intensity'] or '—'}")
        st.write(f"**Ritmo orientativo:** {training['target_pace'] or '—'}")
        st.write(f"**Terreno:** {training['terrain'] or '—'}")
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
    """Muestra el entrenamiento registrado y sus adjuntos."""
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

    with st.container(border=True):
        st.subheader(
            f"{activity['sport']} · {activity['session_type']}"
        )

        metric_1, metric_2, metric_3 = st.columns(3)

        metric_1.metric(
            "Distancia",
            format_value(activity["distance_km"], " km"),
        )
        metric_2.metric(
            "Duración",
            format_value(activity["duration_minutes"], " min"),
        )
        metric_3.metric(
            "RPE",
            format_value(activity["rpe"], "/10"),
        )

        st.write(
            f"**Ritmo medio:** "
            f"{format_pace(activity['average_pace_seconds_per_km'])}"
        )
        st.write(
            f"**FC media:** "
            f"{format_value(activity['average_heart_rate'], ' ppm')}"
        )
        st.write(
            f"**Desnivel positivo:** "
            f"{format_value(activity['elevation_gain_m'], ' m')}"
        )
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


        if activity["comments"]:
            st.write(f"**Comentarios:** {activity['comments']}")

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

    with st.expander("Eliminar este registro"):
        st.warning(
            "Esta acción elimina permanentemente el entrenamiento realizado "
            "y sus imágenes asociadas. No elimina la sesión planificada."
        )

        delete_confirmed = st.checkbox(
            "Confirmo que quiero eliminar este registro.",
            key=f"home_delete_confirm_{activity['id']}",
        )

        if st.button(
            "Eliminar registro",
            key=f"home_delete_button_{activity['id']}",
            disabled=not delete_confirmed,
            type="secondary",
        ):
            delete_activity_session_with_attachments(
                activity["id"]
            )
            st.success("Registro eliminado correctamente.")
            st.rerun()


    return activity


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

    st.title("Preparación San Silvestre Vallecana 2026")
    st.caption(
        "Consulta el plan, registra tu actividad y revisa la recomendación "
        "para la siguiente sesión."
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
    render_drag_calendar(
        trainings=trainings,
        activities=activities,
    )


    st.divider()
    st.caption(f"Día seleccionado: {selected_date}")

    selected_plan = plan_by_date.get(selected_date, [])
    selected_activities = activities_by_date.get(selected_date, [])

    detail_column, coach_column = st.columns([1.45, 1])

    with detail_column:
        st.subheader("Planificación del día")
        planned_training = render_planned_training_detail(selected_plan)

        st.divider()
        st.subheader("Actividad realizada")
        activity = render_activity_detail(selected_activities)

    with coach_column:
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

    with st.expander(
        "Registrar entrenamiento",
        expanded=False,
    ):
        render_training_log(show_title=False)



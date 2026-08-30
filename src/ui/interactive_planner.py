"""Planificador desktop interactivo con calendario semanal y mensual."""

from __future__ import annotations

import calendar
import html
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

import pandas as pd
import streamlit as st

from src.database import (
    TRAINING_STATUSES,
    get_training_plan,
    update_training_status,
)
from src.ui.planner import (
    SPORTS,
    filter_trainings,
    get_default_plan_date,
    render_cancel_training,
    render_create_training,
    render_duplicate_training,
    render_edit_training,
)

MONTHS_ES = [
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]

DAY_NAMES = [
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes",
    "Sábado",
    "Domingo",
]

DAY_SHORT_NAMES = [
    "Lun",
    "Mar",
    "Mié",
    "Jue",
    "Vie",
    "Sáb",
    "Dom",
]

STATUS_ICONS = {
    "Pendiente": "⏳",
    "Completado": "✅",
    "Modificado": "✏️",
    "Cancelado": "🚫",
}


def format_value(value: Any, suffix: str = "") -> str:
    """Muestra valores opcionales de forma legible."""
    if value is None:
        return "—"

    return f"{value}{suffix}"


def status_css_class(status: str) -> str:
    """Convierte un estado a una clase CSS segura."""
    return {
        "Pendiente": "pending",
        "Completado": "completed",
        "Modificado": "modified",
        "Cancelado": "cancelled",
    }.get(status, "pending")


def get_month_start(value: date) -> date:
    """Devuelve el primer día del mes de una fecha."""
    return value.replace(day=1)


def add_months(value: date, months: int) -> date:
    """Desplaza una fecha al primer día de otro mes."""
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1

    return date(year, month, 1)


def initialise_planner_state(trainings: list[dict[str, Any]]) -> None:
    """Inicializa las fechas seleccionadas para calendario y detalle."""
    default_date = get_default_plan_date(trainings)

    if "planner_selected_date" not in st.session_state:
        st.session_state["planner_selected_date"] = default_date.isoformat()

    if "planner_selected_training_id" not in st.session_state:
        st.session_state["planner_selected_training_id"] = None

    if "planner_week_start" not in st.session_state:
        week_start = default_date - timedelta(days=default_date.weekday())
        st.session_state["planner_week_start"] = week_start.isoformat()

    if "planner_month_start" not in st.session_state:
        st.session_state["planner_month_start"] = get_month_start(
            default_date
        ).isoformat()


def select_calendar_date(
    selected_date: date,
    training_id: int | None = None,
) -> None:
    """Actualiza el día y entrenamiento seleccionados."""
    st.session_state["planner_selected_date"] = selected_date.isoformat()
    st.session_state["planner_selected_training_id"] = training_id


def trainings_by_date(
    trainings: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Agrupa entrenamientos por fecha ISO."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for training in trainings:
        grouped[training["planned_date"]].append(training)

    return grouped


def render_session_mini_card(training: dict[str, Any]) -> None:
    """Muestra una tarjeta pequeña dentro de una celda de calendario."""
    status_class = status_css_class(training["status"])
    icon = STATUS_ICONS.get(training["status"], "•")
    session_type = html.escape(training["session_type"])
    description = html.escape(training["description"][:42])

    st.markdown(
        f"""
        <div class="calendar-session {status_class}">
            {icon} <strong>{session_type}</strong><br>
            {description}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_selected_session_detail(
    trainings: list[dict[str, Any]],
    panel_key: str,
) -> None:
    """Muestra el detalle de la sesión seleccionada en el calendario."""
    selected_date = st.session_state["planner_selected_date"]

    sessions_for_day = [
        training
        for training in trainings
        if training["planned_date"] == selected_date
    ]

    st.subheader("Entrenamiento seleccionado")

    if not sessions_for_day:
        st.info(
            f"No hay entrenamientos planificados el {selected_date}. "
            "Selecciona otro día con actividad."
        )
        return

    session_ids = [training["id"] for training in sessions_for_day]
    selected_training_id = st.session_state.get(
        "planner_selected_training_id"
    )

    if selected_training_id not in session_ids:
        selected_training_id = session_ids[0]
        st.session_state["planner_selected_training_id"] = selected_training_id

    if len(sessions_for_day) > 1:
        selected_training_id = st.selectbox(
            "Entrenamiento del día",
            options=session_ids,
            index=session_ids.index(selected_training_id),
            format_func=lambda training_id: next(
                training["session_type"]
                for training in sessions_for_day
                if training["id"] == training_id
            ),
            key=f"selected_training_{panel_key}_{selected_date}",
        )
        st.session_state["planner_selected_training_id"] = selected_training_id

    training = next(
        session
        for session in sessions_for_day
        if session["id"] == selected_training_id
    )

    status_class = status_css_class(training["status"])
    icon = STATUS_ICONS.get(training["status"], "•")

    st.markdown(
        f"""
        <div class="planner-detail">
            <div class="status-badge status-{status_class}">
                {icon} {html.escape(training["status"])}
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

    st.write(f"**Intensidad:** {training['target_intensity'] or '—'}")
    st.write(f"**Ritmo orientativo:** {training['target_pace'] or '—'}")
    st.write(f"**Terreno:** {training['terrain'] or '—'}")

    with st.expander("Ver estructura y razonamiento", expanded=True):
        st.write(f"**Calentamiento:** {training['warmup'] or '—'}")
        st.write(f"**Parte principal:** {training['main_set'] or '—'}")
        st.write(f"**Vuelta a la calma:** {training['cooldown'] or '—'}")
        st.write(f"**Razonamiento:** {training['rationale'] or '—'}")

    st.divider()
    st.write("**Cambiar estado de la sesión**")

    status = st.selectbox(
        "Estado",
        options=TRAINING_STATUSES,
        index=TRAINING_STATUSES.index(training["status"]),
        key=f"status_change_{panel_key}_{training['id']}",
    )

    if st.button(
        "Guardar estado",
        key=f"save_status_{panel_key}_{training['id']}",
        type="primary",
        use_container_width=True,
    ):
        update_training_status(training["id"], status)
        st.success("Estado actualizado correctamente.")
        st.rerun()


def render_week_navigation() -> date:
    """Muestra controles de navegación semanal y devuelve semana activa."""
    week_start = date.fromisoformat(
        st.session_state["planner_week_start"]
    )

    previous_column, current_column, next_column = st.columns([1, 2, 1])

    with previous_column:
        if st.button(
            "← Semana anterior",
            use_container_width=True,
        ):
            new_week_start = week_start - timedelta(days=7)
            st.session_state["planner_week_start"] = new_week_start.isoformat()
            select_calendar_date(new_week_start)
            st.rerun()

    with current_column:
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
            "Ir a la semana actual",
            key="go_to_current_week",
            use_container_width=True,
        ):
            today = date.today()
            new_week_start = today - timedelta(days=today.weekday())
            st.session_state["planner_week_start"] = new_week_start.isoformat()
            select_calendar_date(today)
            st.rerun()

    with next_column:
        if st.button(
            "Semana siguiente →",
            use_container_width=True,
        ):
            new_week_start = week_start + timedelta(days=7)
            st.session_state["planner_week_start"] = new_week_start.isoformat()
            select_calendar_date(new_week_start)
            st.rerun()

    return week_start


def render_weekly_calendar(trainings: list[dict[str, Any]]) -> None:
    """Muestra una semana clicable y el detalle de la sesión seleccionada."""
    week_start = render_week_navigation()
    grouped_trainings = trainings_by_date(trainings)
    today = date.today()

    calendar_column, detail_column = st.columns([1.7, 1])

    with calendar_column:
        st.subheader("Calendario semanal")

        day_columns = st.columns(7)

        for index, column in enumerate(day_columns):
            current_date = week_start + timedelta(days=index)
            date_key = current_date.isoformat()
            sessions = grouped_trainings.get(date_key, [])
            is_selected = (
                st.session_state["planner_selected_date"] == date_key
            )

            with column:
                column.caption(DAY_SHORT_NAMES[index])

                button_label = str(current_date.day)

                if current_date == today:
                    button_label = f"Hoy · {current_date.day}"

                if st.button(
                    button_label,
                    key=f"weekly_day_{date_key}",
                    type="primary" if is_selected else "secondary",
                    use_container_width=True,
                ):
                    select_calendar_date(current_date)
                    st.rerun()

                if not sessions:
                    st.caption("—")

                for training in sessions:
                    render_session_mini_card(training)

                    if st.button(
                        "Ver",
                        key=f"weekly_session_{training['id']}",
                        use_container_width=True,
                    ):
                        select_calendar_date(
                            current_date,
                            training["id"],
                        )
                        st.rerun()

    with detail_column:
        render_selected_session_detail(
        trainings,
        panel_key="weekly",
    )



def render_month_navigation() -> date:
    """Muestra navegación mensual y devuelve el mes activo."""
    month_start = date.fromisoformat(
        st.session_state["planner_month_start"]
    )

    previous_column, title_column, next_column = st.columns([1, 2, 1])

    with previous_column:
        if st.button(
            "← Mes anterior",
            use_container_width=True,
            key="previous_month",
        ):
            new_month = add_months(month_start, -1)
            st.session_state["planner_month_start"] = new_month.isoformat()
            st.rerun()

    with title_column:
        st.markdown(
            f"""
            <div style="text-align:center;">
                <strong>{MONTHS_ES[month_start.month - 1]} {month_start.year}</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with next_column:
        if st.button(
            "Mes siguiente →",
            use_container_width=True,
            key="next_month",
        ):
            new_month = add_months(month_start, 1)
            st.session_state["planner_month_start"] = new_month.isoformat()
            st.rerun()

    return month_start


def render_monthly_calendar(trainings: list[dict[str, Any]]) -> None:
    """Muestra un calendario mensual clicable con detalle lateral."""
    month_start = render_month_navigation()
    grouped_trainings = trainings_by_date(trainings)
    today = date.today()

    calendar_column, detail_column = st.columns([1.7, 1])

    with calendar_column:
        st.subheader("Calendario mensual")

        header_columns = st.columns(7)

        for column, day_name in zip(header_columns, DAY_SHORT_NAMES):
            column.markdown(f"**{day_name}**")

        weeks = calendar.monthcalendar(
            month_start.year,
            month_start.month,
        )

        for week in weeks:
            week_columns = st.columns(7)

            for column, day_number in zip(week_columns, week):
                if day_number == 0:
                    column.write("")
                    continue

                current_date = date(
                    month_start.year,
                    month_start.month,
                    day_number,
                )
                date_key = current_date.isoformat()
                sessions = grouped_trainings.get(date_key, [])
                is_selected = (
                    st.session_state["planner_selected_date"] == date_key
                )

                with column:
                    button_label = str(day_number)

                    if current_date == today:
                        button_label = f"Hoy · {day_number}"

                    if st.button(
                        button_label,
                        key=f"monthly_day_{date_key}",
                        type="primary" if is_selected else "secondary",
                        use_container_width=True,
                    ):
                        select_calendar_date(current_date)
                        st.rerun()

                    for training in sessions:
                        icon = STATUS_ICONS.get(
                            training["status"],
                            "•",
                        )
                        column.caption(
                            f"{icon} {training['session_type']}"
                        )

    with detail_column:
        render_selected_session_detail(
        trainings,
        panel_key="monthly",
    )



def render_upcoming_trainings(trainings: list[dict[str, Any]]) -> None:
    """Muestra próximas sesiones activas en forma de tabla."""
    today_iso = date.today().isoformat()

    upcoming = [
        training
        for training in trainings
        if training["planned_date"] >= today_iso
        and training["status"] != "Cancelado"
    ]

    if not upcoming:
        st.info("No hay entrenamientos futuros activos.")
        return

    rows = [
        {
            "Fecha": training["planned_date"],
            "Deporte": training["sport"],
            "Tipo": training["session_type"],
            "Descripción": training["description"],
            "Km": format_value(training["target_distance_km"]),
            "RPE": format_value(training["target_rpe"]),
            "Estado": training["status"],
        }
        for training in upcoming
    ]

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )


def render_summary_table(trainings: list[dict[str, Any]]) -> None:
    """Muestra una tabla expandible con todo el plan."""
    with st.expander("Ver resumen completo del plan"):
        rows = [
            {
                "Fecha": training["planned_date"],
                "Deporte": training["sport"],
                "Tipo": training["session_type"],
                "Descripción": training["description"],
                "Km objetivo": format_value(
                    training["target_distance_km"]
                ),
                "RPE": format_value(training["target_rpe"]),
                "Estado": training["status"],
                "Descarga": "Sí" if training["is_deload"] else "No",
            }
            for training in trainings
        ]

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )


def render_plan() -> None:
    """Renderiza el planificador desktop interactivo."""
    st.title("📅 Plan de entrenamiento")
    st.caption(
        "Selecciona un día del calendario para consultar el entrenamiento "
        "planificado y actualizar su estado."
    )

    trainings = get_training_plan()

    if not trainings:
        st.warning(
            "No hay entrenamientos planificados en la base de datos."
        )
        return

    initialise_planner_state(trainings)

    total_sessions = len(trainings)
    completed_sessions = sum(
        training["status"] == "Completado"
        for training in trainings
    )
    cancelled_sessions = sum(
        training["status"] == "Cancelado"
        for training in trainings
    )

    metric_1, metric_2, metric_3 = st.columns(3)
    metric_1.metric("Sesiones del plan", total_sessions)
    metric_2.metric("Completadas", completed_sessions)
    metric_3.metric("Canceladas", cancelled_sessions)

    st.divider()
    st.subheader("Filtros")

    filter_column_1, filter_column_2, filter_column_3 = st.columns(3)

    with filter_column_1:
        selected_sports = st.multiselect(
            "Deporte",
            options=SPORTS,
        )

    with filter_column_2:
        selected_types = st.multiselect(
            "Tipo de sesión",
            options=sorted(
                {
                    training["session_type"]
                    for training in trainings
                }
            ),
        )

    with filter_column_3:
        selected_statuses = st.multiselect(
            "Estado",
            options=TRAINING_STATUSES,
        )

    filtered_trainings = filter_trainings(
        trainings,
        selected_sports,
        selected_types,
        selected_statuses,
    )

    if not filtered_trainings:
        st.warning(
            "No hay sesiones que coincidan con los filtros seleccionados."
        )

    weekly_tab, monthly_tab, upcoming_tab, manage_tab = st.tabs(
        [
            "Vista semanal",
            "Calendario mensual",
            "Próximos entrenamientos",
            "Gestionar plan",
        ]
    )

    with weekly_tab:
        if filtered_trainings:
            render_weekly_calendar(filtered_trainings)

    with monthly_tab:
        if filtered_trainings:
            render_monthly_calendar(filtered_trainings)

    with upcoming_tab:
        if filtered_trainings:
            render_upcoming_trainings(filtered_trainings)

    with manage_tab:
        create_tab, edit_tab, duplicate_tab, cancel_tab = st.tabs(
            [
                "Crear",
                "Editar",
                "Duplicar",
                "Cancelar",
            ]
        )

        with create_tab:
            st.subheader("Crear entrenamiento")
            render_create_training()

        with edit_tab:
            st.subheader("Editar entrenamiento")
            render_edit_training(trainings)

        with duplicate_tab:
            st.subheader("Duplicar entrenamiento")
            render_duplicate_training(trainings)

        with cancel_tab:
            st.subheader("Cancelar entrenamiento")
            render_cancel_training(trainings)

    st.divider()
    render_summary_table(trainings)

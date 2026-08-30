"""Interfaz Streamlit para consultar y gestionar el plan de entrenamiento."""

from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

import pandas as pd
import streamlit as st

from src.database import (
    TRAINING_STATUSES,
    create_planned_training,
    get_planned_training_by_id,
    get_training_plan,
    update_planned_training,
    update_training_status,
)
from src.services.session_service import (
    SessionValidationError,
    optional_float,
)

SPORTS = [
    "Carrera",
    "Gimnasio",
    "Jiu-jitsu",
    "Bicicleta",
    "Descanso",
]

SESSION_TYPES = [
    "Rodaje fácil",
    "Tirada larga",
    "Cuestas",
    "Sprints o progresivos",
    "Intervalos",
    "Umbral",
    "Ritmo de competición",
    "Recuperación",
    "Competición",
    "Fuerza general",
    "Jiu-jitsu",
    "Bicicleta",
    "Descanso completo",
    "Otro",
]

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

STATUS_ICONS = {
    "Pendiente": "⏳",
    "Completado": "✅",
    "Modificado": "✏️",
    "Cancelado": "🚫",
}


def text_or_empty(value: Any) -> str:
    """Convierte valores opcionales de SQLite a texto editable."""
    return "" if value is None else str(value)


def format_value(value: Any, suffix: str = "") -> str:
    """Muestra valores opcionales sin convertir ceros en valores vacíos."""
    if value is None:
        return "—"

    return f"{value}{suffix}"


def get_default_plan_date(trainings: list[dict[str, Any]]) -> date:
    """Obtiene la primera sesión futura activa o la primera del plan."""
    today = date.today()

    future_dates = sorted(
        date.fromisoformat(training["planned_date"])
        for training in trainings
        if training["status"] != "Cancelado"
        and training["planned_date"] >= today.isoformat()
    )

    if future_dates:
        return future_dates[0]

    if trainings:
        return min(
            date.fromisoformat(training["planned_date"])
            for training in trainings
        )

    return today


def build_training_payload(
    *,
    training_id: int | None,
    planned_date: date,
    sport: str,
    session_type: str,
    description: str,
    target_distance_km: str,
    target_duration_min: str,
    target_intensity: str,
    target_rpe: str | int,
    target_pace: str,
    terrain: str,
    warmup: str,
    main_set: str,
    cooldown: str,
    rationale: str,
    status: str,
    is_deload: bool,
) -> dict[str, Any]:
    """Valida y prepara un entrenamiento para SQLite."""
    if not description.strip():
        raise SessionValidationError(
            "La descripción del entrenamiento es obligatoria."
        )

    parsed_rpe = None if target_rpe == "Sin dato" else int(target_rpe)

    if parsed_rpe is not None and not 1 <= parsed_rpe <= 10:
        raise SessionValidationError(
            "El RPE objetivo debe estar entre 1 y 10."
        )

    payload = {
        "planned_date": planned_date.isoformat(),
        "sport": sport,
        "session_type": session_type,
        "description": description.strip(),
        "target_distance_km": optional_float(
            target_distance_km,
            "Distancia objetivo",
        ),
        "target_duration_min": optional_float(
            target_duration_min,
            "Duración objetivo",
        ),
        "target_intensity": target_intensity.strip() or None,
        "target_rpe": parsed_rpe,
        "target_pace": target_pace.strip() or None,
        "terrain": terrain.strip() or None,
        "warmup": warmup.strip() or None,
        "main_set": main_set.strip() or None,
        "cooldown": cooldown.strip() or None,
        "rationale": rationale.strip() or None,
        "status": status,
        "is_deload": 1 if is_deload else 0,
    }

    if training_id is not None:
        payload["id"] = training_id

    return payload


def render_training_fields(
    prefix: str,
    defaults: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Renderiza los campos usados para crear y editar sesiones."""
    defaults = defaults or {}

    default_sport = defaults.get("sport", "Carrera")
    default_session_type = defaults.get("session_type", "Rodaje fácil")
    default_status = defaults.get("status", "Pendiente")

    if default_sport not in SPORTS:
        default_sport = "Carrera"

    if default_session_type not in SESSION_TYPES:
        default_session_type = "Otro"

    if default_status not in TRAINING_STATUSES:
        default_status = "Pendiente"

    default_date = defaults.get("planned_date")

    if isinstance(default_date, str):
        default_date = date.fromisoformat(default_date)

    if default_date is None:
        default_date = date.today()

    saved_rpe = defaults.get("target_rpe")

    if saved_rpe is None:
        saved_rpe = "Sin dato"
    else:
        saved_rpe = int(saved_rpe)

    rpe_options = ["Sin dato", *range(1, 11)]

    if saved_rpe not in rpe_options:
        saved_rpe = "Sin dato"

    left_column, right_column = st.columns(2)

    with left_column:
        planned_date = st.date_input(
            "Fecha *",
            value=default_date,
            key=f"{prefix}_date",
        )
        sport = st.selectbox(
            "Deporte *",
            options=SPORTS,
            index=SPORTS.index(default_sport),
            key=f"{prefix}_sport",
        )
        session_type = st.selectbox(
            "Tipo de sesión *",
            options=SESSION_TYPES,
            index=SESSION_TYPES.index(default_session_type),
            key=f"{prefix}_type",
        )
        target_distance_km = st.text_input(
            "Distancia objetivo (km)",
            value=text_or_empty(defaults.get("target_distance_km")),
            placeholder="Ejemplo: 8,5",
            key=f"{prefix}_distance",
        )
        target_duration_min = st.text_input(
            "Duración objetivo (minutos)",
            value=text_or_empty(defaults.get("target_duration_min")),
            placeholder="Ejemplo: 50",
            key=f"{prefix}_duration",
        )

    with right_column:
        target_rpe = st.selectbox(
            "RPE objetivo",
            options=rpe_options,
            index=rpe_options.index(saved_rpe),
            key=f"{prefix}_rpe",
        )
        target_intensity = st.text_input(
            "Intensidad objetivo",
            value=text_or_empty(defaults.get("target_intensity")),
            placeholder="Ejemplo: fácil y conversacional",
            key=f"{prefix}_intensity",
        )
        target_pace = st.text_input(
            "Ritmo orientativo",
            value=text_or_empty(defaults.get("target_pace")),
            placeholder="Ejemplo: sin ritmo rígido",
            key=f"{prefix}_pace",
        )
        terrain = st.text_input(
            "Terreno recomendado",
            value=text_or_empty(defaults.get("terrain")),
            placeholder="Ejemplo: pista o recorrido llano",
            key=f"{prefix}_terrain",
        )
        status = st.selectbox(
            "Estado",
            options=TRAINING_STATUSES,
            index=TRAINING_STATUSES.index(default_status),
            key=f"{prefix}_status",
        )
        is_deload = st.checkbox(
            "Semana o sesión de descarga",
            value=bool(defaults.get("is_deload", False)),
            key=f"{prefix}_deload",
        )

    description = st.text_area(
        "Descripción *",
        value=text_or_empty(defaults.get("description")),
        placeholder="Ejemplo: 8 km fáciles + 4 progresivos de 15 segundos.",
        key=f"{prefix}_description",
    )

    warmup = st.text_area(
        "Calentamiento",
        value=text_or_empty(defaults.get("warmup")),
        key=f"{prefix}_warmup",
    )

    main_set = st.text_area(
        "Parte principal",
        value=text_or_empty(defaults.get("main_set")),
        key=f"{prefix}_main_set",
    )

    cooldown = st.text_area(
        "Vuelta a la calma",
        value=text_or_empty(defaults.get("cooldown")),
        key=f"{prefix}_cooldown",
    )

    rationale = st.text_area(
        "Razonamiento del entrenamiento",
        value=text_or_empty(defaults.get("rationale")),
        key=f"{prefix}_rationale",
    )

    return {
        "planned_date": planned_date,
        "sport": sport,
        "session_type": session_type,
        "description": description,
        "target_distance_km": target_distance_km,
        "target_duration_min": target_duration_min,
        "target_intensity": target_intensity,
        "target_rpe": target_rpe,
        "target_pace": target_pace,
        "terrain": terrain,
        "warmup": warmup,
        "main_set": main_set,
        "cooldown": cooldown,
        "rationale": rationale,
        "status": status,
        "is_deload": is_deload,
    }


def filter_trainings(
    trainings: list[dict[str, Any]],
    sports: list[str],
    session_types: list[str],
    statuses: list[str],
) -> list[dict[str, Any]]:
    """Filtra entrenamientos según los criterios seleccionados."""
    return [
        training
        for training in trainings
        if (not sports or training["sport"] in sports)
        and (not session_types or training["session_type"] in session_types)
        and (not statuses or training["status"] in statuses)
    ]


def render_month_calendar(trainings: list[dict[str, Any]]) -> None:
    """Muestra las sesiones filtradas en una vista de calendario mensual."""
    default_date = get_default_plan_date(trainings)

    selected_year = st.number_input(
        "Año",
        min_value=2020,
        max_value=2100,
        value=default_date.year,
        step=1,
        key="calendar_year",
    )

    selected_month = st.selectbox(
        "Mes",
        options=list(range(1, 13)),
        index=default_date.month - 1,
        format_func=lambda month: MONTHS_ES[month - 1],
        key="calendar_month",
    )

    trainings_by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for training in trainings:
        trainings_by_date[training["planned_date"]].append(training)

    st.caption(
        f"Mostrando {MONTHS_ES[selected_month - 1]} de {selected_year}."
    )

    day_names = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    header_columns = st.columns(7)

    for column, day_name in zip(header_columns, day_names):
        column.markdown(f"**{day_name}**")

    for week in calendar.monthcalendar(int(selected_year), selected_month):
        week_columns = st.columns(7)

        for column, day_number in zip(week_columns, week):
            if day_number == 0:
                column.write("")
                continue

            current_date = date(
                int(selected_year),
                selected_month,
                day_number,
            )
            date_key = current_date.isoformat()

            column.markdown(f"**{day_number}**")

            for training in trainings_by_date.get(date_key, []):
                icon = STATUS_ICONS.get(training["status"], "•")
                column.caption(
                    f"{icon} {training['session_type']}"
                )
                column.caption(training["sport"])


def render_week_view(trainings: list[dict[str, Any]]) -> None:
    """Muestra el detalle de sesiones de una semana."""
    default_date = get_default_plan_date(trainings)

    selected_day = st.date_input(
        "Selecciona cualquier día de la semana",
        value=default_date,
        key="week_selected_date",
    )

    week_start = selected_day - timedelta(days=selected_day.weekday())
    week_end = week_start + timedelta(days=6)

    weekly_trainings = [
        training
        for training in trainings
        if week_start.isoformat()
        <= training["planned_date"]
        <= week_end.isoformat()
    ]

    st.caption(
        f"Semana del {week_start.strftime('%d/%m/%Y')} "
        f"al {week_end.strftime('%d/%m/%Y')}."
    )

    if not weekly_trainings:
        st.info("No hay entrenamientos planificados durante esta semana.")
        return

    for training in weekly_trainings:
        icon = STATUS_ICONS.get(training["status"], "•")

        with st.container(border=True):
            st.markdown(
                f"### {icon} {training['planned_date']} · "
                f"{training['session_type']}"
            )
            st.write(training["description"])

            left_column, right_column = st.columns(2)

            with left_column:
                st.write(f"**Deporte:** {training['sport']}")
                st.write(
                    "**Distancia objetivo:** "
                    f"{format_value(training['target_distance_km'], ' km')}"
                )
                st.write(
                    "**Duración objetivo:** "
                    f"{format_value(training['target_duration_min'], ' min')}"
                )
                st.write(
                    "**RPE objetivo:** "
                    f"{format_value(training['target_rpe'], '/10')}"
                )

            with right_column:
                st.write(f"**Estado:** {training['status']}")
                st.write(
                    f"**Terreno recomendado:** "
                    f"{training['terrain'] or '—'}"
                )
                st.write(
                    f"**Ritmo orientativo:** "
                    f"{training['target_pace'] or '—'}"
                )
                st.write(
                    "**Descarga:** "
                    f"{'Sí' if training['is_deload'] else 'No'}"
                )

            with st.expander("Ver estructura y razonamiento"):
                st.write(
                    f"**Calentamiento:** {training['warmup'] or '—'}"
                )
                st.write(
                    f"**Parte principal:** {training['main_set'] or '—'}"
                )
                st.write(
                    f"**Vuelta a la calma:** {training['cooldown'] or '—'}"
                )
                st.write(
                    f"**Razonamiento:** {training['rationale'] or '—'}"
                )


def render_upcoming_list(trainings: list[dict[str, Any]]) -> None:
    """Muestra una tabla de próximas sesiones activas."""
    today_iso = date.today().isoformat()

    upcoming_trainings = [
        training
        for training in trainings
        if training["planned_date"] >= today_iso
        and training["status"] != "Cancelado"
    ]

    if not upcoming_trainings:
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
        for training in upcoming_trainings
    ]

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )


def render_create_training() -> None:
    """Permite crear una nueva sesión planificada."""
    with st.form("create_planned_training_form"):
        fields = render_training_fields("create_training")

        submitted = st.form_submit_button(
            "Crear entrenamiento",
            type="primary",
        )

    if not submitted:
        return

    try:
        training = build_training_payload(
            training_id=None,
            **fields,
        )
        training_id = create_planned_training(training)

        st.success(
            f"Entrenamiento creado correctamente con identificador {training_id}."
        )
    except SessionValidationError as error:
        st.error(str(error))
    except Exception:
        st.error(
            "No se ha podido crear el entrenamiento. Puede existir ya "
            "una sesión idéntica en la misma fecha."
        )


def render_edit_training(trainings: list[dict[str, Any]]) -> None:
    """Permite editar un entrenamiento existente."""
    if not trainings:
        st.info("No hay entrenamientos para editar.")
        return

    options = {
        training["id"]: (
            f"{training['planned_date']} · "
            f"{training['session_type']} · "
            f"{training['description']}"
        )
        for training in trainings
    }

    selected_id = st.selectbox(
        "Selecciona el entrenamiento que quieres editar",
        options=list(options),
        format_func=lambda training_id: options[training_id],
        key="edit_training_selection",
    )

    training = get_planned_training_by_id(selected_id)

    if training is None:
        st.error("No se ha encontrado el entrenamiento seleccionado.")
        return

    with st.form(f"edit_training_form_{selected_id}"):
        fields = render_training_fields(
            f"edit_training_{selected_id}",
            defaults=training,
        )

        submitted = st.form_submit_button(
            "Guardar cambios",
            type="primary",
        )

    if not submitted:
        return

    try:
        updated_training = build_training_payload(
            training_id=selected_id,
            **fields,
        )
        update_planned_training(updated_training)

        st.success("Entrenamiento actualizado correctamente.")
        st.rerun()
    except SessionValidationError as error:
        st.error(str(error))
    except Exception:
        st.error(
            "No se ha podido actualizar el entrenamiento. Revisa los datos."
        )


def render_duplicate_training(trainings: list[dict[str, Any]]) -> None:
    """Permite duplicar una sesión en otra fecha."""
    if not trainings:
        st.info("No hay entrenamientos para duplicar.")
        return

    options = {
        training["id"]: (
            f"{training['planned_date']} · "
            f"{training['session_type']} · "
            f"{training['description']}"
        )
        for training in trainings
    }

    selected_id = st.selectbox(
        "Entrenamiento de origen",
        options=list(options),
        format_func=lambda training_id: options[training_id],
        key="duplicate_training_selection",
    )

    original_training = get_planned_training_by_id(selected_id)

    if original_training is None:
        st.error("No se ha encontrado el entrenamiento de origen.")
        return

    default_new_date = (
        date.fromisoformat(original_training["planned_date"])
        + timedelta(days=7)
    )

    with st.form(f"duplicate_training_form_{selected_id}"):
        new_date = st.date_input(
            "Nueva fecha",
            value=default_new_date,
        )
        new_description = st.text_area(
            "Descripción de la copia",
            value=original_training["description"],
        )
        submitted = st.form_submit_button(
            "Duplicar entrenamiento",
            type="primary",
        )

    if not submitted:
        return

    if not new_description.strip():
        st.error("La descripción no puede estar vacía.")
        return

    duplicate = {
        "planned_date": new_date.isoformat(),
        "sport": original_training["sport"],
        "session_type": original_training["session_type"],
        "description": new_description.strip(),
        "target_distance_km": original_training["target_distance_km"],
        "target_duration_min": original_training["target_duration_min"],
        "target_intensity": original_training["target_intensity"],
        "target_rpe": original_training["target_rpe"],
        "target_pace": original_training["target_pace"],
        "terrain": original_training["terrain"],
        "warmup": original_training["warmup"],
        "main_set": original_training["main_set"],
        "cooldown": original_training["cooldown"],
        "rationale": original_training["rationale"],
        "status": "Pendiente",
        "is_deload": original_training["is_deload"],
    }

    try:
        training_id = create_planned_training(duplicate)

        st.success(
            f"Entrenamiento duplicado correctamente con identificador {training_id}."
        )
        st.rerun()
    except Exception:
        st.error(
            "No se ha podido duplicar. Puede existir ya una sesión "
            "idéntica en la fecha elegida."
        )


def render_cancel_training(trainings: list[dict[str, Any]]) -> None:
    """Permite cancelar una sesión sin eliminarla del historial."""
    active_trainings = [
        training
        for training in trainings
        if training["status"] != "Cancelado"
    ]

    if not active_trainings:
        st.info("No hay entrenamientos activos para cancelar.")
        return

    options = {
        training["id"]: (
            f"{training['planned_date']} · "
            f"{training['session_type']} · "
            f"{training['description']}"
        )
        for training in active_trainings
    }

    selected_id = st.selectbox(
        "Selecciona el entrenamiento que quieres cancelar",
        options=list(options),
        format_func=lambda training_id: options[training_id],
        key="cancel_training_selection",
    )

    st.warning(
        "Cancelar una sesión no añade automáticamente carga a las sesiones posteriores."
    )

    if st.button(
        "Cancelar entrenamiento seleccionado",
        key="cancel_training_button",
    ):
        update_training_status(selected_id, "Cancelado")
        st.success(
            "Entrenamiento cancelado. La sesión se conserva en el historial."
        )
        st.rerun()


def render_plan() -> None:
    """Renderiza el módulo completo de planificación."""
    st.title("📅 Plan semanal y mensual")
    st.caption(
        "Los cambios manuales se guardan inmediatamente. "
        "Las propuestas futuras requerirán aceptación explícita."
    )

    trainings = get_training_plan()

    if not trainings:
        st.warning(
            "No hay entrenamientos planificados en la base de datos."
        )
        return

    st.success(
        f"Se han cargado {len(trainings)} entrenamientos planificados."
    )

    st.subheader("Resumen completo del plan")

    summary_rows = [
        {
            "Fecha": training["planned_date"],
            "Deporte": training["sport"],
            "Tipo": training["session_type"],
            "Descripción": training["description"],
            "Km objetivo": format_value(training["target_distance_km"]),
            "RPE": format_value(training["target_rpe"]),
            "Estado": training["status"],
            "Descarga": "Sí" if training["is_deload"] else "No",
        }
        for training in trainings
    ]

    st.dataframe(
        pd.DataFrame(summary_rows),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.subheader("Filtros")

    sport_filter = st.multiselect(
        "Filtrar por deporte",
        options=SPORTS,
    )

    session_type_filter = st.multiselect(
        "Filtrar por tipo de sesión",
        options=sorted(
            {
                training["session_type"]
                for training in trainings
            }
        ),
    )

    status_filter = st.multiselect(
        "Filtrar por estado",
        options=TRAINING_STATUSES,
    )

    filtered_trainings = filter_trainings(
        trainings,
        sport_filter,
        session_type_filter,
        status_filter,
    )

    if not filtered_trainings:
        st.warning(
            "No hay sesiones que coincidan con los filtros seleccionados."
        )

    calendar_tab, weekly_tab, upcoming_tab, manage_tab = st.tabs(
        [
            "Calendario mensual",
            "Vista semanal",
            "Próximos entrenamientos",
            "Gestionar plan",
        ]
    )

    with calendar_tab:
        if filtered_trainings:
            render_month_calendar(filtered_trainings)

    with weekly_tab:
        if filtered_trainings:
            render_week_view(filtered_trainings)

    with upcoming_tab:
        if filtered_trainings:
            render_upcoming_list(filtered_trainings)

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

"""Interfaz Streamlit para importar sesiones desde CSV y Excel."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.database import (
    create_activity_sessions,
    get_activity_sessions_for_duplicate_detection,
)
from src.services.import_service import (
    ImportValidationError,
    read_uploaded_dataframe,
    suggest_column_mapping,
    validate_import_dataframe,
)

NO_COLUMN = "— Sin asignar —"

MAPPING_FIELDS = [
    ("session_date", "Fecha *"),
    ("sport", "Deporte"),
    ("session_type", "Tipo de sesión"),
    ("duration_minutes", "Duración"),
    ("distance_km", "Distancia"),
    ("average_pace", "Ritmo medio"),
    ("average_heart_rate", "Frecuencia cardiaca media"),
    ("max_heart_rate", "Frecuencia cardiaca máxima"),
    ("elevation_gain_m", "Desnivel positivo"),
    ("rpe", "RPE"),
    ("surface", "Superficie"),
    ("shoes", "Zapatillas"),
    ("pain_during", "Dolor durante"),
    ("pain_after", "Dolor después"),
    ("pain_next_day", "Dolor al día siguiente"),
    ("sleep_hours", "Horas de sueño"),
    ("fatigue", "Fatiga"),
    ("comments", "Comentarios"),
]

SOURCE_OPTIONS = [
    "CSV",
    "Excel",
    "Garmin",
    "Strava",
    "Otro",
]

DEFAULT_SPORT_OPTIONS = [
    "Carrera",
    "Gimnasio",
    "Jiu-jitsu",
    "Bicicleta",
    "Descanso",
]


def get_default_source(file_name: str) -> str:
    """Obtiene el origen inicial a partir de la extensión del archivo."""
    suffix = Path(file_name).suffix.lower()

    if suffix == ".csv":
        return "CSV"

    return "Excel"


def render_import_data() -> None:
    """Renderiza el asistente de importación de datos."""
    st.title("📥 Importar datos")
    st.caption(
        "Puedes subir archivos CSV o Excel. Revisa y valida los datos "
        "antes de guardarlos en la aplicación."
    )

    st.info(
        "No existe todavía conexión directa con Garmin o Strava. "
        "Puedes exportar un archivo desde esas plataformas y seleccionar "
        "su origen durante la importación."
    )

    uploaded_file = st.file_uploader(
        "Selecciona un archivo CSV o Excel",
        type=["csv", "xlsx", "xls"],
    )

    if uploaded_file is None:
        st.markdown(
            """
            **Columnas habituales reconocidas automáticamente:**

            - Fecha / Date
            - Deporte / Sport / Activity Type
            - Distancia / Distance
            - Duración / Duration / Elapsed Time
            - Ritmo / Pace
            - Frecuencia cardiaca / Heart Rate
            - RPE, dolor, sueño y fatiga
            """
        )
        return

    try:
        dataframe = read_uploaded_dataframe(uploaded_file)
    except ImportValidationError as error:
        st.error(str(error))
        return

    if dataframe.empty:
        st.error("El archivo no contiene filas para importar.")
        return

    dataframe.columns = [str(column) for column in dataframe.columns]

    st.subheader("Previsualización del archivo")
    st.write(
        f"Archivo: **{uploaded_file.name}** · "
        f"{len(dataframe)} filas · {len(dataframe.columns)} columnas"
    )
    st.dataframe(dataframe.head(20), use_container_width=True)

    suggestions = suggest_column_mapping(list(dataframe.columns))
    options = [NO_COLUMN, *dataframe.columns]

    st.subheader("Asignación de columnas")
    st.caption(
        "La fecha es obligatoria. Los demás campos pueden dejarse sin asignar."
    )

    mapping: dict[str, str | None] = {}

    mapping_left, mapping_right = st.columns(2)

    for index, (field_name, field_label) in enumerate(MAPPING_FIELDS):
        suggested_column = suggestions.get(field_name)
        default_index = (
            options.index(suggested_column)
            if suggested_column in options
            else 0
        )

        target_column = (
            mapping_left
            if index % 2 == 0
            else mapping_right
        )

        with target_column:
            selected_column = st.selectbox(
                field_label,
                options=options,
                index=default_index,
                key=f"mapping_{uploaded_file.name}_{field_name}",
            )

        mapping[field_name] = (
            None if selected_column == NO_COLUMN else selected_column
        )

    st.subheader("Origen y valores por defecto")

    default_source = get_default_source(uploaded_file.name)
    source = st.selectbox(
        "Origen que se guardará",
        options=SOURCE_OPTIONS,
        index=SOURCE_OPTIONS.index(default_source),
    )

    default_sport = st.selectbox(
        "Deporte por defecto si no existe columna de deporte",
        options=DEFAULT_SPORT_OPTIONS,
    )

    validation_key = (
        uploaded_file.name,
        tuple(sorted(mapping.items())),
        source,
        default_sport,
    )

    if mapping["session_date"] is None:
        st.error("Asigna una columna de fecha para poder validar el archivo.")
        return

    if st.button("Validar archivo", type="primary"):
        try:
            valid_sessions, errors = validate_import_dataframe(
                dataframe=dataframe,
                mapping=mapping,
                source=source,
                default_sport=default_sport,
                existing_sessions=get_activity_sessions_for_duplicate_detection(),
            )

            st.session_state["import_validation_key"] = validation_key
            st.session_state["valid_import_sessions"] = valid_sessions
            st.session_state["import_errors"] = errors

        except ImportValidationError as error:
            st.error(str(error))

    is_current_validation = (
        st.session_state.get("import_validation_key") == validation_key
    )

    if not is_current_validation:
        st.caption(
            "Selecciona las columnas necesarias y pulsa «Validar archivo»."
        )
        return

    valid_sessions = st.session_state.get("valid_import_sessions", [])
    errors = st.session_state.get("import_errors", [])

    st.divider()
    st.subheader("Resultado de la validación")

    metric_1, metric_2 = st.columns(2)
    metric_1.metric("Sesiones listas para importar", len(valid_sessions))
    metric_2.metric("Filas con errores o duplicadas", len(errors))

    if errors:
        st.warning(
            "Las filas con errores no se importarán. Corrige el archivo "
            "o revisa la asignación de columnas si es necesario."
        )
        st.dataframe(
            pd.DataFrame(errors),
            use_container_width=True,
            hide_index=True,
        )

    if valid_sessions:
        st.success(
            f"{len(valid_sessions)} sesiones válidas listas para importar."
        )

        preview_columns = [
            "session_date",
            "sport",
            "session_type",
            "duration_minutes",
            "distance_km",
            "average_pace_seconds_per_km",
            "rpe",
            "source",
        ]

        st.dataframe(
            pd.DataFrame(valid_sessions)[preview_columns],
            use_container_width=True,
            hide_index=True,
        )

        if st.button(
            f"Importar {len(valid_sessions)} sesiones",
            type="primary",
        ):
            imported_count = create_activity_sessions(valid_sessions)

            for session_state_key in [
                "import_validation_key",
                "valid_import_sessions",
                "import_errors",
            ]:
                st.session_state.pop(session_state_key, None)

            st.success(
                f"Se han importado correctamente {imported_count} sesiones."
            )
            st.rerun()
    else:
        st.error(
            "No hay filas válidas para importar. Revisa los errores mostrados."
        )

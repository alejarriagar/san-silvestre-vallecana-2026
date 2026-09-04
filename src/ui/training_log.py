"""Interfaz Streamlit para registrar entrenamientos realizados."""

from __future__ import annotations

from datetime import date
from pathlib import Path


import pandas as pd
import streamlit as st

from src.database import (
    create_activity_session,
    get_linked_planned_training,
    get_recent_activity_sessions,
    get_session_attachments,
    get_training_plan,
    save_activity_plan_link,
    save_session_nutrition,
)




from src.services.session_service import (
    SessionValidationError,
    build_activity_session,
    optional_nonnegative_integer,
)

from src.services.attachment_service import (
    AttachmentValidationError,
    delete_activity_session_with_attachments,
    save_uploaded_session_attachment,
)







SPORTS = [
    "Carrera",
    "Gimnasio",
    "Jiu-jitsu",
    "Bicicleta",
    "Descanso",
]

SESSION_TYPES_BY_SPORT = {
    "Carrera": [
        "Rodaje fácil",
        "Tirada larga",
        "Cuestas",
        "Sprints o progresivos",
        "Intervalos",
        "Umbral",
        "Ritmo de competición",
        "Recuperación",
        "Competición",
        "Otro",
    ],
    "Gimnasio": [
        "Fuerza general",
        "Fuerza de tren inferior",
        "Fuerza de tren superior",
        "Movilidad",
        "Otro",
    ],
    "Jiu-jitsu": [
        "Técnica",
        "Sparring",
        "Técnica y sparring",
        "Competición",
        "Otro",
    ],
    "Bicicleta": [
        "Rodaje suave",
        "Rodaje largo",
        "Intervalos",
        "Recuperación",
        "Otro",
    ],
    "Descanso": [
        "Descanso completo",
        "Recuperación activa",
    ],
}

SURFACES = [
    "Sin dato",
    "Asfalto",
    "Pista de atletismo",
    "Tierra",
    "Sendero",
    "Cinta",
    "Bicicleta estática",
    "Gimnasio",
    "Tatami",
    "Otro",
]

FATIGUE_LEVELS = [
    "Sin dato",
    "Muy baja",
    "Baja",
    "Media",
    "Alta",
    "Muy alta",
]


def pace_to_text(seconds: int | None) -> str:
    """Muestra un ritmo almacenado como segundos en formato MM:SS."""
    if seconds is None:
        return "—"

    minutes, remaining_seconds = divmod(seconds, 60)
    return f"{minutes}:{remaining_seconds:02d} min/km"


def render_training_log(show_title: bool = True) -> None:

    """Renderiza el formulario de registro y las últimas sesiones."""
    if show_title:
        st.title("Registrar entrenamiento")
    else:
        st.subheader("Registrar entrenamiento")

    st.caption(

        "Los campos sin datos conocidos pueden dejarse vacíos. "
        "La carga se calculará posteriormente como duración × RPE."
    )

    planned_training_options = {
        "Sin vincular": None,
    }

    for planned_training in get_training_plan():
        label = (
            f"{planned_training['planned_date']} · "
            f"{planned_training['session_type']} · "
            f"{planned_training['description']}"
        )
        planned_training_options[label] = planned_training["id"]
    
    


    with st.form("activity_session_form"):
        selected_planned_training_label = st.selectbox(
            "Sesión planificada relacionada",
            options=list(planned_training_options),
            help=(
                "Selecciona la sesión del plan que corresponde a este "
                "entrenamiento. Puedes dejarlo sin vincular."
            ),
        )

        planned_training_id = planned_training_options[
            selected_planned_training_label
        ]

        first_column, second_column = st.columns(2)

        with first_column:
            session_date = st.date_input(
                "Fecha *",
                value=date.today(),
            )
            sport = st.selectbox("Deporte *", options=SPORTS)
            session_type = st.selectbox(
                "Tipo de sesión *",
                options=SESSION_TYPES_BY_SPORT[sport],
            )
            duration_minutes = st.text_input(
            "Duración",
            placeholder="Ejemplo: 45:23 o 1:45:23",
            help=(
                "Formatos admitidos: 45 minutos, 45:23 minutos y segundos, "
                "o 1:45:23 horas, minutos y segundos."
            ),
        )

            distance_km = st.text_input(
                "Distancia (km)",
                placeholder="Ejemplo: 6,5",
            )
            average_pace = st.text_input(
                "Ritmo medio (MM:SS min/km)",
                placeholder="Ejemplo: 5:45",
            )
            elevation_gain_m = st.text_input(
                "Desnivel positivo (m)",
                placeholder="Ejemplo: 120",
            )

        with second_column:
            average_heart_rate = st.text_input(
                "Frecuencia cardiaca media (ppm)",
                placeholder="Ejemplo: 158",
            )
            max_heart_rate = st.text_input(
                "Frecuencia cardiaca máxima (ppm)",
                placeholder="Ejemplo: 177",
            )
            rpe = st.selectbox(
                "RPE (1-10)",
                options=["Sin dato", *range(1, 11)],
            )
            surface = st.selectbox("Superficie", options=SURFACES)
            shoes = st.text_input(
                "Zapatillas utilizadas",
                placeholder="Ejemplo: ASICS MetaRide 2020",
            )
            sleep_hours = st.text_input(
                "Horas de sueño previas",
                placeholder="Ejemplo: 7,5",
            )
            fatigue = st.selectbox("Sensación de fatiga", options=FATIGUE_LEVELS)

        st.subheader("Dolor de rodilla (0-10)")

        pain_column_1, pain_column_2, pain_column_3 = st.columns(3)

        with pain_column_1:
            pain_during = st.selectbox(
                "Durante la sesión",
                options=["Sin dato", *range(0, 11)],
            )

        with pain_column_2:
            pain_after = st.selectbox(
                "Inmediatamente después",
                options=["Sin dato", *range(0, 11)],
            )

        with pain_column_3:
            pain_next_day = st.selectbox(
                "Al día siguiente",
                options=["Sin dato", *range(0, 11)],
            )
        
        st.subheader("Comida previa al entrenamiento")

        pre_workout_food = st.text_area(
            "Qué comiste antes",
            placeholder=(
                "Ejemplo: plátano y bebida con carbohidratos; "
                "café; tostada..."
            ),
            help=(
                "Este dato permitirá estudiar en el futuro qué estrategia "
                "nutricional se asocia con mejores sensaciones."
            ),
        )

        pre_workout_minutes = st.text_input(
            "Cuántos minutos antes",
            placeholder="Ejemplo: 30",
            help="Puedes introducir 0 si comiste justo antes de entrenar.",
        )

        st.subheader("Captura opcional de actividad")

        strava_image = st.file_uploader(
            "Adjuntar captura de Strava o gráfico de entrenamiento",
            type=["png", "jpg", "jpeg", "webp"],
            help=(
                "La imagen se almacena solo en este ordenador. "
                "No se sube a GitHub ni a servicios externos."
            ),
        )        

        comments = st.text_area(
            "Comentarios",
            placeholder=(
                "Ejemplo: rodaje con calor, buenas sensaciones, "
                "molestia leve al terminar..."
            ),
        )

        submitted = st.form_submit_button(
            "Guardar entrenamiento",
            type="primary",
        )

    if submitted:
        try:
            parsed_pre_workout_minutes = optional_nonnegative_integer(
                pre_workout_minutes,
                "Minutos antes",
            )
            
            session = build_activity_session(
                session_date=session_date,
                sport=sport,
                session_type=session_type,
                duration_minutes=duration_minutes,
                distance_km=distance_km,
                average_pace=average_pace,
                average_heart_rate=average_heart_rate,
                max_heart_rate=max_heart_rate,
                elevation_gain_m=elevation_gain_m,
                rpe=rpe,
                surface=surface,
                shoes=shoes,
                pain_during=pain_during,
                pain_after=pain_after,
                pain_next_day=pain_next_day,
                sleep_hours=sleep_hours,
                fatigue=fatigue,
                comments=comments,
            )
            session_id = create_activity_session(session)

            save_activity_plan_link(
                activity_session_id=session_id,
                planned_training_id=planned_training_id,
            )

            save_session_nutrition(
                session_id=session_id,
                pre_workout_food=pre_workout_food.strip() or None,
                minutes_before=parsed_pre_workout_minutes,
            )
   


            if strava_image is not None:
                try:
                    save_uploaded_session_attachment(
                        session_id,
                        strava_image,
                    )
                except AttachmentValidationError as error:
                    st.warning(
                        "El entrenamiento se ha guardado, pero no se pudo adjuntar "
                        f"la imagen: {error}"
                    )

            st.success("Entrenamiento guardado correctamente.")
            st.info(
                "El plan no se marca como completado automáticamente. "
                "Puedes actualizar su estado desde «Plan semanal y mensual»."
            )
        except SessionValidationError as error:
            st.error(str(error))

    st.divider()
    st.subheader("Últimos entrenamientos registrados")

    recent_sessions = get_recent_activity_sessions()

    if not recent_sessions:
        st.info("Todavía no hay entrenamientos registrados.")
        return

    rows = []

    for session in recent_sessions:
        related_training = get_linked_planned_training(
            session["id"]
        )

        rows.append(
            {
                "Fecha": session["session_date"],
                "Deporte": session["sport"],
                "Tipo": session["session_type"],
                "Plan relacionado": (
                    related_training["session_type"]
                    if related_training
                    else "Sin vincular"
                ),
                "Duración (min)": (
                    session["duration_minutes"]
                    if session["duration_minutes"] is not None
                    else "—"
                ),
                "Distancia (km)": (
                    session["distance_km"]
                    if session["distance_km"] is not None
                    else "—"
                ),
                "Ritmo": pace_to_text(
                    session["average_pace_seconds_per_km"]
                ),
                "RPE": (
                    session["rpe"]
                    if session["rpe"] is not None
                    else "—"
                ),
                "Dolor después": (
                    session["pain_after"]
                    if session["pain_after"] is not None
                    else "—"
                ),
                "Origen": session["source"],
            }
        )


    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
        

    st.subheader("Capturas de entrenamientos")

    session_options = {
        session["id"]: (
            f"{session['session_date']} · "
            f"{session['sport']} · "
            f"{session['session_type']}"
        )
        for session in recent_sessions
    }

    selected_session_id = st.selectbox(
        "Selecciona una sesión para ver sus adjuntos",
        options=list(session_options),
        format_func=lambda session_id: session_options[session_id],
    )

    attachments = get_session_attachments(selected_session_id)

    if not attachments:
        st.info("Esta sesión no tiene capturas adjuntas.")
    else:
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
                    "No se encuentra el archivo local de este adjunto."
                )
    st.divider()
    st.subheader("Eliminar registro realizado")

    st.warning(
        "Esta acción elimina permanentemente el entrenamiento registrado "
        "y sus capturas adjuntas locales. No elimina el entrenamiento "
        "planificado."
    )

    delete_session_options = {
        session["id"]: (
            f"{session['session_date']} · "
            f"{session['sport']} · "
            f"{session['session_type']}"
        )
        for session in recent_sessions
    }

    selected_session_to_delete = st.selectbox(
        "Selecciona el registro que quieres eliminar",
        options=list(delete_session_options),
        format_func=lambda session_id: delete_session_options[session_id],
        key="delete_activity_session_selector",
    )

    deletion_confirmed = st.checkbox(
        "Entiendo que esta acción no se puede deshacer.",
        key="delete_activity_session_confirm",
    )

    if st.button(
        "Eliminar registro seleccionado",
        key="delete_activity_session_button",
        disabled=not deletion_confirmed,
    ):
        try:
            deleted_files = delete_activity_session_with_attachments(
                selected_session_to_delete
            )

            st.success(
                "Registro eliminado correctamente. "
                f"Capturas eliminadas: {deleted_files}."
            )
            st.rerun()
        except ValueError as error:
            st.error(str(error))


def optional_nonnegative_integer(
    value: str,
    field_name: str,
) -> int | None:
    """Convierte un entero opcional que puede ser cero."""
    cleaned_value = value.strip()

    if not cleaned_value:
        return None

    try:
        converted_value = int(cleaned_value)
    except ValueError as error:
        raise SessionValidationError(
            f"El campo «{field_name}» debe ser un número entero."
        ) from error

    if converted_value < 0:
        raise SessionValidationError(
            f"El campo «{field_name}» no puede ser negativo."
        )

    return converted_value




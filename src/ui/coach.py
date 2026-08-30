"""Interfaz Streamlit para el entrenador deportivo en modo demo o LLM."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import streamlit as st

from src.database import (
    create_plan_version,
    get_coach_analysis_history,
    get_latest_coach_analysis,
    get_plan_versions,
    save_coach_analysis,
    set_plan_version_decision,
)
from src.services.coach_service import generate_coach_analysis
from src.services.llm_service import (
    CoachAnalysis,
    LLMServiceError,
    load_provider_configuration,
)


def get_plan_version_status(accepted_value: int) -> str:
    """Convierte el valor interno de una propuesta a texto legible."""
    if accepted_value == 1:
        return "Aceptada"

    if accepted_value == -1:
        return "Rechazada"

    return "Pendiente"


def get_analysis_from_row(row: dict[str, Any]) -> CoachAnalysis | None:
    """Convierte el JSON de SQLite a un análisis validado."""
    try:
        return CoachAnalysis.model_validate_json(row["analysis_json"])
    except Exception:
        return None


def render_state_banner(analysis: CoachAnalysis) -> None:
    """Muestra el estado verde, amarillo o rojo del entrenador."""
    message = (
        f"Estado general: **{analysis.estado.upper()}** · "
        f"Confianza del análisis: **{analysis.confianza:.0%}**"
    )

    if analysis.estado == "verde":
        st.success(message)
    elif analysis.estado == "amarillo":
        st.warning(message)
    else:
        st.error(message)


def render_list(title: str, values: list[str]) -> None:
    """Muestra una lista de textos cuando existen datos."""
    st.markdown(f"#### {title}")

    if not values:
        st.caption("Sin elementos disponibles.")
        return

    for value in values:
        st.write(f"- {value}")


def render_coach_analysis(
    analysis: CoachAnalysis,
    compact: bool = False,
) -> None:
    """Renderiza el contenido de un análisis estructurado."""
    render_state_banner(analysis)

    st.markdown("#### Resumen")
    st.write(analysis.resumen)

    if compact:
        left_column, right_column = st.columns(2)

        with left_column:
            render_list("Qué se ha hecho bien", analysis.logros)

        with right_column:
            render_list("Alertas importantes", analysis.alertas)

        render_list("Recomendación para la próxima semana", analysis.recomendaciones)
        return

    first_column, second_column = st.columns(2)

    with first_column:
        render_list("Qué se ha hecho bien", analysis.logros)
        render_list(
            "Recomendación para la próxima semana",
            analysis.recomendaciones,
        )

    with second_column:
        render_list("Alertas importantes", analysis.alertas)
        render_list(
            "Datos que faltan para mejorar la recomendación",
            analysis.preguntas_pendientes,
        )

    st.divider()
    st.subheader("Análisis específico")

    load_column, knee_column = st.columns(2)

    with load_column:
        st.markdown("#### Carga")
        st.write(analysis.analisis_de_carga or "Sin análisis de carga.")

    with knee_column:
        st.markdown("#### Rodilla")
        st.write(analysis.analisis_de_rodilla or "Sin análisis de rodilla.")

    st.divider()
    st.subheader("Cambios propuestos")

    if not analysis.cambios_propuestos:
        st.info(
            "No hay cambios propuestos. El análisis recomienda mantener "
            "el plan actual con seguimiento de los datos disponibles."
        )
        return

    st.info(
        "Los cambios son propuestas. No se aplicarán automáticamente "
        "al calendario ni al plan."
    )

    for change in analysis.cambios_propuestos:
        with st.container(border=True):
            st.write(f"**Fecha:** {change.fecha}")
            st.write(f"**Cambio propuesto:** {change.cambio}")
            st.write(f"**Motivo:** {change.motivo}")


def render_coach_summary() -> None:
    """Muestra un resumen del último análisis dentro del dashboard."""
    configuration = load_provider_configuration()
    latest_row = get_latest_coach_analysis()

    st.subheader("🧠 Entrenador de preparación")

    if latest_row is None:
        st.info(configuration.message)
        st.write(
            "Todavía no se ha generado un análisis. Entra en la sección "
            "«Entrenador LLM» y pulsa «Generar análisis»."
        )
        return

    analysis = get_analysis_from_row(latest_row)

    if analysis is None:
        st.warning(
            "El último análisis guardado no tiene un formato válido. "
            "Genera uno nuevo desde la sección Entrenador LLM."
        )
        return

    st.caption(
        f"Último análisis: {latest_row['created_at']} · "
        f"Proveedor: {latest_row['provider']} · "
        f"Modelo: {latest_row['model'] or 'Modo demo'}"
    )

    render_coach_analysis(analysis, compact=True)


def render_context_summary(context: dict[str, Any]) -> None:
    """Muestra al usuario el contexto utilizado sin exponer secretos."""
    with st.expander("Ver datos utilizados para el análisis"):
        metrics = context.get("metricas", {})
        safety = context.get("evaluacion_determinista", {})

        st.write("**Métricas utilizadas**")
        st.json(metrics)

        st.write("**Evaluación determinista previa**")
        st.json(safety)

        st.write("**Número de sesiones recientes enviadas al análisis**")
        st.write(len(context.get("sesiones_recientes", [])))

        st.caption(
            "No se incluyen claves API. En modo demo estos datos no salen "
            "del ordenador."
        )


def render_coach_history() -> None:
    """Muestra análisis históricos guardados localmente."""
    history = get_coach_analysis_history()

    if not history:
        st.info("Todavía no hay análisis guardados.")
        return

    for row in history:
        analysis = get_analysis_from_row(row)

        with st.expander(
            f"#{row['id']} · {row['created_at']} · "
            f"{row['provider']} · {row['model'] or 'demo'}"
        ):
            if analysis is None:
                st.warning("No se pudo interpretar este análisis histórico.")
                continue

            render_coach_analysis(analysis, compact=False)


def render_coach_plan_proposals() -> None:
    """Muestra propuestas de entrenador guardadas como versiones de plan."""
    versions = get_plan_versions()

    coach_versions = []

    for version in versions:
        try:
            snapshot = json.loads(version["snapshot_json"])
        except json.JSONDecodeError:
            continue

        if snapshot.get("origen") == "entrenador":
            coach_versions.append((version, snapshot))

    if not coach_versions:
        st.info(
            "Todavía no hay propuestas del entrenador guardadas como "
            "versiones de plan."
        )
        return

    for version, snapshot in coach_versions:
        status = get_plan_version_status(version["accepted"])
        analysis_data = snapshot.get("analisis", {})

        with st.expander(
            f"Versión #{version['id']} · {status} · {version['created_at']}"
        ):
            st.write(f"**Motivo:** {version['reason']}")

            for change in analysis_data.get("cambios_propuestos", []):
                st.write(f"**Fecha:** {change.get('fecha', '—')}")
                st.write(
                    f"**Cambio propuesto:** {change.get('cambio', '—')}"
                )
                st.write(f"**Motivo:** {change.get('motivo', '—')}")
                st.divider()

            if status == "Pendiente":
                st.info(
                    "Aceptar una propuesta no modifica el plan automáticamente. "
                    "Puedes aplicar o editar manualmente los cambios desde "
                    "«Plan semanal y mensual»."
                )

                accept_column, reject_column = st.columns(2)

                with accept_column:
                    if st.button(
                        "Aceptar como guía",
                        key=f"accept_coach_proposal_{version['id']}",
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
                        key=f"reject_coach_proposal_{version['id']}",
                    ):
                        set_plan_version_decision(
                            version["id"],
                            "Rechazada",
                        )
                        st.rerun()


def render_coach_page() -> None:
    """Renderiza el módulo completo del entrenador."""
    st.title("🧠 Entrenador LLM")
    st.caption(
        "El sistema aplica primero reglas deterministas y después, "
        "si existe un proveedor configurado, genera un análisis estructurado."
    )

    configuration = load_provider_configuration()

    if configuration.is_demo_mode:
        st.info(configuration.message)
        st.caption(
            "El modo demo es local: no usa claves, no llama a modelos "
            "externos y no envía datos fuera del ordenador."
        )
    else:
        st.success(configuration.message)
        st.caption(
            "Revisa las políticas de tu organización antes de enviar "
            "información a un proveedor externo."
        )

    generate_tab, history_tab, proposal_tab = st.tabs(
        [
            "Generar análisis",
            "Historial de análisis",
            "Propuestas de plan",
        ]
    )

    with generate_tab:
        st.write(
            "El análisis tendrá en cuenta sesiones, carga, sueño, fatiga, "
            "dolor de rodilla, competiciones y plan próximo."
        )

        if st.button("Generar análisis de entrenador", type="primary"):
            try:
                with st.spinner("Analizando datos deportivos..."):
                    analysis, used_configuration, context = (
                        generate_coach_analysis(date.today())
                    )

                    analysis_id = save_coach_analysis(
                        provider=used_configuration.provider,
                        model=used_configuration.model,
                        analysis_json=analysis.model_dump_json(),
                    )

                    st.session_state["last_coach_context"] = context
                    st.session_state["last_coach_analysis_id"] = analysis_id

                st.success(
                    f"Análisis #{analysis_id} generado correctamente."
                )
                st.rerun()

            except LLMServiceError as error:
                st.error(str(error))

        latest_row = get_latest_coach_analysis()

        if latest_row:
            analysis = get_analysis_from_row(latest_row)

            if analysis:
                st.divider()
                render_coach_analysis(analysis, compact=False)

                if analysis.cambios_propuestos:
                    if st.button(
                        "Guardar cambios como propuesta de plan",
                        type="primary",
                    ):
                        snapshot = {
                            "origen": "entrenador",
                            "analisis": analysis.model_dump(mode="json"),
                        }

                        version_id = create_plan_version(
                            reason=(
                                "Propuesta generada por el entrenador "
                                f"el {date.today().isoformat()}"
                            ),
                            snapshot_json=json.dumps(
                                snapshot,
                                ensure_ascii=False,
                            ),
                        )

                        st.success(
                            f"Propuesta guardada como versión #{version_id}. "
                            "No se ha modificado el plan."
                        )

        if "last_coach_context" in st.session_state:
            render_context_summary(st.session_state["last_coach_context"])

    with history_tab:
        render_coach_history()

    with proposal_tab:
        render_coach_plan_proposals()

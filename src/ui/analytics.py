"""Panel de análisis y estadísticas deportivas con Plotly."""

from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from src.database import (
    get_activity_sessions_between,
    get_competitions,
    get_training_plan,
)

QUALITY_SESSION_TYPES = {
    "Cuestas",
    "Sprints o progresivos",
    "Intervalos cortos",
    "Intervalos",
    "Umbral",
    "Ritmo de competición",
}

EASY_RUNNING_TYPES = {
    "Rodaje fácil",
    "Tirada larga",
    "Recuperación",
}


def seconds_to_time(total_seconds: int | float | None) -> str:
    """Convierte segundos a formato MM:SS."""
    if total_seconds is None or pd.isna(total_seconds):
        return "—"

    total_seconds = int(total_seconds)
    minutes, seconds = divmod(total_seconds, 60)

    return f"{minutes}:{seconds:02d}"


def prepare_sessions_dataframe(sessions: list[dict]) -> pd.DataFrame:
    """Convierte sesiones de SQLite a un DataFrame preparado para análisis."""
    dataframe = pd.DataFrame(sessions)

    if dataframe.empty:
        return dataframe

    dataframe["session_date"] = pd.to_datetime(dataframe["session_date"])

    numeric_columns = [
        "duration_minutes",
        "distance_km",
        "average_pace_seconds_per_km",
        "average_heart_rate",
        "max_heart_rate",
        "elevation_gain_m",
        "rpe",
        "pain_during",
        "pain_after",
        "pain_next_day",
        "sleep_hours",
    ]

    for column in numeric_columns:
        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

    dataframe["load"] = dataframe["duration_minutes"] * dataframe["rpe"]
    dataframe["pace_min_per_km"] = (
        dataframe["average_pace_seconds_per_km"] / 60
    )
    dataframe["week_start"] = (
        dataframe["session_date"]
        - pd.to_timedelta(dataframe["session_date"].dt.weekday, unit="D")
    ).dt.date
    dataframe["month"] = dataframe["session_date"].dt.to_period("M").astype(str)

    return dataframe


def render_running_distance_charts(dataframe: pd.DataFrame) -> None:
    """Muestra kilómetros semanales, mensuales y acumulados."""
    running = dataframe[dataframe["sport"] == "Carrera"].copy()

    if running.empty or running["distance_km"].dropna().empty:
        st.info("Registra distancia en sesiones de carrera para ver los gráficos de volumen.")
        return

    weekly_distance = (
        running.groupby("week_start", as_index=False)["distance_km"]
        .sum()
        .sort_values("week_start")
    )

    monthly_distance = (
        running.groupby("month", as_index=False)["distance_km"]
        .sum()
        .sort_values("month")
    )

    running = running.sort_values("session_date")
    running["cumulative_distance_km"] = running["distance_km"].fillna(0).cumsum()

    left_column, right_column = st.columns(2)

    with left_column:
        weekly_chart = px.bar(
            weekly_distance,
            x="week_start",
            y="distance_km",
            title="Kilómetros de carrera por semana",
            labels={
                "week_start": "Semana de inicio",
                "distance_km": "Kilómetros",
            },
            color_discrete_sequence=["#2E86DE"],
        )
        st.plotly_chart(weekly_chart, use_container_width=True)

    with right_column:
        monthly_chart = px.bar(
            monthly_distance,
            x="month",
            y="distance_km",
            title="Kilómetros de carrera por mes",
            labels={
                "month": "Mes",
                "distance_km": "Kilómetros",
            },
            color_discrete_sequence=["#20BF6B"],
        )
        st.plotly_chart(monthly_chart, use_container_width=True)

    cumulative_chart = px.line(
        running,
        x="session_date",
        y="cumulative_distance_km",
        markers=True,
        title="Distancia acumulada de carrera",
        labels={
            "session_date": "Fecha",
            "cumulative_distance_km": "Kilómetros acumulados",
        },
        color_discrete_sequence=["#8854D0"],
    )
    st.plotly_chart(cumulative_chart, use_container_width=True)


def render_effort_charts(dataframe: pd.DataFrame) -> None:
    """Muestra ritmo, RPE, frecuencia cardiaca y carga."""
    st.subheader("Esfuerzo y carga")

    chart_column_1, chart_column_2 = st.columns(2)

    with chart_column_1:
        pace_data = dataframe[
            (dataframe["sport"] == "Carrera")
            & dataframe["pace_min_per_km"].notna()
        ].copy()

        if pace_data.empty:
            st.info("No hay suficientes datos de ritmo.")
        else:
            pace_chart = px.scatter(
                pace_data,
                x="session_date",
                y="pace_min_per_km",
                color="session_type",
                hover_data={
                    "distance_km": True,
                    "rpe": True,
                    "pace_min_per_km": ":.2f",
                },
                title="Ritmo medio por sesión de carrera",
                labels={
                    "session_date": "Fecha",
                    "pace_min_per_km": "Minutos por km",
                    "session_type": "Tipo",
                },
            )
            pace_chart.update_yaxes(autorange="reversed")
            st.plotly_chart(pace_chart, use_container_width=True)

    with chart_column_2:
        rpe_data = dataframe[dataframe["rpe"].notna()].copy()

        if rpe_data.empty:
            st.info("No hay datos de RPE registrados.")
        else:
            rpe_chart = px.scatter(
                rpe_data,
                x="session_date",
                y="rpe",
                color="sport",
                symbol="sport",
                hover_data=["session_type", "duration_minutes"],
                title="RPE por sesión",
                labels={
                    "session_date": "Fecha",
                    "rpe": "RPE (1-10)",
                    "sport": "Deporte",
                },
            )
            rpe_chart.update_yaxes(range=[0.5, 10.5], dtick=1)
            st.plotly_chart(rpe_chart, use_container_width=True)

    chart_column_3, chart_column_4 = st.columns(2)

    with chart_column_3:
        heart_rate_data = dataframe[dataframe["average_heart_rate"].notna()].copy()

        if heart_rate_data.empty:
            st.info("No hay datos de frecuencia cardiaca media.")
        else:
            heart_rate_chart = px.scatter(
                heart_rate_data,
                x="session_date",
                y="average_heart_rate",
                color="sport",
                hover_data=["session_type", "rpe"],
                title="Frecuencia cardiaca media",
                labels={
                    "session_date": "Fecha",
                    "average_heart_rate": "Pulsaciones por minuto",
                    "sport": "Deporte",
                },
            )
            st.plotly_chart(heart_rate_chart, use_container_width=True)

    with chart_column_4:
        load_data = dataframe[dataframe["load"].notna()].copy()

        if load_data.empty:
            st.info(
                "La carga requiere duración y RPE. "
                "Registra ambos campos para visualizarla."
            )
        else:
            weekly_load = (
                load_data.groupby(["week_start", "sport"], as_index=False)["load"]
                .sum()
                .sort_values("week_start")
            )

            load_chart = px.bar(
                weekly_load,
                x="week_start",
                y="load",
                color="sport",
                barmode="stack",
                title="Carga estimada semanal por deporte",
                labels={
                    "week_start": "Semana de inicio",
                    "load": "Carga = minutos × RPE",
                    "sport": "Deporte",
                },
            )
            st.plotly_chart(load_chart, use_container_width=True)


def render_recovery_charts(dataframe: pd.DataFrame) -> None:
    """Muestra tendencias de dolor, sueño y fatiga."""
    st.subheader("Recuperación, sueño y rodilla")

    left_column, right_column = st.columns(2)

    with left_column:
        pain_columns = [
            "pain_during",
            "pain_after",
            "pain_next_day",
        ]

        pain_data = dataframe[
            ["session_date", *pain_columns]
        ].melt(
            id_vars=["session_date"],
            value_vars=pain_columns,
            var_name="measurement",
            value_name="pain",
        )

        pain_data = pain_data.dropna(subset=["pain"])

        pain_names = {
            "pain_during": "Durante",
            "pain_after": "Después",
            "pain_next_day": "Al día siguiente",
        }

        pain_data["measurement"] = pain_data["measurement"].map(pain_names)

        if pain_data.empty:
            st.info("No hay datos de dolor de rodilla.")
        else:
            pain_chart = px.line(
                pain_data,
                x="session_date",
                y="pain",
                color="measurement",
                markers=True,
                title="Dolor de rodilla a lo largo del tiempo",
                labels={
                    "session_date": "Fecha",
                    "pain": "Dolor (0-10)",
                    "measurement": "Momento de medición",
                },
            )
            pain_chart.update_yaxes(range=[0, 10], dtick=1)
            st.plotly_chart(pain_chart, use_container_width=True)

    with right_column:
        sleep_data = dataframe[dataframe["sleep_hours"].notna()].copy()

        if sleep_data.empty:
            st.info("No hay horas de sueño registradas.")
        else:
            sleep_chart = px.scatter(
                sleep_data,
                x="session_date",
                y="sleep_hours",
                color="fatigue",
                symbol="sport",
                hover_data=["rpe", "session_type"],
                title="Sueño y fatiga",
                labels={
                    "session_date": "Fecha",
                    "sleep_hours": "Horas de sueño",
                    "fatigue": "Fatiga",
                    "sport": "Deporte",
                },
            )
            st.plotly_chart(sleep_chart, use_container_width=True)


def render_plan_comparison(
    dataframe: pd.DataFrame,
    start_date: date,
    end_date: date,
) -> None:
    """Compara volumen semanal planificado y volumen real de carrera."""
    st.subheader("Planificado frente a realizado")

    plan = pd.DataFrame(get_training_plan())

    if plan.empty:
        st.info("No hay sesiones planificadas para comparar.")
        return

    plan["planned_date"] = pd.to_datetime(plan["planned_date"])
    plan = plan[
        (plan["planned_date"].dt.date >= start_date)
        & (plan["planned_date"].dt.date <= end_date)
        & (plan["sport"] == "Carrera")
        & (plan["status"] != "Cancelado")
    ].copy()

    actual_running = dataframe[dataframe["sport"] == "Carrera"].copy()

    if plan.empty and actual_running.empty:
        st.info("No hay datos de carrera para comparar en el periodo seleccionado.")
        return

    if not plan.empty:
        plan["week_start"] = (
            plan["planned_date"]
            - pd.to_timedelta(plan["planned_date"].dt.weekday, unit="D")
        ).dt.date

        planned_weekly = (
            plan.groupby("week_start", as_index=False)["target_distance_km"]
            .sum()
            .rename(columns={"target_distance_km": "Kilómetros"})
        )
        planned_weekly["Tipo"] = "Planificado"
    else:
        planned_weekly = pd.DataFrame(
            columns=["week_start", "Kilómetros", "Tipo"]
        )

    if not actual_running.empty:
        actual_weekly = (
            actual_running.groupby("week_start", as_index=False)["distance_km"]
            .sum()
            .rename(columns={"distance_km": "Kilómetros"})
        )
        actual_weekly["Tipo"] = "Realizado"
    else:
        actual_weekly = pd.DataFrame(
            columns=["week_start", "Kilómetros", "Tipo"]
        )

    comparison = pd.concat(
        [planned_weekly, actual_weekly],
        ignore_index=True,
    )

    if comparison.empty:
        st.info("No hay kilómetros suficientes para el gráfico comparativo.")
        return

    comparison_chart = px.bar(
        comparison,
        x="week_start",
        y="Kilómetros",
        color="Tipo",
        barmode="group",
        title="Kilómetros semanales: planificado frente a realizado",
        labels={
            "week_start": "Semana de inicio",
        },
        color_discrete_map={
            "Planificado": "#95A5A6",
            "Realizado": "#2E86DE",
        },
    )
    st.plotly_chart(comparison_chart, use_container_width=True)

    st.caption(
        "La comparación es semanal y no vincula automáticamente un registro "
        "real con una sesión concreta del plan."
    )


def render_quality_and_easy_run_analysis(dataframe: pd.DataFrame) -> None:
    """Muestra cumplimiento de calidad y evolución de rodajes fáciles."""
    st.subheader("Calidad y rodajes fáciles")

    plan = pd.DataFrame(get_training_plan())

    left_column, right_column = st.columns(2)

    with left_column:
        if plan.empty:
            st.info("No hay sesiones planificadas.")
        else:
            quality_plan = plan[
                plan["session_type"].isin(QUALITY_SESSION_TYPES)
            ]

            if quality_plan.empty:
                st.info("No hay sesiones de calidad planificadas.")
            else:
                completed = int(
                    (quality_plan["status"] == "Completado").sum()
                )
                total = len(quality_plan)
                percentage = completed / total * 100 if total else 0

                st.metric(
                    "Cumplimiento de sesiones de calidad",
                    f"{percentage:.0f}%",
                    help=(
                        "Porcentaje de sesiones de calidad planificadas "
                        "marcadas como completadas."
                    ),
                )
                st.progress(percentage / 100)
                st.caption(f"{completed} de {total} sesiones de calidad completadas.")

    with right_column:
        easy_runs = dataframe[
            (dataframe["sport"] == "Carrera")
            & dataframe["session_type"].isin(EASY_RUNNING_TYPES)
            & dataframe["pace_min_per_km"].notna()
        ].copy()

        if easy_runs.empty:
            st.info("No hay rodajes fáciles con ritmo registrado.")
        else:
            easy_chart = px.line(
                easy_runs.sort_values("session_date"),
                x="session_date",
                y="pace_min_per_km",
                markers=True,
                title="Evolución de rodajes fáciles",
                labels={
                    "session_date": "Fecha",
                    "pace_min_per_km": "Minutos por km",
                },
            )
            easy_chart.update_yaxes(autorange="reversed")
            st.plotly_chart(easy_chart, use_container_width=True)


def render_competition_evolution() -> None:
    """Muestra resultados oficiales disponibles de 5 km y 10 km."""
    st.subheader("Evolución de marcas en competición")

    competitions = pd.DataFrame(get_competitions())

    if competitions.empty:
        st.info("No hay competiciones registradas.")
        return

    competitions = competitions[
        competitions["official_time_seconds"].notna()
        & competitions["distance_km"].isin([5.0, 10.0])
    ].copy()

    if competitions.empty:
        st.info(
            "Cuando registres un tiempo oficial de 5 km o 10 km, "
            "aparecerá aquí su evolución."
        )
        return

    competitions["competition_date"] = pd.to_datetime(
        competitions["competition_date"]
    )
    competitions["time_minutes"] = (
        competitions["official_time_seconds"] / 60
    )
    competitions["distance_label"] = (
        competitions["distance_km"].astype(int).astype(str) + " km"
    )
    competitions["time_text"] = competitions["official_time_seconds"].apply(
        seconds_to_time
    )

    competition_chart = px.line(
        competitions.sort_values("competition_date"),
        x="competition_date",
        y="time_minutes",
        color="distance_label",
        markers=True,
        hover_name="name",
        hover_data={
            "time_text": True,
            "time_minutes": False,
        },
        title="Evolución de marcas en 5 km y 10 km",
        labels={
            "competition_date": "Fecha",
            "time_minutes": "Tiempo (minutos)",
            "distance_label": "Distancia",
        },
    )
    competition_chart.update_yaxes(autorange="reversed")
    st.plotly_chart(competition_chart, use_container_width=True)


def render_analytics() -> None:
    """Renderiza toda la sección de análisis deportivo."""
    st.title("📊 Análisis y estadísticas")
    st.caption(
        "Los cálculos se basan exclusivamente en los datos registrados. "
        "La carga estimada es duración en minutos × RPE."
    )

    all_sessions = get_activity_sessions_between(
        date(2000, 1, 1),
        date.today(),
    )

    dataframe = prepare_sessions_dataframe(all_sessions)

    if dataframe.empty:
        st.info(
            "Todavía no hay entrenamientos registrados. "
            "Añade una sesión desde «Registrar entrenamiento» para iniciar el análisis."
        )
        return

    minimum_date = dataframe["session_date"].dt.date.min()
    maximum_date = dataframe["session_date"].dt.date.max()

    selected_range = st.date_input(
        "Periodo de análisis",
        value=(minimum_date, maximum_date),
        min_value=minimum_date,
        max_value=maximum_date,
    )

    if not isinstance(selected_range, tuple) or len(selected_range) != 2:
        st.warning("Selecciona una fecha de inicio y una fecha de fin.")
        return

    start_date, end_date = selected_range

    if start_date > end_date:
        st.error("La fecha inicial no puede ser posterior a la fecha final.")
        return

    filtered_dataframe = dataframe[
        (dataframe["session_date"].dt.date >= start_date)
        & (dataframe["session_date"].dt.date <= end_date)
    ].copy()

    if filtered_dataframe.empty:
        st.info("No hay sesiones en el periodo seleccionado.")
        return

    metric_1, metric_2, metric_3, metric_4 = st.columns(4)

    total_running_km = filtered_dataframe.loc[
        filtered_dataframe["sport"] == "Carrera",
        "distance_km",
    ].sum()

    total_load = filtered_dataframe["load"].sum(min_count=1)
    total_load_text = "—" if pd.isna(total_load) else f"{total_load:.0f}"

    metric_1.metric("Sesiones registradas", len(filtered_dataframe))
    metric_2.metric("Km de carrera", f"{total_running_km:.1f} km")
    metric_3.metric("Carga registrada", total_load_text)
    metric_4.metric(
        "Deportes practicados",
        filtered_dataframe["sport"].nunique(),
    )

    st.divider()

    sport_distribution = (
        filtered_dataframe["sport"]
        .value_counts()
        .reset_index()
        .rename(columns={"sport": "Deporte", "count": "Sesiones"})
    )

    left_column, right_column = st.columns(2)

    with left_column:
        sport_chart = px.pie(
            sport_distribution,
            names="Deporte",
            values="Sesiones",
            title="Distribución de entrenamientos por deporte",
        )
        st.plotly_chart(sport_chart, use_container_width=True)

    with right_column:
        source_distribution = (
            filtered_dataframe["source"]
            .value_counts()
            .reset_index()
            .rename(columns={"source": "Origen", "count": "Sesiones"})
        )

        source_chart = px.bar(
            source_distribution,
            x="Origen",
            y="Sesiones",
            title="Origen de los datos",
            color="Origen",
        )
        st.plotly_chart(source_chart, use_container_width=True)

    st.divider()
    render_running_distance_charts(filtered_dataframe)

    st.divider()
    render_effort_charts(filtered_dataframe)

    st.divider()
    render_recovery_charts(filtered_dataframe)

    st.divider()
    render_plan_comparison(filtered_dataframe, start_date, end_date)

    st.divider()
    render_quality_and_easy_run_analysis(filtered_dataframe)

    st.divider()
    render_competition_evolution()

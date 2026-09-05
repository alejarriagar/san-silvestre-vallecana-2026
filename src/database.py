"""Persistencia SQLite y datos iniciales de la aplicación."""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "data" / "training.db"

TRAINING_STATUSES = (
    "Pendiente",
    "Completado",
    "Modificado",
    "Cancelado",
)


def get_connection() -> sqlite3.Connection:
    """Crea una conexión SQLite configurada para devolver filas como diccionarios."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def init_database() -> None:
    """Crea las tablas necesarias y precarga los datos deportivos iniciales."""
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS athlete_profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                sex TEXT NOT NULL,
                age INTEGER NOT NULL,
                height_cm REAL,
                weight_kg REAL,
                health_notes TEXT,
                diet TEXT,
                alcohol_consumption TEXT,
                coffee_per_day INTEGER,
                sleep_hours_baseline REAL,
                supplements TEXT,
                training_preferences TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS competitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                competition_date TEXT NOT NULL,
                distance_km REAL NOT NULL,
                goal_time_seconds INTEGER,
                official_time_seconds INTEGER,
                average_pace_seconds_per_km INTEGER,
                average_heart_rate INTEGER,
                comments TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, competition_date)
            );

            CREATE TABLE IF NOT EXISTS planned_trainings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                planned_date TEXT NOT NULL,
                sport TEXT NOT NULL,
                session_type TEXT NOT NULL,
                description TEXT NOT NULL,
                target_distance_km REAL,
                target_duration_min REAL,
                target_intensity TEXT,
                target_rpe INTEGER,
                target_pace TEXT,
                terrain TEXT,
                warmup TEXT,
                main_set TEXT,
                cooldown TEXT,
                rationale TEXT,
                status TEXT NOT NULL DEFAULT 'Pendiente',
                is_deload INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(planned_date, description)
            );

            CREATE TABLE IF NOT EXISTS activity_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_date TEXT NOT NULL,
                sport TEXT NOT NULL,
                session_type TEXT,
                duration_minutes REAL,
                distance_km REAL,
                average_pace_seconds_per_km INTEGER,
                average_heart_rate INTEGER,
                max_heart_rate INTEGER,
                elevation_gain_m REAL,
                rpe INTEGER,
                surface TEXT,
                shoes TEXT,
                pain_during INTEGER,
                pain_after INTEGER,
                pain_next_day INTEGER,
                sleep_hours REAL,
                fatigue TEXT,
                comments TEXT,
                source TEXT NOT NULL DEFAULT 'Manual',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS plan_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                reason TEXT NOT NULL,
                snapshot_json TEXT NOT NULL,
                accepted INTEGER NOT NULL DEFAULT 0
            );
            """
        )

        _seed_initial_profile(connection)
        _seed_competitions(connection)
        _seed_initial_plan(connection)


def _seed_initial_profile(connection: sqlite3.Connection) -> None:
    """Crea el perfil inicial solo si todavía no existe."""
    connection.execute(
        """
        INSERT OR IGNORE INTO athlete_profile (
            id,
            sex,
            age,
            height_cm,
            weight_kg,
            health_notes,
            diet,
            alcohol_consumption,
            coffee_per_day,
            sleep_hours_baseline,
            supplements,
            training_preferences
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            1,
            "Hombre",
            31,
            178.0,
            80.0,
            (
                "Sin enfermedades conocidas, medicación, alergias o "
                "intolerancias. Molestia ocasional anterior/inferior en "
                "rodilla derecha tras correr."
            ),
            "Omnívora",
            "No consume alcohol",
            2,
            7.5,
            "Creatina, aminoácidos, electrolitos y carbohidratos de rápida ingestión.",
            (
                "Jiu-jitsu normalmente lunes y jueves. Musculación tres días "
                "por semana. Bicicleta normalmente sábado o domingo. "
                "Mantener inicialmente dos días de carrera semanales."
            ),
        ),
    )


def _seed_competitions(connection: sqlite3.Connection) -> None:
    """Precarga las dos competiciones objetivo."""
    competitions = [
        (
            "XVI Derbi de las Aficiones 2026",
            "2026-10-25",
            10.0,
            None,
            None,
            None,
            None,
            (
                "Carrera de control. Competir con intensidad. Recorrido "
                "favorable en la primera parte y más exigente en los dos "
                "kilómetros finales."
            ),
        ),
        (
            "San Silvestre Vallecana 2026",
            "2026-12-31",
            10.0,
            2999,
            None,
            None,
            None,
            (
                "Objetivo principal: bajar de 50 minutos y conseguir un "
                "cajón de salida adecuado."
            ),
        ),
    ]

    connection.executemany(
        """
        INSERT OR IGNORE INTO competitions (
            name,
            competition_date,
            distance_km,
            goal_time_seconds,
            official_time_seconds,
            average_pace_seconds_per_km,
            average_heart_rate,
            comments
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        competitions,
    )


def _seed_initial_plan(connection: sqlite3.Connection) -> None:
    """Precarga el bloque de entrenamiento inicial proporcionado."""

    existing_plan = connection.execute(
        "SELECT 1 FROM planned_trainings LIMIT 1"
    ).fetchone()

    if existing_plan is not None:
        return


    trainings = [
        (
            "2026-08-29",
            "Carrera",
            "Rodaje fácil",
            "6 km muy fáciles.",
            6.0,
            40.0,
            "Muy suave; conversación completa.",
            3,
            "Sin ritmo rígido.",
            "Superficie llana y cómoda.",
            "5-10 min de movilidad y trote progresivo.",
            "6 km muy fáciles.",
            "Caminar 3-5 min y movilidad suave.",
            "Sesión de reinicio para observar sensaciones y rodilla.",
            0,
        ),
        (
            "2026-09-01",
            "Carrera",
            "Progresivos",
            "6-7 km fáciles + 4 progresivos de 15 segundos.",
            6.5,
            45.0,
            "Fácil; progresivos ágiles sin esprintar.",
            4,
            "Conversacional en el rodaje.",
            "Llano o pista de atletismo.",
            "10 min de trote suave y movilidad.",
            "6-7 km fáciles + 4 × 15 s progresivos con recuperación completa.",
            "5-10 min muy suaves.",
            "Introducir técnica y velocidad de forma controlada.",
            0,
        ),
        (
            "2026-09-06",
            "Carrera",
            "Rodaje fácil",
            "7 km fáciles.",
            7.0,
            47.0,
            "RPE bajo; conversación completa.",
            3,
            "Sin ritmo rígido.",
            "Terreno llano o ligeramente ondulado.",
            "Movilidad breve y primeros minutos muy suaves.",
            "7 km fáciles.",
            "Caminar y movilidad suave.",
            "Construir volumen sin añadir intensidad.",
            0,
        ),
        (
            "2026-09-08",
            "Carrera",
            "Intervalos cortos",
            "Calentamiento + 6 × 1 min vivo, recuperando 2 min suaves + vuelta a la calma.",
            6.5,
            45.0,
            "Vivo pero controlado; sin llegar al máximo.",
            6,
            "Guiarse por RPE y técnica.",
            "Pista, carril bici llano o camino firme.",
            "12-15 min suaves + movilidad dinámica.",
            "6 × 1 min vivo / 2 min suaves.",
            "10 min suaves.",
            "Primera sesión de calidad corta para desarrollar tolerancia al esfuerzo.",
            0,
        ),
        (
            "2026-09-13",
            "Carrera",
            "Rodaje fácil",
            "8 km fáciles.",
            8.0,
            54.0,
            "Fácil; mantener conversación.",
            3,
            "Sin ritmo rígido.",
            "Terreno cómodo y preferiblemente llano.",
            "Inicio muy suave durante 10 min.",
            "8 km fáciles.",
            "Caminar 3-5 min.",
            "Consolidar volumen observando RPE y respuesta de la rodilla.",
            0,
        ),
        (
            "2026-09-15",
            "Carrera",
            "Intervalos",
            "Calentamiento + 6 × 2 min controlados, recuperando 2 min suaves + vuelta a la calma.",
            7.0,
            52.0,
            "Controlado; debe quedar margen al terminar.",
            6,
            "Ritmo orientativo, ajustado por fatiga y terreno.",
            "Pista o superficie llana y regular.",
            "15 min suaves + movilidad dinámica.",
            "6 × 2 min controlados / 2 min suaves.",
            "10 min suaves.",
            "Progresar gradualmente el tiempo de trabajo de calidad.",
            0,
        ),
        (
            "2026-09-20",
            "Carrera",
            "Tirada larga",
            "8-9 km fáciles.",
            8.5,
            58.0,
            "Fácil; conversación sostenida.",
            4,
            "Sin ritmo rígido.",
            "Terreno cómodo; evitar desnivel agresivo.",
            "Primer kilómetro especialmente suave.",
            "8-9 km fáciles.",
            "Movilidad suave y recuperación.",
            "Aumentar ligeramente la resistencia aeróbica.",
            0,
        ),
        (
            "2026-09-22",
            "Carrera",
            "Intervalos",
            "Calentamiento + 5 × 2 min controlados, recuperando 2 min suaves + vuelta a la calma.",
            6.5,
            48.0,
            "Controlado y con buena técnica.",
            6,
            "Ritmo adaptado a sensaciones.",
            "Pista o recorrido llano.",
            "12-15 min suaves + movilidad dinámica.",
            "5 × 2 min controlados / 2 min suaves.",
            "10 min suaves.",
            "Semana de descarga: reducir ligeramente el volumen de calidad.",
            1,
        ),
        (
            "2026-09-27",
            "Carrera",
            "Rodaje fácil",
            "7-8 km fáciles.",
            7.5,
            52.0,
            "Fácil; conversación completa.",
            3,
            "Sin ritmo rígido.",
            "Terreno llano y cómodo.",
            "Inicio muy progresivo.",
            "7-8 km fáciles.",
            "Caminar y movilidad suave.",
            "Completar la semana de descarga sin recuperar carga perdida.",
            1,
        ),
    ]

    connection.executemany(
        """
        INSERT INTO planned_trainings (
            planned_date,
            sport,
            session_type,
            description,
            target_distance_km,
            target_duration_min,
            target_intensity,
            target_rpe,
            target_pace,
            terrain,
            warmup,
            main_set,
            cooldown,
            rationale,
            is_deload
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        trainings,
    )


def get_profile() -> dict[str, Any]:
    """Obtiene el perfil deportivo único del usuario."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM athlete_profile WHERE id = 1"
        ).fetchone()

    return dict(row) if row else {}


def update_profile(profile: dict[str, Any]) -> None:
    """Actualiza los campos editables del perfil deportivo."""
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE athlete_profile
            SET
                sex = :sex,
                age = :age,
                height_cm = :height_cm,
                weight_kg = :weight_kg,
                health_notes = :health_notes,
                diet = :diet,
                alcohol_consumption = :alcohol_consumption,
                coffee_per_day = :coffee_per_day,
                sleep_hours_baseline = :sleep_hours_baseline,
                supplements = :supplements,
                training_preferences = :training_preferences,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            """,
            profile,
        )


def get_competitions() -> list[dict[str, Any]]:
    """Devuelve las competiciones ordenadas por fecha."""
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM competitions ORDER BY competition_date"
        ).fetchall()

    return [dict(row) for row in rows]


def get_next_competition(today: date) -> dict[str, Any] | None:
    """Obtiene la siguiente competición pendiente."""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM competitions
            WHERE competition_date >= ?
            ORDER BY competition_date
            LIMIT 1
            """,
            (today.isoformat(),),
        ).fetchone()

    return dict(row) if row else None


def get_training_plan() -> list[dict[str, Any]]:
    """Obtiene todos los entrenamientos planificados por fecha."""
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM planned_trainings ORDER BY planned_date, id"
        ).fetchall()

    return [dict(row) for row in rows]


def get_next_training(today: date) -> dict[str, Any] | None:
    """Obtiene el siguiente entrenamiento pendiente."""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM planned_trainings
            WHERE planned_date >= ?
              AND status = 'Pendiente'
            ORDER BY planned_date, id
            LIMIT 1
            """,
            (today.isoformat(),),
        ).fetchone()

        if row is None:
            row = connection.execute(
                """
                SELECT *
                FROM planned_trainings
                WHERE status = 'Pendiente'
                ORDER BY planned_date, id
                LIMIT 1
                """
            ).fetchone()

    return dict(row) if row else None


def update_training_status(training_id: int, status: str) -> None:
    """Actualiza el estado de un entrenamiento planificado."""
    if status not in TRAINING_STATUSES:
        raise ValueError(f"Estado de entrenamiento no válido: {status}")

    with get_connection() as connection:
        connection.execute(
            "UPDATE planned_trainings SET status = ? WHERE id = ?",
            (status, training_id),
        )


def get_completion_summary() -> dict[str, float]:
    """Calcula el cumplimiento de sesiones excluyendo las canceladas."""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'Completado' THEN 1 ELSE 0 END) AS completed
            FROM planned_trainings
            WHERE status != 'Cancelado'
            """
        ).fetchone()

    total = int(row["total"] or 0)
    completed = int(row["completed"] or 0)
    percentage = (completed / total * 100) if total else 0.0

    return {
        "total": total,
        "completed": completed,
        "percentage": percentage,
    }


def get_weekly_planned_distance(today: date) -> float:
    """Suma los kilómetros de carrera previstos en la semana actual."""
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT COALESCE(SUM(target_distance_km), 0) AS total_distance
            FROM planned_trainings
            WHERE sport = 'Carrera'
              AND planned_date BETWEEN ? AND ?
              AND status != 'Cancelado'
            """,
            (week_start.isoformat(), week_end.isoformat()),
        ).fetchone()

    return float(row["total_distance"] or 0.0)

def create_activity_session(session: dict[str, Any]) -> int:
    """Guarda un entrenamiento realizado y devuelve su identificador."""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO activity_sessions (
                session_date,
                sport,
                session_type,
                duration_minutes,
                distance_km,
                average_pace_seconds_per_km,
                average_heart_rate,
                max_heart_rate,
                elevation_gain_m,
                rpe,
                surface,
                shoes,
                pain_during,
                pain_after,
                pain_next_day,
                sleep_hours,
                fatigue,
                comments,
                source
            )
            VALUES (
                :session_date,
                :sport,
                :session_type,
                :duration_minutes,
                :distance_km,
                :average_pace_seconds_per_km,
                :average_heart_rate,
                :max_heart_rate,
                :elevation_gain_m,
                :rpe,
                :surface,
                :shoes,
                :pain_during,
                :pain_after,
                :pain_next_day,
                :sleep_hours,
                :fatigue,
                :comments,
                :source
            )
            """,
            session,
        )

    return int(cursor.lastrowid)


def get_recent_activity_sessions(limit: int = 20) -> list[dict[str, Any]]:
    """Obtiene las últimas sesiones realizadas, ordenadas por fecha."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM activity_sessions
            ORDER BY session_date DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def get_last_activity_session() -> dict[str, Any] | None:
    """Obtiene el último entrenamiento registrado."""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM activity_sessions
            ORDER BY session_date DESC, id DESC
            LIMIT 1
            """
        ).fetchone()

    return dict(row) if row else None

def get_activity_sessions_between(
    start_date: date,
    end_date: date,
) -> list[dict[str, Any]]:
    """Obtiene sesiones realizadas entre dos fechas, ambas incluidas."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM activity_sessions
            WHERE session_date BETWEEN ? AND ?
            ORDER BY session_date DESC, id DESC
            """,
            (start_date.isoformat(), end_date.isoformat()),
        ).fetchall()

    return [dict(row) for row in rows]

def create_activity_sessions(sessions: list[dict[str, Any]]) -> int:
    """Guarda varias sesiones en una única transacción SQLite."""
    if not sessions:
        return 0

    with get_connection() as connection:
        connection.executemany(
            """
            INSERT INTO activity_sessions (
                session_date,
                sport,
                session_type,
                duration_minutes,
                distance_km,
                average_pace_seconds_per_km,
                average_heart_rate,
                max_heart_rate,
                elevation_gain_m,
                rpe,
                surface,
                shoes,
                pain_during,
                pain_after,
                pain_next_day,
                sleep_hours,
                fatigue,
                comments,
                source
            )
            VALUES (
                :session_date,
                :sport,
                :session_type,
                :duration_minutes,
                :distance_km,
                :average_pace_seconds_per_km,
                :average_heart_rate,
                :max_heart_rate,
                :elevation_gain_m,
                :rpe,
                :surface,
                :shoes,
                :pain_during,
                :pain_after,
                :pain_next_day,
                :sleep_hours,
                :fatigue,
                :comments,
                :source
            )
            """,
            sessions,
        )

    return len(sessions)


def get_activity_sessions_for_duplicate_detection() -> list[dict[str, Any]]:
    """Obtiene los campos necesarios para detectar importaciones duplicadas."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                session_date,
                sport,
                session_type,
                duration_minutes,
                distance_km
            FROM activity_sessions
            """
        ).fetchall()

    return [dict(row) for row in rows]

def get_competition_by_id(competition_id: int) -> dict[str, Any] | None:
    """Obtiene una competición concreta por su identificador."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM competitions WHERE id = ?",
            (competition_id,),
        ).fetchone()

    return dict(row) if row else None


def create_competition(competition: dict[str, Any]) -> int:
    """Crea una nueva competición y devuelve su identificador."""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO competitions (
                name,
                competition_date,
                distance_km,
                goal_time_seconds,
                comments
            )
            VALUES (
                :name,
                :competition_date,
                :distance_km,
                :goal_time_seconds,
                :comments
            )
            """,
            competition,
        )

    return int(cursor.lastrowid)


def update_competition_result(
    competition_id: int,
    official_time_seconds: int,
    average_pace_seconds_per_km: int,
    average_heart_rate: int | None,
    comments: str | None,
) -> None:
    """Guarda el resultado oficial de una competición."""
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE competitions
            SET
                official_time_seconds = ?,
                average_pace_seconds_per_km = ?,
                average_heart_rate = ?,
                comments = ?
            WHERE id = ?
            """,
            (
                official_time_seconds,
                average_pace_seconds_per_km,
                average_heart_rate,
                comments,
                competition_id,
            ),
        )


def create_plan_version(reason: str, snapshot_json: str) -> int:
    """Guarda una propuesta de versión de plan pendiente de decisión."""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO plan_versions (
                reason,
                snapshot_json,
                accepted
            )
            VALUES (?, ?, 0)
            """,
            (reason, snapshot_json),
        )

    return int(cursor.lastrowid)


def get_plan_versions() -> list[dict[str, Any]]:
    """Obtiene el historial de propuestas de planificación."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM plan_versions
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def set_plan_version_decision(
    plan_version_id: int,
    decision: str,
) -> None:
    """Acepta o rechaza una propuesta de plan.

    Se usa 1 para aceptada, 0 para pendiente y -1 para rechazada.
    """
    decisions = {
        "Aceptada": 1,
        "Pendiente": 0,
        "Rechazada": -1,
    }

    if decision not in decisions:
        raise ValueError(f"Decisión no válida: {decision}")

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE plan_versions
            SET accepted = ?
            WHERE id = ?
            """,
            (decisions[decision], plan_version_id),
        )

def get_planned_training_by_id(training_id: int) -> dict[str, Any] | None:
    """Obtiene un entrenamiento planificado por su identificador."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM planned_trainings WHERE id = ?",
            (training_id,),
        ).fetchone()

    return dict(row) if row else None


def create_planned_training(training: dict[str, Any]) -> int:
    """Crea un nuevo entrenamiento planificado."""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO planned_trainings (
                planned_date,
                sport,
                session_type,
                description,
                target_distance_km,
                target_duration_min,
                target_intensity,
                target_rpe,
                target_pace,
                terrain,
                warmup,
                main_set,
                cooldown,
                rationale,
                status,
                is_deload
            )
            VALUES (
                :planned_date,
                :sport,
                :session_type,
                :description,
                :target_distance_km,
                :target_duration_min,
                :target_intensity,
                :target_rpe,
                :target_pace,
                :terrain,
                :warmup,
                :main_set,
                :cooldown,
                :rationale,
                :status,
                :is_deload
            )
            """,
            training,
        )

    return int(cursor.lastrowid)


def update_planned_training(training: dict[str, Any]) -> None:
    """Actualiza todos los campos editables de un entrenamiento planificado."""
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE planned_trainings
            SET
                planned_date = :planned_date,
                sport = :sport,
                session_type = :session_type,
                description = :description,
                target_distance_km = :target_distance_km,
                target_duration_min = :target_duration_min,
                target_intensity = :target_intensity,
                target_rpe = :target_rpe,
                target_pace = :target_pace,
                terrain = :terrain,
                warmup = :warmup,
                main_set = :main_set,
                cooldown = :cooldown,
                rationale = :rationale,
                status = :status,
                is_deload = :is_deload
            WHERE id = :id
            """,
            training,
        )

def _ensure_coach_analyses_table(connection: sqlite3.Connection) -> None:
    """Crea la tabla de análisis del entrenador si todavía no existe."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS coach_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            provider TEXT NOT NULL,
            model TEXT,
            analysis_json TEXT NOT NULL
        )
        """
    )


def save_coach_analysis(
    provider: str,
    model: str | None,
    analysis_json: str,
) -> int:
    """Guarda un análisis estructurado generado por el entrenador."""
    with get_connection() as connection:
        _ensure_coach_analyses_table(connection)

        cursor = connection.execute(
            """
            INSERT INTO coach_analyses (
                provider,
                model,
                analysis_json
            )
            VALUES (?, ?, ?)
            """,
            (provider, model, analysis_json),
        )

    return int(cursor.lastrowid)


def get_latest_coach_analysis() -> dict[str, Any] | None:
    """Obtiene el análisis más reciente del entrenador."""
    with get_connection() as connection:
        _ensure_coach_analyses_table(connection)

        row = connection.execute(
            """
            SELECT *
            FROM coach_analyses
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """
        ).fetchone()

    return dict(row) if row else None


def get_coach_analysis_history(
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Obtiene el historial de análisis del entrenador."""
    with get_connection() as connection:
        _ensure_coach_analyses_table(connection)

        rows = connection.execute(
            """
            SELECT *
            FROM coach_analyses
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]

def _ensure_session_attachments_table(
    connection: sqlite3.Connection,
) -> None:
    """Crea la tabla de adjuntos de sesiones si todavía no existe."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS session_attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            original_file_name TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            mime_type TEXT,
            size_bytes INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id)
                REFERENCES activity_sessions(id)
                ON DELETE CASCADE
        )
        """
    )


def create_session_attachment(
    session_id: int,
    original_file_name: str,
    stored_path: str,
    mime_type: str | None,
    size_bytes: int,
) -> int:
    """Guarda los metadatos de un adjunto asociado a una sesión."""
    with get_connection() as connection:
        _ensure_session_attachments_table(connection)

        cursor = connection.execute(
            """
            INSERT INTO session_attachments (
                session_id,
                original_file_name,
                stored_path,
                mime_type,
                size_bytes
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                original_file_name,
                stored_path,
                mime_type,
                size_bytes,
            ),
        )

    return int(cursor.lastrowid)


def get_session_attachments(
    session_id: int,
) -> list[dict[str, Any]]:
    """Obtiene los adjuntos de una sesión ordenados por fecha."""
    with get_connection() as connection:
        _ensure_session_attachments_table(connection)

        rows = connection.execute(
            """
            SELECT *
            FROM session_attachments
            WHERE session_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (session_id,),
        ).fetchall()

    return [dict(row) for row in rows]

def delete_activity_session(session_id: int) -> list[str]:
    """Elimina una sesión realizada y devuelve las rutas de sus adjuntos."""
    with get_connection() as connection:
        _ensure_session_attachments_table(connection)

        attachment_rows = connection.execute(
            """
            SELECT stored_path
            FROM session_attachments
            WHERE session_id = ?
            """,
            (session_id,),
        ).fetchall()

        cursor = connection.execute(
            """
            DELETE FROM activity_sessions
            WHERE id = ?
            """,
            (session_id,),
        )

        if cursor.rowcount == 0:
            raise ValueError("No se ha encontrado la sesión a eliminar.")

    return [
        str(row["stored_path"])
        for row in attachment_rows
    ]


def _ensure_session_nutrition_table(
    connection: sqlite3.Connection,
) -> None:
    """Crea la tabla de nutrición previa si todavía no existe."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS session_nutrition (
            session_id INTEGER PRIMARY KEY,
            pre_workout_food TEXT,
            minutes_before INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id)
                REFERENCES activity_sessions(id)
                ON DELETE CASCADE
        )
        """
    )


def save_session_nutrition(
    session_id: int,
    pre_workout_food: str | None,
    minutes_before: int | None,
) -> None:
    """Guarda o actualiza la comida previa de una sesión."""
    with get_connection() as connection:
        _ensure_session_nutrition_table(connection)

        if not pre_workout_food and minutes_before is None:
            connection.execute(
                """
                DELETE FROM session_nutrition
                WHERE session_id = ?
                """,
                (session_id,),
            )
            return

        connection.execute(
            """
            INSERT INTO session_nutrition (
                session_id,
                pre_workout_food,
                minutes_before
            )
            VALUES (?, ?, ?)
            ON CONFLICT(session_id)
            DO UPDATE SET
                pre_workout_food = excluded.pre_workout_food,
                minutes_before = excluded.minutes_before
            """,
            (
                session_id,
                pre_workout_food,
                minutes_before,
            ),
        )


def get_session_nutrition(
    session_id: int,
) -> dict[str, Any] | None:
    """Obtiene la comida previa asociada a una sesión."""
    with get_connection() as connection:
        _ensure_session_nutrition_table(connection)

        row = connection.execute(
            """
            SELECT *
            FROM session_nutrition
            WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()

    return dict(row) if row else None


def _remove_planned_training_unique_constraint(
    connection: sqlite3.Connection,
) -> None:
    """Migra planned_trainings para permitir sesiones similares el mismo día."""
    table_row = connection.execute(
        """
        SELECT sql
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'planned_trainings'
        """
    ).fetchone()

    if table_row is None or not table_row["sql"]:
        return

    normalized_sql = (
        table_row["sql"]
        .upper()
        .replace(" ", "")
        .replace("\n", "")
    )

    constraint_signature = "UNIQUE(PLANNED_DATE,DESCRIPTION)"

    if constraint_signature not in normalized_sql:
        return

    connection.execute("PRAGMA foreign_keys = OFF")

    try:
        connection.execute(
            """
            DROP TABLE IF EXISTS planned_trainings_migrated
            """
        )

        connection.execute(
            """
            CREATE TABLE planned_trainings_migrated (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                planned_date TEXT NOT NULL,
                sport TEXT NOT NULL,
                session_type TEXT NOT NULL,
                description TEXT NOT NULL,
                target_distance_km REAL,
                target_duration_min REAL,
                target_intensity TEXT,
                target_rpe INTEGER,
                target_pace TEXT,
                terrain TEXT,
                warmup TEXT,
                main_set TEXT,
                cooldown TEXT,
                rationale TEXT,
                status TEXT NOT NULL DEFAULT 'Pendiente',
                is_deload INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.execute(
            """
            INSERT INTO planned_trainings_migrated (
                id,
                planned_date,
                sport,
                session_type,
                description,
                target_distance_km,
                target_duration_min,
                target_intensity,
                target_rpe,
                target_pace,
                terrain,
                warmup,
                main_set,
                cooldown,
                rationale,
                status,
                is_deload,
                created_at
            )
            SELECT
                id,
                planned_date,
                sport,
                session_type,
                description,
                target_distance_km,
                target_duration_min,
                target_intensity,
                target_rpe,
                target_pace,
                terrain,
                warmup,
                main_set,
                cooldown,
                rationale,
                status,
                is_deload,
                created_at
            FROM planned_trainings
            """
        )

        connection.execute(
            """
            DROP TABLE planned_trainings
            """
        )

        connection.execute(
            """
            ALTER TABLE planned_trainings_migrated
            RENAME TO planned_trainings
            """
        )
    finally:
        connection.execute("PRAGMA foreign_keys = ON")


def move_planned_training(
    training_id: int,
    new_date: date,
) -> None:
    """Mueve una sesión planificada a otra fecha sin duplicarla."""
    with get_connection() as connection:
        _remove_planned_training_unique_constraint(connection)

        current_row = connection.execute(
            """
            SELECT planned_date
            FROM planned_trainings
            WHERE id = ?
            """,
            (training_id,),
        ).fetchone()

        if current_row is None:
            raise ValueError(
                "No se ha encontrado el entrenamiento que quieres mover."
            )

        new_date_iso = new_date.isoformat()

        # Evita procesar dos veces el mismo evento enviado por el calendario.
        if current_row["planned_date"] == new_date_iso:
            return

        connection.execute(
            """
            UPDATE planned_trainings
            SET planned_date = ?
            WHERE id = ?
            """,
            (
                new_date_iso,
                training_id,
            ),
        )


def _ensure_activity_plan_links_table(
    connection: sqlite3.Connection,
) -> None:
    """Crea la tabla que relaciona sesiones realizadas y planificadas."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS activity_plan_links (
            activity_session_id INTEGER PRIMARY KEY,
            planned_training_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (activity_session_id)
                REFERENCES activity_sessions(id)
                ON DELETE CASCADE,
            FOREIGN KEY (planned_training_id)
                REFERENCES planned_trainings(id)
                ON DELETE CASCADE
        )
        """
    )


def save_activity_plan_link(
    activity_session_id: int,
    planned_training_id: int | None,
) -> None:
    """Guarda o elimina el vínculo entre actividad y plan."""
    with get_connection() as connection:
        _ensure_activity_plan_links_table(connection)

        if planned_training_id is None:
            connection.execute(
                """
                DELETE FROM activity_plan_links
                WHERE activity_session_id = ?
                """,
                (activity_session_id,),
            )
            return

        connection.execute(
            """
            INSERT INTO activity_plan_links (
                activity_session_id,
                planned_training_id
            )
            VALUES (?, ?)
            ON CONFLICT(activity_session_id)
            DO UPDATE SET
                planned_training_id = excluded.planned_training_id
            """,
            (
                activity_session_id,
                planned_training_id,
            ),
        )


def get_linked_planned_training(
    activity_session_id: int,
) -> dict[str, Any] | None:
    """Obtiene el entrenamiento planificado vinculado a una actividad."""
    with get_connection() as connection:
        _ensure_activity_plan_links_table(connection)

        row = connection.execute(
            """
            SELECT planned_trainings.*
            FROM planned_trainings
            INNER JOIN activity_plan_links
                ON planned_trainings.id =
                   activity_plan_links.planned_training_id
            WHERE activity_plan_links.activity_session_id = ?
            """,
            (activity_session_id,),
        ).fetchone()

    return dict(row) if row else None

def delete_planned_training(training_id: int) -> None:
    """Elimina permanentemente una sesión planificada.

    Se usa solo para corregir duplicados o errores de introducción de datos.
    Para "no voy a poder hacerla hoy", usa mover o cancelar en lugar de borrar.
    """
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM planned_trainings WHERE id = ?",
            (training_id,),
        )

        if cursor.rowcount == 0:
            raise ValueError(
                "No se ha encontrado la sesión planificada a eliminar."
            )

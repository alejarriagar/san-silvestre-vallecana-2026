"""Elimina copias duplicadas del plan inicial conservando una sesión."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DATABASE_PATH = Path("data") / "training.db"


def main() -> None:
    """Conserva la sesión con menor id de cada duplicado."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    links_table_exists = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'activity_plan_links'
        """
    ).fetchone() is not None

    duplicate_groups = connection.execute(
        """
        SELECT
            planned_date,
            description,
            GROUP_CONCAT(id) AS ids,
            COUNT(*) AS total
        FROM planned_trainings
        GROUP BY planned_date, description
        HAVING COUNT(*) > 1
        """
    ).fetchall()

    deleted_rows = 0

    for group in duplicate_groups:
        training_ids = sorted(
            int(training_id)
            for training_id in group["ids"].split(",")
        )

        canonical_id = training_ids[0]

        for duplicate_id in training_ids[1:]:
            if links_table_exists:
                connection.execute(
                    """
                    UPDATE activity_plan_links
                    SET planned_training_id = ?
                    WHERE planned_training_id = ?
                    """,
                    (
                        canonical_id,
                        duplicate_id,
                    ),
                )

            connection.execute(
                """
                DELETE FROM planned_trainings
                WHERE id = ?
                """,
                (duplicate_id,),
            )

            deleted_rows += 1

    connection.commit()

    remaining_count = connection.execute(
        "SELECT COUNT(*) FROM planned_trainings"
    ).fetchone()[0]

    connection.close()

    print(f"Copias eliminadas: {deleted_rows}")
    print(f"Sesiones planificadas restantes: {remaining_count}")


if __name__ == "__main__":
    main()

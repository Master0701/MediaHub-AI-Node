from sqlalchemy import inspect, text

from app.database import engine


REQUIRED_COLUMNS = {
    "progress": "INTEGER NOT NULL DEFAULT 0",
    "result": "TEXT",
    "error": "TEXT",
    "started": "DATETIME",
    "finished": "DATETIME",
    "updated": "DATETIME",
}


def migrate() -> None:
    inspector = inspect(engine)

    if "jobs" not in inspector.get_table_names():
        raise RuntimeError(
            "Die Tabelle 'jobs' wurde nicht gefunden."
        )

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("jobs")
    }

    added_columns: list[str] = []

    with engine.begin() as connection:
        for column_name, column_definition in REQUIRED_COLUMNS.items():
            if column_name in existing_columns:
                continue

            connection.execute(
                text(
                    f"ALTER TABLE jobs "
                    f"ADD COLUMN {column_name} "
                    f"{column_definition}"
                )
            )
            added_columns.append(column_name)

    if added_columns:
        print(
            "Neue Job-Spalten angelegt: "
            + ", ".join(added_columns)
        )
    else:
        print("Die Job-Tabelle ist bereits aktuell.")


if __name__ == "__main__":
    migrate()

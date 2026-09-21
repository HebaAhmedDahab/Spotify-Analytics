import os

import psycopg
from dotenv import load_dotenv

load_dotenv()


def _get_table_columns(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'recent_tracks'
            ORDER BY ordinal_position
            """
        )
        return {row[0] for row in cursor.fetchall()}


def _ensure_image_column(connection):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "ALTER TABLE recent_tracks ADD COLUMN IF NOT EXISTS image_url TEXT"
            )
        connection.commit()
    except psycopg.errors.InsufficientPrivilege:
        connection.rollback()
        print("Skipping image_url schema migration: database user is not table owner")


def _has_unique_constraint(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                WHERE t.relname = 'recent_tracks'
                  AND c.contype IN ('p', 'u')
            )
            """
        )
        return bool(cursor.fetchone()[0])


def load_to_postgresql(df):
    connection = psycopg.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )
    try:
        _ensure_image_column(connection)
        available_columns = _get_table_columns(connection)
        expected_columns = [
            "track_id",
            "track",
            "artist",
            "album",
            "played_at",
            "played_date",
            "played_hour",
            "day_of_week",
            "duration_minutes",
            "image_url",
        ]
        insert_columns = [col for col in expected_columns if col in available_columns]

        if not insert_columns:
            raise ValueError("No compatible columns found in recent_tracks table")

        conflict_clause = ""
        if _has_unique_constraint(connection):
            conflict_clause = " ON CONFLICT DO NOTHING"

        with connection.cursor() as cursor:
            for _, row in df.iterrows():
                values = [row.get(column) for column in insert_columns]
                placeholders = ", ".join(["%s"] * len(values))
                column_sql = ", ".join(insert_columns)
                cursor.execute(
                    f"""
                    INSERT INTO recent_tracks ({column_sql})
                    VALUES ({placeholders}){conflict_clause};
                    """,
                    values,
                )

        connection.commit()
        print("Data loaded successfully into PostgreSQL!")

    except Exception as error:
        connection.rollback()
        print(f"Error loading data: {error}")
        raise
    finally:
        connection.close()
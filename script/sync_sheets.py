import os
from pathlib import Path

import gspread
import psycopg
from dotenv import load_dotenv
from google.oauth2 import service_account

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def get_db_connection():
    """Create a PostgreSQL connection using values from .env."""
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


def get_sheet_client():
    """Authenticate with the Google service account and open the spreadsheet."""
    spreadsheet_key = os.getenv("SPREADSHEETS_KEY")
    if not spreadsheet_key:
        raise ValueError("SPREADSHEETS_KEY is missing in .env")

    credentials_path = os.getenv(
        "GOOGLE_SERVICE_ACCOUNT_PATH",
        str(PROJECT_ROOT / "config" / "google_credentials.json"),
    )

    credentials = service_account.Credentials.from_service_account_file(
        credentials_path,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )

    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(spreadsheet_key)
    return spreadsheet


def fetch_recent_tracks(limit=None):
    """Pull the latest rows from the PostgreSQL recent_tracks table."""
    query = """
        SELECT track_id, track, artist, album, played_at,
               played_date, played_hour, day_of_week, duration_minutes
        FROM recent_tracks
        ORDER BY played_at DESC
    """

    params = ()
    if limit is not None:
        query += " LIMIT %s"
        params = (limit,)

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

    headers = [
        "track_id",
        "track",
        "artist",
        "album",
        "played_at",
        "played_date",
        "played_hour",
        "day_of_week",
        "duration_minutes",
    ]
    values = [
        [
            row[0],
            row[1],
            row[2],
            row[3],
            row[4].strftime("%Y-%m-%d %H:%M:%S") if hasattr(row[4], "strftime") else row[4],
            row[5],
            row[6],
            row[7],
            row[8],
        ]
        for row in rows
    ]

    return [headers] + values


def sync_to_sheets(worksheet_name="recent_tracks", limit=None):
    """Write the current Postgres data into the target Google Sheet."""
    spreadsheet = get_sheet_client()

    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=worksheet_name,
            rows="1000",
            cols="10",
        )

    rows = fetch_recent_tracks(limit=limit)

    worksheet.clear()
    worksheet.update("A1", rows, value_input_option="RAW")
    worksheet.freeze(rows=1)

    print(f"Synced {len(rows) - 1} rows to sheet '{worksheet_name}'")
    return {
        "worksheet": worksheet_name,
        "rows_synced": len(rows) - 1,
    }


if __name__ == "__main__":
    sync_to_sheets()
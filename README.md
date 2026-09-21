# Spotify Listening Analytics

A small Spotify data pipeline that extracts recently played tracks, transforms them into analytics-ready records, stores them in PostgreSQL, and displays listening insights in a Dash dashboard.

## Features

- Spotify recently-played track extraction using a refresh token
- Incremental ingestion using `config/last_played_at.txt`
- Transformation into dates, hours, weekdays, and duration metrics
- PostgreSQL loading with duplicate protection when the database constraint is available
- Dash dashboard with listening KPIs, top songs, top artists, activity by date, and activity by hour
- Optional Google Sheets synchronization
- Airflow DAGs for scheduled ingestion and Sheets synchronization

## Project Layout

```text
dags/       Airflow DAG definitions
dashboard/  Dash application
script/     Extract, transform, load, and sync scripts
sql/        PostgreSQL schema
test/       Tests
```

Generated data, credentials, local databases, and runtime logs are intentionally excluded from Git with `.gitignore`.

## Requirements

- Python 3.11+
- PostgreSQL
- Spotify Developer application credentials
- Optional: Apache Airflow and a Google service account for scheduled jobs and Sheets sync

Install the Python dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirments.txt
```

## Configuration

Create a `.env` file in the project root. Never commit it.

```env
CLIENT_ID=your_spotify_client_id
CLIENT_SECRET=your_spotify_client_secret
REDIRECT_URI=your_spotify_redirect_uri
REFRESH_TOKEN=your_spotify_refresh_token

PROJECT_ROOT=/absolute/path/to/spotify_analytics
OUTPUT_FOLDER=/absolute/path/to/spotify_analytics/bronze

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=spotifyanalytics
POSTGRES_USER=spotify_user
POSTGRES_PASSWORD=your_database_password

# Optional Google Sheets sync
SPREADSHEETS_KEY=your_google_spreadsheet_id
GOOGLE_SERVICE_ACCOUNT_PATH=/absolute/path/to/google_credentials.json
```

Create the database tables with `sql/schema.sql`, then make sure the Spotify refresh token has permission to read recently played tracks.

## Run the Pipeline

Run an incremental refresh manually:

```bash
source .venv/bin/activate
export PROJECT_ROOT="$PWD"
export OUTPUT_FOLDER="$PWD/bronze"
python script/extract.py
python script/transform.py
```

Run the dashboard:

```bash
source .venv/bin/activate
python dashboard/app.py
```

Open <http://localhost:8050/> in a browser.

The Spotify endpoint only returns plays recorded after the checkpoint in `config/last_played_at.txt`. Play a track in Spotify before running the refresh when no new items are returned.

## Airflow

The DAG file defines:

- `spotify_ingest_pipeline`, scheduled every 15 minutes
- `spotify_sheets_sync`, scheduled every 16 minutes

Copy the project into the Airflow DAGs location or configure Airflow to load this directory, then start the scheduler and webserver using your local Airflow setup.

## Security

Do not commit Spotify client secrets, refresh tokens, database passwords, Google credentials, or generated listening history. If a secret has been exposed, revoke and regenerate it before publishing the repository.
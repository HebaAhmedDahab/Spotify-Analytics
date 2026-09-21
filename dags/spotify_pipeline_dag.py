from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def run_extract():
    extract_path = PROJECT_ROOT / "script" / "extract.py"
    subprocess.run([sys.executable, str(extract_path)], check=True)


def run_transform():
    transform_path = PROJECT_ROOT / "script" / "transform.py"
    subprocess.run([sys.executable, str(transform_path)], check=True)


def run_sync_to_sheets():
    sync_path = PROJECT_ROOT / "script" / "sync_sheets.py"
    subprocess.run([sys.executable, str(sync_path)], check=True)


with DAG(
    dag_id="spotify_ingest_pipeline",
    description="Extract Spotify recent tracks and store them in Postgres every 15 minutes.",
    start_date=datetime(2026, 9, 9),
    schedule="*/15 * * * *",
    catchup=False,
    tags=["spotify", "analytics", "postgres"],
) as ingest_dag:
    extract_task = PythonOperator(
        task_id="extract_recent_tracks",
        python_callable=run_extract,
    )

    transform_task = PythonOperator(
        task_id="transform_recent_tracks",
        python_callable=run_transform,
    )

    extract_task >> transform_task


with DAG(
    dag_id="spotify_sheets_sync",
    description="Push Postgres recent tracks into Google Sheets every 16 minutes with a 1-minute buffer.",
    start_date=datetime(2026, 9, 9),
    schedule="*/16 * * * *",
    catchup=False,
    tags=["spotify", "analytics", "sheets"],
) as sync_dag:
    sync_task = PythonOperator(
        task_id="sync_recent_tracks_to_sheets",
        python_callable=run_sync_to_sheets,
    )

    sync_task

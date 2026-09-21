import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()


def transform():
    # Read the latest JSON file and convert it into a DataFrame
    project_root = Path(os.getenv("PROJECT_ROOT"))
    raw_folder = project_root / "raw"
    json_files = list(raw_folder.glob("recent_tracks_*.json"))

    if not json_files:
        raise FileNotFoundError("No JSON files found in Raw folder.")

    filename = max(json_files, key=lambda file: file.stat().st_mtime)

    print(f"Reading file: {filename}")

    with open(filename, "r") as file:
        data = json.load(file)

    tracks = []

    for item in data["items"]:
        track = item["track"]
        album = track["album"]
        artist = album["artists"][0]
        played_at = item["played_at"]
        image_url = None

        if album.get("images"):
            image_url = album["images"][0].get("url")

        tracks.append({
            "track_id": track["id"],
            "track": track["name"],
            "artist": artist["name"],
            "album": album["name"],
            "played_at": played_at,
            "duration_ms": track.get("duration_ms", 0),
            "image_url": image_url,
        })

    # Cleaning and validation stage

    df = pd.DataFrame(tracks)

    df["played_at"] = pd.to_datetime(df["played_at"], utc=True)
    df["played_date"] = df["played_at"].dt.strftime("%Y-%m-%d")
    df["played_hour"] = df["played_at"].dt.hour
    df["day_of_week"] = df["played_at"].dt.day_name()
    df["duration_minutes"] = (df["duration_ms"] / 60000).round(2)
    df["played_at"] = df["played_at"].dt.strftime("%Y-%m-%d %H:%M:%S")

    required_columns = [
        "track_id",
        "track",
        "artist",
        "album",
        "played_at",
        "played_date",
        "played_hour",
        "day_of_week",
        "duration_minutes",
        "image_url"
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing Columns: {missing_columns}"
        )

    if df[required_columns].isnull().any().any():
        raise ValueError(
            "Missing value found in required columns"
        )

    print("Validation completed successfully!")

    # Save CSV as backup

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    output_folder = Path(os.getenv("OUTPUT_FOLDER"))

    output_file = (
        output_folder / f"recent_tracks_{timestamp}.csv"
    )

    df.to_csv(output_file, index=False)

    print("Transform completed successfully!")
    print(f"File saved: {output_file}")

    from load import load_to_postgresql
    load_to_postgresql(df)

    return df
    
if __name__ == "__main__":
    transform()
from get_access_token import get_access_token
import requests
import json
from datetime import datetime
import os
from pathlib import Path

def extract():
    project_root = Path(os.getenv("PROJECT_ROOT"))
    raw_folder = project_root / "raw"
    access_token = get_access_token()
    headers = {
    "Authorization": f"Bearer {access_token}"
    }
    URL = "https://api.spotify.com/v1/me/player/recently-played"
    last_played_file = project_root / "config" / "last_played_at.txt"
    with open(last_played_file, "r") as file:
        last_played_at = file.read().strip()
    
    last_played_at_ms = int(
        datetime.fromisoformat(
            last_played_at.replace("Z", "+00:00")
        ).timestamp() * 1000
    )   
    params = {"after": last_played_at_ms}
    response = requests.get(URL, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    all_items = data["items"]
    next_url = data.get("next")

    while next_url:
        next_response = requests.get(next_url, headers=headers)
        next_response.raise_for_status()
        next_data = next_response.json()
        all_items.extend(next_data["items"])
        next_url = next_data.get("next")
    print(f"Total item collected: {len(all_items)}")

    if not all_items:
        print("No new tracks found.")
        return

    latest_played_at = max(item["played_at"] for item in all_items)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_folder = project_root / "raw"
    filename = raw_folder / f"recent_tracks_{timestamp}.json"

    with open(filename, "w") as file:
        data["items"] = all_items
        json.dump(data, file, indent=4)

    with open(last_played_file, "w") as file:
        file.write(latest_played_at)

    print("Checkpoint updated successfully!")
    print("Extract completed successfully!")
    print(f"File saved: {filename}")
    print(f"Latest played_at: {latest_played_at}")

if __name__ == "__main__":
    extract()
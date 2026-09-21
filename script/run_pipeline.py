import os
from pathlib import Path
import subprocess
import sys
from dotenv import load_dotenv

load_dotenv()
project_root = os.getenv("PROJECT_ROOT")
extract_script = Path(project_root) / "script" / "extract.py"
transform_script = Path(project_root) / "script" / "transform.py"
print("Starting Spotify Pipeline....")

print("\n--- Extracting Data ---\n")
subprocess.run([sys.executable, extract_script], check=True)

print("\n--- Transforming Data ---\n")
subprocess.run([sys.executable, transform_script], check=True)

print("\n Pipeline Completed Successfully!")

from pathlib import Path
import os

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database path
DB_PATH = os.getenv("DB_PATH", str(DATA_DIR / "causaganha.duckdb"))

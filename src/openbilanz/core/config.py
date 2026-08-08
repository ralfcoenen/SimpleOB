from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]


DATA_DIR = BASE_DIR / "data"


DATABASE_FILE = DATA_DIR / "openbilanz.db"


DATABASE_URL = f"sqlite:///{DATABASE_FILE}"


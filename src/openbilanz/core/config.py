"""Anwendungskonfiguration von OpenBilanz."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]

DEFAULT_DATA_DIR = BASE_DIR / "data"

DEFAULT_CONFIG_FILE = (
    DEFAULT_DATA_DIR
    / "config.toml"
)


@dataclass(frozen=True, slots=True)
class ApplicationConfig:
    """Technische Konfiguration der OpenBilanz-Anwendung."""

    data_dir: Path
    database_file: Path
    taxonomy_dir: Path
    config_file: Path

    @property
    def database_url(self) -> str:
        """Liefert die SQLAlchemy-URL der SQLite-Datenbank."""

        return f"sqlite:///{self.database_file}"


def default_config() -> ApplicationConfig:
    """Erzeugt die Standardkonfiguration für die Entwicklung."""

    return ApplicationConfig(
        data_dir=DEFAULT_DATA_DIR,
        database_file=(
            DEFAULT_DATA_DIR
            / "openbilanz.db"
        ),
        taxonomy_dir=(
            DEFAULT_DATA_DIR
            / "taxonomy"
        ),
        config_file=DEFAULT_CONFIG_FILE,
    )


def load_config(
    config_file: Path | None = None,
) -> ApplicationConfig:
    """Lädt die Anwendungskonfiguration aus einer TOML-Datei."""

    defaults = default_config()

    path = (
        config_file
        if config_file is not None
        else defaults.config_file
    )

    if not path.is_file():
        return ApplicationConfig(
            data_dir=defaults.data_dir,
            database_file=defaults.database_file,
            taxonomy_dir=defaults.taxonomy_dir,
            config_file=path,
        )

    with path.open("rb") as file:
        data = tomllib.load(file)

    application = data.get(
        "application",
        {},
    )

    database = data.get(
        "database",
        {},
    )

    taxonomy = data.get(
        "taxonomy",
        {},
    )

    data_dir = Path(
        application.get(
            "data_dir",
            str(defaults.data_dir),
        )
    ).expanduser()

    database_file = Path(
        database.get(
            "file",
            str(
                data_dir
                / "openbilanz.db"
            ),
        )
    ).expanduser()

    taxonomy_dir = Path(
        taxonomy.get(
            "root",
            str(
                data_dir
                / "taxonomy"
            ),
        )
    ).expanduser()

    return ApplicationConfig(
        data_dir=data_dir,
        database_file=database_file,
        taxonomy_dir=taxonomy_dir,
        config_file=path,
    )


# ---------------------------------------------------------
# Übergangskompatibilität
# ---------------------------------------------------------

_current_config = load_config()

DATA_DIR = _current_config.data_dir
DATABASE_FILE = _current_config.database_file
DATABASE_URL = _current_config.database_url
TAXONOMY_DIR = _current_config.taxonomy_dir


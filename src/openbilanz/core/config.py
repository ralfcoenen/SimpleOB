"""Anwendungskonfiguration von OpenBilanz."""

from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]

DEFAULT_DATA_DIR = BASE_DIR / "data"

DEFAULT_CONFIG_FILE = DEFAULT_DATA_DIR / "config.toml"

APPLICATION_DATA_DIRECTORY_NAME = "SimpleOB"


@dataclass(frozen=True, slots=True)
class ApplicationConfig:
    """Technische Konfiguration der OpenBilanz-Anwendung."""

    data_dir: Path
    database_file: Path
    taxonomy_dir: Path
    config_file: Path
    eric_lib_dir: Path | None = None
    eric_manufacturer_id: str | None = None
    eric_data_supplier: str | None = None
    eric_certificate_path: Path | None = None
    eric_certificate_pin: str | None = None

    @property
    def database_url(self) -> str:
        """Liefert die SQLAlchemy-URL der SQLite-Datenbank."""

        return f"sqlite:///{self.database_file}"


def default_config() -> ApplicationConfig:
    """Erzeugt die Standardkonfiguration für die Entwicklung."""

    return _default_config_for_data_dir(
        DEFAULT_DATA_DIR
    )


def desktop_application_data_dir() -> Path:
    """Liefert das Benutzerdatenverzeichnis der installierten Anwendung."""

    if sys.platform == "darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / APPLICATION_DATA_DIRECTORY_NAME
        )

    if sys.platform == "win32":
        local_app_data = os.environ.get(
            "LOCALAPPDATA"
        )

        if not local_app_data:
            raise RuntimeError(
                "LOCALAPPDATA ist unter Windows nicht gesetzt."
            )

        return (
            Path(local_app_data)
            / APPLICATION_DATA_DIRECTORY_NAME
        )

    return (
        Path.home()
        / ".local"
        / "share"
        / APPLICATION_DATA_DIRECTORY_NAME
    )


def bundled_eric_lib_dir() -> Path | None:
    """Liefert das ERiC-lib-Verzeichnis der gebündelten Anwendung."""

    if not getattr(sys, "frozen", False):
        return None

    bundle_dir_value = getattr(sys, "_MEIPASS", None)

    if not bundle_dir_value:
        return None

    lib_dir = (
        Path(bundle_dir_value)
        / "eric"
        / "lib"
    )

    if not lib_dir.is_dir():
        return None

    return lib_dir


def installed_config() -> ApplicationConfig:
    """Erzeugt die Standardkonfiguration der installierten Anwendung."""

    config = _default_config_for_data_dir(
        desktop_application_data_dir()
    )

    return ApplicationConfig(
        data_dir=config.data_dir,
        database_file=config.database_file,
        taxonomy_dir=config.taxonomy_dir,
        config_file=config.config_file,
        eric_lib_dir=bundled_eric_lib_dir(),
    )


def load_config(
    config_file: Path | None = None,
    *,
    defaults: ApplicationConfig | None = None,
) -> ApplicationConfig:
    """Lädt die Anwendungskonfiguration aus einer TOML-Datei."""

    effective_defaults = (
        defaults
        if defaults is not None
        else default_config()
    )

    path = (
        config_file
        if config_file is not None
        else effective_defaults.config_file
    )

    if not path.is_file():
        return ApplicationConfig(
            data_dir=effective_defaults.data_dir,
            database_file=effective_defaults.database_file,
            taxonomy_dir=effective_defaults.taxonomy_dir,
            config_file=path,
            eric_lib_dir=effective_defaults.eric_lib_dir,
            eric_manufacturer_id=effective_defaults.eric_manufacturer_id,
            eric_data_supplier=effective_defaults.eric_data_supplier,
            eric_certificate_path=effective_defaults.eric_certificate_path,
            eric_certificate_pin=effective_defaults.eric_certificate_pin,
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

    eric = data.get(
        "eric",
        {},
    )

    data_dir = Path(
        application.get(
            "data_dir",
            str(effective_defaults.data_dir),
        )
    ).expanduser()

    database_file = Path(
        database.get(
            "file",
            str(data_dir / "openbilanz.db"),
        )
    ).expanduser()

    taxonomy_dir = Path(
        taxonomy.get(
            "root",
            str(data_dir / "taxonomy"),
        )
    ).expanduser()

    eric_lib_dir_value = eric.get(
        "lib_dir",
    )
    eric_lib_dir = (
        Path(eric_lib_dir_value).expanduser()
        if eric_lib_dir_value
        else None
    )

    eric_manufacturer_id_value = eric.get(
        "manufacturer_id",
    )
    eric_manufacturer_id = (
        str(eric_manufacturer_id_value).strip()
        if eric_manufacturer_id_value is not None
        else None
    )

    if not eric_manufacturer_id:
        eric_manufacturer_id = None

    eric_data_supplier_value = eric.get(
        "data_supplier",
    )
    eric_data_supplier = (
        str(eric_data_supplier_value).strip()
        if eric_data_supplier_value is not None
        else None
    )

    if not eric_data_supplier:
        eric_data_supplier = None

    eric_certificate_path_value = eric.get(
        "certificate_path",
    )
    eric_certificate_path = (
        Path(eric_certificate_path_value).expanduser()
        if eric_certificate_path_value
        else None
    )

    eric_certificate_pin_value = eric.get(
        "certificate_pin",
    )
    eric_certificate_pin = (
        str(eric_certificate_pin_value)
        if eric_certificate_pin_value is not None
        else None
    )

    if not eric_certificate_pin:
        eric_certificate_pin = None

    return ApplicationConfig(
        data_dir=data_dir,
        database_file=database_file,
        taxonomy_dir=taxonomy_dir,
        config_file=path,
        eric_lib_dir=eric_lib_dir,
        eric_manufacturer_id=eric_manufacturer_id,
        eric_data_supplier=eric_data_supplier,
        eric_certificate_path=eric_certificate_path,
        eric_certificate_pin=eric_certificate_pin,
    )


def load_installed_config() -> ApplicationConfig:
    """Lädt die Konfiguration der installierten Desktop-Anwendung."""

    defaults = installed_config()

    config = load_config(
        defaults.config_file,
        defaults=defaults,
    )

    return ApplicationConfig(
        data_dir=config.data_dir,
        database_file=config.database_file,
        taxonomy_dir=config.taxonomy_dir,
        config_file=config.config_file,
        eric_lib_dir=defaults.eric_lib_dir,
        eric_manufacturer_id=config.eric_manufacturer_id,
        eric_data_supplier=config.eric_data_supplier,
        eric_certificate_path=config.eric_certificate_path,
        eric_certificate_pin=config.eric_certificate_pin,
    )


def prepare_application_data_directories(
    config: ApplicationConfig,
) -> None:
    """Legt die benötigten beschreibbaren Anwendungsverzeichnisse an."""

    config.data_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    config.taxonomy_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

def _default_config_for_data_dir(
    data_dir: Path,
) -> ApplicationConfig:
    return ApplicationConfig(
        data_dir=data_dir,
        database_file=data_dir / "openbilanz.db",
        taxonomy_dir=data_dir / "taxonomy",
        config_file=data_dir / "config.toml",
    )


# ---------------------------------------------------------
# Übergangskompatibilität
# ---------------------------------------------------------

_current_config = load_config()

DATA_DIR = _current_config.data_dir
DATABASE_FILE = _current_config.database_file
DATABASE_URL = _current_config.database_url
TAXONOMY_DIR = _current_config.taxonomy_dir

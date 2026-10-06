"""Anwendungskonfiguration von OpenBilanz."""

from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

from openbilanz.domain.elster_data_supplier import ElsterDataSupplier

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
    eric_data_supplier: str | None = None
    eric_certificate_path: Path | None = None

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
            eric_data_supplier=effective_defaults.eric_data_supplier,
            eric_certificate_path=effective_defaults.eric_certificate_path,
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

    data_supplier = eric.get(
        "data_supplier",
        {},
    )

    if isinstance(data_supplier, str):
        legacy_parts = [
            part.strip()
            for part in data_supplier.split(";")
        ]

        if len(legacy_parts) != 10:
            raise ValueError(
                "Der alte Wert eric.data_supplier "
                "muss aus genau 10 durch Semikolon "
                "getrennten Feldern bestehen."
            )

        eric_data_supplier = ElsterDataSupplier(
            name=legacy_parts[0],
            street=legacy_parts[1],
            house_number=legacy_parts[2],
            house_number_suffix=legacy_parts[3],
            address_addition=legacy_parts[4],
            postal_code=legacy_parts[5],
            city=legacy_parts[6],
            country=legacy_parts[7],
            phone=legacy_parts[8],
            email=legacy_parts[9],
        )

    elif isinstance(data_supplier, dict):
        eric_data_supplier = ElsterDataSupplier(
            name=str(data_supplier.get("name", "")),
            street=str(data_supplier.get("street", "")),
            house_number=str(
                data_supplier.get("house_number", "")
            ),
            house_number_suffix=str(
                data_supplier.get("house_number_suffix", "")
            ),
            address_addition=str(
                data_supplier.get("address_addition", "")
            ),
            postal_code=str(
                data_supplier.get("postal_code", "")
            ),
            city=str(data_supplier.get("city", "")),
            country=str(data_supplier.get("country", "")),
            phone=str(data_supplier.get("phone", "")),
            email=str(data_supplier.get("email", "")),
        )

    else:
        raise ValueError(
            "eric.data_supplier muss eine TOML-Tabelle "
            "oder ein alter Zeichenkettenwert sein."
        )

    if not eric_data_supplier.is_configured:
        eric_data_supplier = None

    eric_certificate_path_value = eric.get(
        "certificate_path",
    )
    eric_certificate_path = (
        Path(eric_certificate_path_value).expanduser()
        if eric_certificate_path_value
        else None
    )

    return ApplicationConfig(
        data_dir=data_dir,
        database_file=database_file,
        taxonomy_dir=taxonomy_dir,
        config_file=path,
        eric_lib_dir=eric_lib_dir,
        eric_data_supplier=eric_data_supplier,
        eric_certificate_path=eric_certificate_path,
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
        eric_data_supplier=config.eric_data_supplier,
        eric_certificate_path=config.eric_certificate_path,
    )


def _remove_legacy_eric_settings(
    lines: list[str],
) -> list[str]:
    """Entfernt veraltete Einträge aus der direkten [eric]-Sektion."""

    legacy_keys = {
        "manufacturer_id",
        "certificate_pin",
        "data_supplier",
    }

    eric_start: int | None = None
    eric_end = len(lines)

    for index, line in enumerate(lines):
        stripped = line.strip()

        if stripped == "[eric]":
            eric_start = index
            continue

        if (
            eric_start is not None
            and index > eric_start
            and stripped.startswith("[")
            and stripped.endswith("]")
        ):
            eric_end = index
            break

    if eric_start is None:
        return lines

    cleaned_lines = list(lines)

    for index in range(
        eric_end - 1,
        eric_start,
        -1,
    ):
        stripped = cleaned_lines[index].strip()
        key, separator, _ = stripped.partition("=")

        if (
            separator
            and key.strip() in legacy_keys
        ):
            del cleaned_lines[index]

    return cleaned_lines


def save_eric_certificate_path(
    config: ApplicationConfig,
    certificate_path: Path,
) -> None:
    """Speichert den Pfad zum ELSTER-Zertifikat in der Konfiguration."""

    certificate_path = Path(
        certificate_path
    ).expanduser()

    config_file = config.config_file
    config_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    certificate_value = str(
        certificate_path
    ).replace("\\", "\\\\").replace('"', '\\"')

    certificate_line = (
        f'certificate_path = "{certificate_value}"'
    )

    if config_file.is_file():
        text = config_file.read_text(
            encoding="utf-8",
        )
    else:
        text = ""

    lines = text.splitlines()
    lines = _remove_legacy_eric_settings(
        lines
    )
    eric_start: int | None = None
    eric_end = len(lines)

    for index, line in enumerate(lines):
        stripped = line.strip()

        if stripped == "[eric]":
            eric_start = index
            continue

        if (
            eric_start is not None
            and index > eric_start
            and stripped.startswith("[")
            and stripped.endswith("]")
        ):
            eric_end = index
            break

    if eric_start is None:
        if lines and lines[-1].strip():
            lines.append("")

        lines.extend(
            (
                "[eric]",
                certificate_line,
            )
        )
    else:
        certificate_index: int | None = None

        for index in range(
            eric_start + 1,
            eric_end,
        ):
            stripped = lines[index].strip()

            if not stripped.startswith(
                "certificate_path"
            ):
                continue

            key, separator, _ = stripped.partition("=")

            if separator and key.strip() == "certificate_path":
                certificate_index = index
                break

        if certificate_index is None:
            lines.insert(
                eric_end,
                certificate_line,
            )
        else:
            lines[certificate_index] = certificate_line

    config_file.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def save_eric_data_supplier(
    config: ApplicationConfig,
    data_supplier: ElsterDataSupplier,
) -> None:
    """Speichert die Daten des ELSTER-Datenlieferanten."""

    if not isinstance(
        data_supplier,
        ElsterDataSupplier,
    ):
        raise TypeError(
            "data_supplier muss ein ElsterDataSupplier sein."
        )

    if not data_supplier.is_configured:
        raise ValueError(
            "Der ELSTER-Datenlieferant ist nicht konfiguriert."
        )

    config_file = config.config_file
    config_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if config_file.is_file():
        text = config_file.read_text(
            encoding="utf-8",
        )
    else:
        text = ""

    lines = text.splitlines()
    lines = _remove_legacy_eric_settings(
        lines
    )

    section_name = "[eric.data_supplier]"
    section_start: int | None = None
    section_end = len(lines)

    for index, line in enumerate(lines):
        stripped = line.strip()

        if stripped == section_name:
            section_start = index
            continue

        if (
            section_start is not None
            and index > section_start
            and stripped.startswith("[")
            and stripped.endswith("]")
        ):
            section_end = index
            break

    if section_start is not None:
        del lines[
            section_start:section_end
        ]

        while (
            section_start > 0
            and section_start <= len(lines)
            and not lines[section_start - 1].strip()
        ):
            del lines[section_start - 1]
            section_start -= 1

    def toml_string(value: str) -> str:
        escaped = (
            value
            .replace("\\", "\\\\")
            .replace('"', '\\"')
        )
        return f'"{escaped}"'

    supplier_lines = [
        section_name,
        f"name = {toml_string(data_supplier.name)}",
        f"street = {toml_string(data_supplier.street)}",
        (
            "house_number = "
            f"{toml_string(data_supplier.house_number)}"
        ),
        (
            "house_number_suffix = "
            f"{toml_string(data_supplier.house_number_suffix)}"
        ),
        (
            "address_addition = "
            f"{toml_string(data_supplier.address_addition)}"
        ),
        (
            "postal_code = "
            f"{toml_string(data_supplier.postal_code)}"
        ),
        f"city = {toml_string(data_supplier.city)}",
        f"country = {toml_string(data_supplier.country)}",
        f"phone = {toml_string(data_supplier.phone)}",
        f"email = {toml_string(data_supplier.email)}",
    ]

    if lines and lines[-1].strip():
        lines.append("")

    lines.extend(
        supplier_lines
    )

    config_file.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
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

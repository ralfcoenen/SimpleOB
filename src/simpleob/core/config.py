"""Anwendungskonfiguration von OpenBilanz."""

from __future__ import annotations

import os
import stat
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

from simpleob.domain.elster_data_supplier import ElsterDataSupplier

BASE_DIR = Path(__file__).resolve().parents[3]

DEFAULT_DATA_DIR = BASE_DIR / "data"

DEFAULT_CONFIG_FILE = DEFAULT_DATA_DIR / "config.toml"

APPLICATION_DATA_DIRECTORY_NAME = "SimpleOB"


@dataclass(frozen=True, slots=True)
class ApplicationConfig:
    """Konfiguration der SimpleOB-Anwendung."""

    data_dir: Path
    database_file: Path
    taxonomy_dir: Path
    config_file: Path

    eric_lib_dir: Path | None = None
    eric_data_supplier: ElsterDataSupplier | None = None
    eric_certificate_path: Path | None = None

    database_url_override: str | None = None

    @property
    def database_url(self) -> str:
        """Liefert die konfigurierte SQLAlchemy-Datenbank-URL."""

        if self.database_url_override is not None:
            return self.database_url_override

        return f"sqlite:///{self.database_file}"


class ConfigurationFileError(Exception):
    """Eine Konfigurationsdatei kann nicht sicher gelesen oder geparst werden."""

    def __init__(self, path: Path, message: str) -> None:
        self.path = path
        self.message = message
        super().__init__(f"{path}: {message}")


class ConfigurationSyntaxError(ConfigurationFileError):
    """Die Konfigurationsdatei enthält ungültige TOML-Syntax."""


class ConfigurationReadError(ConfigurationFileError):
    """Die Konfigurationsdatei ist nicht lesbar oder keine reguläre Datei."""


class ConfigurationValueError(ConfigurationFileError):
    """Ein anderer Konfigurationswert ist ungültig."""


class InvalidDatabaseConfigurationError(ValueError):
    """Die übrige Konfiguration ist lesbar, aber die Datenbank-URL ungültig."""

    def __init__(
        self,
        path: Path,
        message: str,
        recovery_config: ApplicationConfig,
    ) -> None:
        self.path = path
        self.message = message
        self.recovery_config = recovery_config
        super().__init__(f"{path}: {message}")


@property
def database_url(self) -> str:
    """Liefert die konfigurierte SQLAlchemy-Datenbank-URL."""

    if self.database_url_override is not None:
        return self.database_url_override

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

    try:
        file_mode = path.stat().st_mode
    except FileNotFoundError:
        return ApplicationConfig(
            data_dir=effective_defaults.data_dir,
            database_file=effective_defaults.database_file,
            taxonomy_dir=effective_defaults.taxonomy_dir,
            config_file=path,
            database_url_override=effective_defaults.database_url_override,
            eric_lib_dir=effective_defaults.eric_lib_dir,
            eric_data_supplier=effective_defaults.eric_data_supplier,
            eric_certificate_path=effective_defaults.eric_certificate_path,
        )
    except OSError as exc:
        raise ConfigurationReadError(
            path,
            f"Datei- oder Berechtigungsfehler beim Zugriff: {exc.strerror or exc}",
        ) from exc

    if not stat.S_ISREG(file_mode):
        raise ConfigurationReadError(
            path,
            "Der Konfigurationspfad ist keine reguläre Datei.",
        )

    try:
        with path.open("rb") as file:
            data = tomllib.load(file)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigurationSyntaxError(
            path,
            f"TOML-Syntaxfehler: {exc}",
        ) from exc
    except OSError as exc:
        raise ConfigurationReadError(
            path,
            f"Datei- oder Berechtigungsfehler beim Lesen: {exc.strerror or exc}",
        ) from exc

    application = _configuration_table(data, "application", path)
    database = _configuration_table(data, "database", path)
    taxonomy = _configuration_table(data, "taxonomy", path)
    eric = _configuration_table(data, "eric", path)

    database_url_override = database.get("url")
    invalid_database_message: str | None = None
    if database_url_override is not None:
        if not isinstance(database_url_override, str):
            invalid_database_message = "database.url muss eine Zeichenkette sein."
            database_url_override = None
        else:
            database_url_override = database_url_override.strip()
            if not database_url_override:
                invalid_database_message = "database.url darf nicht leer sein."
                database_url_override = None
            elif not database_url_override.startswith(
                ("sqlite:///", "postgresql+psycopg://")
            ):
                invalid_database_message = (
                    "Nicht unterstützter Datenbanktyp. Unterstützt werden "
                    "SQLite und PostgreSQL mit psycopg."
                )
                database_url_override = None
            else:
                from sqlalchemy.engine import make_url
                from sqlalchemy.exc import ArgumentError

                try:
                    parsed_database_url = make_url(database_url_override)
                except (ArgumentError, TypeError, ValueError):
                    invalid_database_message = (
                        "database.url ist keine gültige Datenbank-URL."
                    )
                    database_url_override = None
                else:
                    if parsed_database_url.password is not None:
                        invalid_database_message = (
                            "database.url darf kein Passwort enthalten. "
                            "Das Passwort wird beim Verbinden abgefragt."
                        )
                        database_url_override = None

    data_dir = _configured_path(
        application,
        "data_dir",
        str(effective_defaults.data_dir),
        path,
    )
    database_file = _configured_path(
        database,
        "file",
        str(data_dir / "openbilanz.db"),
        path,
    )
    taxonomy_dir = _configured_path(
        taxonomy,
        "root",
        str(data_dir / "taxonomy"),
        path,
    )

    eric_lib_dir_value = eric.get(
        "lib_dir",
    )
    eric_lib_dir = None
    if eric_lib_dir_value:
        eric_lib_dir = _configured_path(
            eric,
            "lib_dir",
            "",
            path,
        )

    data_supplier = eric.get(
        "data_supplier",
        {},
    )

    if isinstance(data_supplier, str):
        legacy_parts = [part.strip() for part in data_supplier.split(";")]

        if len(legacy_parts) != 10:
            raise ConfigurationValueError(
                path,
                "Der alte Wert eric.data_supplier muss aus genau 10 durch "
                "Semikolon getrennten Feldern bestehen.",
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
            house_number=str(data_supplier.get("house_number", "")),
            house_number_suffix=str(data_supplier.get("house_number_suffix", "")),
            address_addition=str(data_supplier.get("address_addition", "")),
            postal_code=str(data_supplier.get("postal_code", "")),
            city=str(data_supplier.get("city", "")),
            country=str(data_supplier.get("country", "")),
            phone=str(data_supplier.get("phone", "")),
            email=str(data_supplier.get("email", "")),
        )

    else:
        raise ConfigurationValueError(
            path,
            "eric.data_supplier muss eine TOML-Tabelle oder ein alter "
            "Zeichenkettenwert sein.",
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

    eric_certificate_path = None
    if eric_certificate_path_value:
        eric_certificate_path = _configured_path(
            eric,
            "certificate_path",
            "",
            path,
        )

    config = ApplicationConfig(
        data_dir=data_dir,
        database_file=database_file,
        taxonomy_dir=taxonomy_dir,
        config_file=path,
        database_url_override=database_url_override,
        eric_lib_dir=eric_lib_dir,
        eric_data_supplier=eric_data_supplier,
        eric_certificate_path=eric_certificate_path,
    )

    if invalid_database_message is not None:
        raise InvalidDatabaseConfigurationError(
            path,
            invalid_database_message,
            config,
        )

    return config


def _configuration_table(
    data: dict[str, object],
    name: str,
    path: Path,
) -> dict[str, object]:
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise ConfigurationValueError(
            path,
            f"Der Abschnitt [{name}] muss eine TOML-Tabelle sein.",
        )
    return value


def _configured_path(
    section: dict[str, object],
    key: str,
    default: str,
    config_file: Path,
) -> Path:
    value = section.get(key, default)
    if not isinstance(value, str) or not value:
        raise ConfigurationValueError(
            config_file,
            f"Der Konfigurationswert {key!r} muss ein nichtleerer Pfad sein.",
        )
    try:
        return Path(value).expanduser()
    except (TypeError, ValueError) as exc:
        raise ConfigurationValueError(
            config_file,
            f"Der Konfigurationswert {key!r} ist kein gültiger Pfad.",
        ) from exc


def load_installed_config() -> ApplicationConfig:
    """Lädt die Konfiguration der installierten Desktop-Anwendung."""

    defaults = installed_config()

    try:
        config = load_config(
            defaults.config_file,
            defaults=defaults,
        )
    except InvalidDatabaseConfigurationError as exc:
        recovery_config = ApplicationConfig(
            data_dir=exc.recovery_config.data_dir,
            database_file=exc.recovery_config.database_file,
            taxonomy_dir=exc.recovery_config.taxonomy_dir,
            config_file=exc.recovery_config.config_file,
            database_url_override=None,
            eric_lib_dir=defaults.eric_lib_dir,
            eric_data_supplier=exc.recovery_config.eric_data_supplier,
            eric_certificate_path=exc.recovery_config.eric_certificate_path,
        )
        raise InvalidDatabaseConfigurationError(
            exc.path,
            exc.message,
            recovery_config,
        ) from exc

    return ApplicationConfig(
        data_dir=config.data_dir,
        database_file=config.database_file,
        taxonomy_dir=config.taxonomy_dir,
        config_file=config.config_file,
        database_url_override=config.database_url_override,
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

def save_database_configuration(
    config: ApplicationConfig,
    database_url: str | None,
) -> None:
    """Speichert die ausgewählte Datenbankverbindung.

    None bedeutet: SQLite-Standardkonfiguration verwenden.
    """

    from sqlalchemy.engine import make_url

    if database_url is not None:
        if not isinstance(database_url, str):
            raise TypeError(
                "database_url muss eine Zeichenkette sein."
            )

        database_url = database_url.strip()

        if not database_url:
            raise ValueError(
                "Die Datenbank-URL darf nicht leer sein."
            )

        if not database_url.startswith(
            ("sqlite:///", "postgresql+psycopg://")
        ):
            raise ValueError(
                "Nicht unterstützte Datenbank-URL."
            )

        parsed_url = make_url(database_url)

        if parsed_url.password is not None:
            raise ValueError(
                "Datenbankpasswörter dürfen nicht "
                "in der Konfiguration gespeichert werden."
            )

    config_file = config.config_file

    if config_file.is_file():
        text = config_file.read_text(
            encoding="utf-8",
        )
    else:
        text = ""

    lines = text.splitlines()

    section_start: int | None = None
    section_end = len(lines)

    for index, line in enumerate(lines):
        stripped = line.strip()

        if stripped == "[database]":
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
        section_lines = lines[
            section_start + 1:section_end
        ]

        preserved_lines = []

        for line in section_lines:
            stripped = line.strip()
            key, separator, _ = stripped.partition("=")

            if separator and key.strip() == "url":
                continue

            preserved_lines.append(line)

        lines[
            section_start + 1:section_end
        ] = preserved_lines

    if database_url is not None:
        escaped_url = (
            database_url
            .replace("\\", "\\\\")
            .replace('"', '\\"')
        )

        url_line = f'url = "{escaped_url}"'

        if section_start is not None:
            lines.insert(
                section_start + 1,
                url_line,
            )
        else:
            if lines and lines[-1].strip():
                lines.append("")

            lines.extend([
                "[database]",
                url_line,
            ])

    config_file.parent.mkdir(
        parents=True,
        exist_ok=True,
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

# Historische Konstanten bleiben für Importkompatibilität erhalten, dürfen
# aber beim Modulimport keine Konfigurationsdatei lesen. Der Anwendungsstart
# lädt und validiert die Datei ausdrücklich über load_config().
_current_config = _default_config_for_data_dir(DEFAULT_DATA_DIR)

DATA_DIR = _current_config.data_dir
DATABASE_FILE = _current_config.database_file
DATABASE_URL = _current_config.database_url
TAXONOMY_DIR = _current_config.taxonomy_dir

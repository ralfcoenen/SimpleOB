"""Tests für die Anwendungskonfiguration."""

from pathlib import Path

from openbilanz.core.config import (
    ApplicationConfig,
    default_config,
    desktop_application_data_dir,
    installed_config,
    load_config,
    load_installed_config,
    prepare_application_data_directories,
)


def test_default_config_uses_project_data_directory() -> None:
    config = default_config()

    assert isinstance(
        config,
        ApplicationConfig,
    )

    assert config.database_file == (
        config.data_dir
        / "openbilanz.db"
    )

    assert config.taxonomy_dir == (
        config.data_dir
        / "taxonomy"
    )

    assert config.database_url == (
        f"sqlite:///{config.database_file}"
    )

    assert config.eric_lib_dir is None
    assert config.eric_manufacturer_id is None


def test_load_config_uses_defaults_when_file_is_missing(
    tmp_path: Path,
) -> None:
    config_file = (
        tmp_path
        / "missing.toml"
    )

    config = load_config(
        config_file
    )

    defaults = default_config()

    assert config.data_dir == (
        defaults.data_dir
    )

    assert config.database_file == (
        defaults.database_file
    )

    assert config.taxonomy_dir == (
        defaults.taxonomy_dir
    )

    assert config.config_file == (
        config_file
    )

    assert config.eric_lib_dir is None
    assert config.eric_manufacturer_id is None


def test_load_config_reads_toml_file(
    tmp_path: Path,
) -> None:
    config_file = (
        tmp_path
        / "config.toml"
    )

    data_dir = (
        tmp_path
        / "application-data"
    )

    database_file = (
        tmp_path
        / "database"
        / "openbilanz.db"
    )

    taxonomy_dir = (
        tmp_path
        / "taxonomies"
    )

    config_file.write_text(
        (
            "[application]\n"
            f'data_dir = "{data_dir}"\n'
            "\n"
            "[database]\n"
            f'file = "{database_file}"\n'
            "\n"
            "[taxonomy]\n"
            f'root = "{taxonomy_dir}"\n'
        ),
        encoding="utf-8",
    )

    config = load_config(
        config_file
    )

    assert config.data_dir == (
        data_dir
    )

    assert config.database_file == (
        database_file
    )

    assert config.taxonomy_dir == (
        taxonomy_dir
    )

    assert config.config_file == (
        config_file
    )

    assert config.eric_lib_dir is None
    assert config.eric_manufacturer_id is None


def test_database_and_taxonomy_paths_follow_configured_data_dir(
    tmp_path: Path,
) -> None:
    config_file = (
        tmp_path
        / "config.toml"
    )

    data_dir = (
        tmp_path
        / "application-data"
    )

    config_file.write_text(
        (
            "[application]\n"
            f'data_dir = "{data_dir}"\n'
        ),
        encoding="utf-8",
    )

    config = load_config(
        config_file
    )

    assert config.database_file == (
        data_dir
        / "openbilanz.db"
    )

    assert config.taxonomy_dir == (
        data_dir
        / "taxonomy"
    )


def test_load_config_reads_eric_configuration(
    tmp_path: Path,
) -> None:
    config_file = (
        tmp_path
        / "config.toml"
    )

    eric_lib_dir = (
        tmp_path
        / "eric"
        / "lib"
    )

    certificate_path = (
        tmp_path
        / "certificate"
        / "elster.pfx"
    )

    config_file.write_text(
        (
            "[eric]\n"
            f'lib_dir = "{eric_lib_dir}"\n'
            'manufacturer_id = " 12345 "\n'
            'data_supplier = " Test-Datenlieferant "\n'
            f'certificate_path = "{certificate_path}"\n'
            'certificate_pin = "123456"\n'
        ),
        encoding="utf-8",
    )

    config = load_config(
        config_file
    )

    assert config.eric_lib_dir == eric_lib_dir
    assert config.eric_manufacturer_id == "12345"
    assert config.eric_certificate_path == certificate_path
    assert config.eric_certificate_pin == "123456"

def test_load_config_expands_eric_lib_directory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    home_dir = (
        tmp_path
        / "home"
    )

    monkeypatch.setenv(
        "HOME",
        str(home_dir),
    )

    config_file = (
        tmp_path
        / "config.toml"
    )

    config_file.write_text(
        (
            "[eric]\n"
            'lib_dir = "~/Developer/ERiC/lib"\n'
        ),
        encoding="utf-8",
    )

    config = load_config(
        config_file
    )

    assert config.eric_lib_dir == (
        home_dir
        / "Developer"
        / "ERiC"
        / "lib"
    )

    assert config.eric_manufacturer_id is None


def test_load_config_treats_empty_eric_values_as_missing(
    tmp_path: Path,
) -> None:
    config_file = (
        tmp_path
        / "config.toml"
    )

    config_file.write_text(
        (
            "[eric]\n"
            'lib_dir = ""\n'
            'manufacturer_id = "   "\n'
        ),
        encoding="utf-8",
    )

    config = load_config(
        config_file
    )

    assert config.eric_lib_dir is None
    assert config.eric_manufacturer_id is None
    assert config.eric_data_supplier is None


def test_desktop_application_data_dir_uses_macos_application_support(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "openbilanz.core.config.sys.platform",
        "darwin",
    )
    monkeypatch.setattr(
        Path,
        "home",
        lambda: tmp_path,
    )

    assert desktop_application_data_dir() == (
        tmp_path
        / "Library"
        / "Application Support"
        / "SimpleOB"
    )


def test_installed_config_uses_desktop_application_data_directory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "openbilanz.core.config.sys.platform",
        "darwin",
    )
    monkeypatch.setattr(
        Path,
        "home",
        lambda: tmp_path,
    )

    config = installed_config()

    expected_data_dir = (
        tmp_path
        / "Library"
        / "Application Support"
        / "SimpleOB"
    )

    assert config.data_dir == expected_data_dir
    assert config.database_file == (
        expected_data_dir
        / "openbilanz.db"
    )
    assert config.taxonomy_dir == (
        expected_data_dir
        / "taxonomy"
    )
    assert config.config_file == (
        expected_data_dir
        / "config.toml"
    )


def test_load_installed_config_reads_config_from_desktop_data_directory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "openbilanz.core.config.sys.platform",
        "darwin",
    )
    monkeypatch.setattr(
        Path,
        "home",
        lambda: tmp_path,
    )

    data_dir = (
        tmp_path
        / "Library"
        / "Application Support"
        / "SimpleOB"
    )
    data_dir.mkdir(
        parents=True
    )

    config_file = (
        data_dir
        / "config.toml"
    )
    config_file.write_text(
        (
            "[eric]\n"
            'manufacturer_id = "22924"\n'
        ),
        encoding="utf-8",
    )

    config = load_installed_config()

    assert config.data_dir == data_dir
    assert config.database_file == (
        data_dir
        / "openbilanz.db"
    )
    assert config.taxonomy_dir == (
        data_dir
        / "taxonomy"
    )
    assert config.config_file == config_file
    assert config.eric_manufacturer_id == "22924"


def test_prepare_application_data_directories_creates_required_directories(
    tmp_path: Path,
) -> None:
    data_dir = (
        tmp_path
        / "application-data"
    )
    taxonomy_dir = (
        data_dir
        / "custom-taxonomy"
    )

    config = ApplicationConfig(
        data_dir=data_dir,
        database_file=data_dir / "openbilanz.db",
        taxonomy_dir=taxonomy_dir,
        config_file=data_dir / "config.toml",
    )

    assert not data_dir.exists()
    assert not taxonomy_dir.exists()

    prepare_application_data_directories(
        config
    )

    assert data_dir.is_dir()
    assert taxonomy_dir.is_dir()
    assert not config.database_file.exists()
    assert not config.config_file.exists()

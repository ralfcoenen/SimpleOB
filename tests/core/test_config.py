"""Tests für die Anwendungskonfiguration."""

from pathlib import Path

from openbilanz.core.config import (
    ApplicationConfig,
    default_config,
    load_config,
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

"""Tests für die Anwendungskonfiguration."""

import sys
from pathlib import Path

from openbilanz.core.config import (
    ApplicationConfig,
    bundled_eric_lib_dir,
    default_config,
    desktop_application_data_dir,
    installed_config,
    load_config,
    load_installed_config,
    prepare_application_data_directories,
    save_eric_certificate_path,
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
            'data_supplier = " Test-Datenlieferant "\n'
            f'certificate_path = "{certificate_path}"\n'
        ),
        encoding="utf-8",
    )

    config = load_config(
        config_file
    )

    assert config.eric_lib_dir == eric_lib_dir
    assert config.eric_certificate_path == certificate_path



def test_save_eric_certificate_path_preserves_existing_config(
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

    old_certificate_path = (
        tmp_path
        / "certificates"
        / "old.pfx"
    )

    new_certificate_path = (
        tmp_path
        / "certificates"
        / "new.pfx"
    )

    config_file.write_text(
        (
            "[application]\n"
            f'data_dir = "{data_dir}"\n'
            "\n"
            "[eric]\n"
            'data_supplier = "Testlieferant"\n'
            f'certificate_path = "{old_certificate_path}"\n'
        ),
        encoding="utf-8",
    )

    config = load_config(
        config_file
    )

    save_eric_certificate_path(
        config,
        new_certificate_path,
    )

    text = config_file.read_text(
        encoding="utf-8",
    )

    assert (
        f'data_dir = "{data_dir}"'
        in text
    )
    assert 'data_supplier = "Testlieferant"' in text
    assert (
        f'certificate_path = "{new_certificate_path}"'
        in text
    )
    assert str(old_certificate_path) not in text

    reloaded = load_config(
        config_file
    )

    assert reloaded.data_dir == data_dir
    assert reloaded.eric_data_supplier == "Testlieferant"
    assert (
        reloaded.eric_certificate_path
        == new_certificate_path
    )


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
            'data_supplier = "   "\n'
        ),
        encoding="utf-8",
    )

    config = load_config(
        config_file
    )

    assert config.eric_lib_dir is None
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
        "",
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


def test_bundled_eric_lib_dir_returns_none_outside_frozen_application(
    monkeypatch,
) -> None:
    monkeypatch.delattr(
        sys,
        "frozen",
        raising=False,
    )
    monkeypatch.delattr(
        sys,
        "_MEIPASS",
        raising=False,
    )

    assert bundled_eric_lib_dir() is None


def test_bundled_eric_lib_dir_returns_bundled_lib_directory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    eric_lib_dir = (
        tmp_path
        / "eric"
        / "lib"
    )
    eric_lib_dir.mkdir(
        parents=True
    )

    monkeypatch.setattr(
        sys,
        "frozen",
        True,
        raising=False,
    )
    monkeypatch.setattr(
        sys,
        "_MEIPASS",
        str(tmp_path),
        raising=False,
    )

    assert (
        bundled_eric_lib_dir()
        == eric_lib_dir
    )


def test_load_installed_config_uses_bundled_eric_lib_directory(
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

    application_data_dir = (
        tmp_path
        / "Library"
        / "Application Support"
        / "SimpleOB"
    )
    application_data_dir.mkdir(
        parents=True
    )

    bundle_dir = (
        tmp_path
        / "bundle"
    )
    eric_lib_dir = (
        bundle_dir
        / "eric"
        / "lib"
    )
    eric_lib_dir.mkdir(
        parents=True
    )

    config_file = (
        application_data_dir
        / "config.toml"
    )
    config_file.write_text(
        (
            "[eric]\n"
            'lib_dir = "/old/development/eric/lib"\n'
            'data_supplier = "Testlieferant"\n'
            'certificate_path = "/tmp/test.pfx"\n'
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "frozen",
        True,
        raising=False,
    )
    monkeypatch.setattr(
        sys,
        "_MEIPASS",
        str(bundle_dir),
        raising=False,
    )

    config = load_installed_config()

    assert config.eric_lib_dir == eric_lib_dir
    assert config.eric_data_supplier == "Testlieferant"
    assert config.eric_certificate_path == Path(
        "/tmp/test.pfx"
    )

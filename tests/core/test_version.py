"""Tests für die zentrale SimpleOB-Versionsinformation."""

from importlib.metadata import PackageNotFoundError

import simpleob.core.version as version_module


def test_get_application_version_uses_distribution_version(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        version_module,
        "version",
        lambda distribution_name: "0.44.0",
    )

    assert version_module.get_application_version() == "0.44.0"


def test_get_application_version_uses_fallback_when_package_is_missing(
    monkeypatch,
) -> None:
    def raise_package_not_found(distribution_name: str) -> str:
        raise PackageNotFoundError(distribution_name)

    monkeypatch.setattr(
        version_module,
        "version",
        raise_package_not_found,
    )

    assert version_module.get_application_version() == "0.0.0"

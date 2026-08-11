"""Tests für den Arelle-Adapter."""

from pathlib import Path

import pytest

from openbilanz.taxonomy.arelle_adapter import ArelleAdapter

ENTRY_POINT = Path(
    "/tmp/openbilanz-taxonomy/6.8/"
    "german-gaap-taxonomy-v6.8-2024-04-01/"
    "xbrl/"
    "de-gaap-ci-2024-04-01/"
    "de-gaap-ci-2024-04-01-shell-fiscal.xsd"
)

INVALID_INSTANCE = Path(
    "tests/fixtures/invalid_xbrl_instance.xbrl"
)


def require_taxonomy() -> None:
    """Überspringt den Test, wenn die lokale Taxonomie fehlt."""

    if not ENTRY_POINT.is_file():
        pytest.skip(
            "German GAAP taxonomy 6.8 is not installed locally"
        )


def test_arelle_adapter_loads_taxonomy() -> None:
    """Der Adapter lädt eine Taxonomie über Arelle."""

    require_taxonomy()

    adapter = ArelleAdapter()

    try:
        taxonomy = adapter.load_taxonomy(
            ENTRY_POINT
        )

        assert taxonomy.concept_count == 3531

        assert (
            "http://www.xbrl.de/taxonomies/"
            "de-gaap-ci-2024-04-01"
            in taxonomy.namespaces
        )

    finally:
        adapter.close()


def test_arelle_adapter_validates_taxonomy() -> None:
    """Der Adapter validiert eine Taxonomie über Arelle."""

    require_taxonomy()

    adapter = ArelleAdapter()

    try:
        result = adapter.validate(
            ENTRY_POINT
        )

        assert result.is_valid
        assert result.errors == ()

    finally:
        adapter.close()


def test_arelle_adapter_reports_validation_errors() -> None:
    """Der Adapter gibt Arelle-Validierungsfehler zurück."""

    adapter = ArelleAdapter()

    try:
        result = adapter.validate(
            INVALID_INSTANCE
        )

        assert not result.is_valid
        assert result.errors

    finally:
        adapter.close()


"""Gemeinsame Auflösung optionaler, bereits lokal vorhandener Testtaxonomien.

SIMPLEOB_TAXONOMY_ROOT bezeichnet ein Verzeichnis mit den Versionsordnern
6.8, 6.9 und/oder 6.10. Pakete dürfen darunter unterschiedlich verschachtelt
sein. Ohne Vorgabe werden Projektressourcen, danach Benutzerdaten verwendet.
Es werden weder Dateien installiert noch produktive Einstellungen geändert.
"""

import os
from pathlib import Path

import pytest

from simpleob.core.config import desktop_application_data_dir
from simpleob.taxonomy.resolver import TaxonomyResolver
from simpleob.taxonomy.taxonomy import TaxonomyVersion


def taxonomy_test_root() -> Path:
    """Liefert die explizite Testwurzel oder einen vorhandenen Standardpfad."""
    configured = os.environ.get("SIMPLEOB_TAXONOMY_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    project_root = Path(__file__).resolve().parents[1] / "data" / "taxonomy"
    if any((project_root / version.value).is_dir() for version in TaxonomyVersion):
        return project_root
    return desktop_application_data_dir() / "taxonomy"


def taxonomy_entry_point(version: str, *, kind: str = "gaap-ci") -> Path:
    """Findet ein eindeutiges Einstiegsschema; fehlende Ressourcen sind optional."""
    root = taxonomy_test_root()
    resolver = TaxonomyResolver(root)
    if kind == "gaap-ci":
        find = resolver.gaap_ci_fiscal_entry_point
    elif kind == "gcd":
        find = resolver.gcd_entry_point
    else:
        raise ValueError(f"Unbekannter Taxonomie-Einstiegspunkt: {kind}")
    try:
        return find(TaxonomyVersion(version))
    except FileNotFoundError:
        pytest.skip(
            f"Optionale Taxonomie {version} ({kind}) fehlt unter {root}. "
            "SIMPLEOB_TAXONOMY_ROOT auf vorhandene Versionsverzeichnisse setzen."
        )

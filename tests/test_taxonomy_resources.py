"""Testressourcen bleiben konfigurierbar und unterschiedliche Paketlayouts lesbar."""


import pytest

from tests.taxonomy_resources import taxonomy_entry_point


@pytest.mark.parametrize("nested", (False, True))
def test_taxonomy_resources_resolve_both_package_layouts(tmp_path, monkeypatch, nested):
    monkeypatch.setenv("SIMPLEOB_TAXONOMY_ROOT", str(tmp_path))
    version = tmp_path / "6.9"
    package = version / "package" / "xbrl" if nested else version
    gaap = package / "de-gaap-ci-2025-04-01" / "de-gaap-ci-2025-04-01-shell-fiscal.xsd"
    gcd = package / "de-gcd-2025-04-01" / "de-gcd-2025-04-01-shell.xsd"
    for path in (gaap, gcd):
        path.parent.mkdir(parents=True)
        path.touch()
    assert taxonomy_entry_point("6.9") == gaap
    assert taxonomy_entry_point("6.9", kind="gcd") == gcd


def test_explicit_missing_taxonomy_root_skips_without_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("SIMPLEOB_TAXONOMY_ROOT", str(tmp_path))
    with pytest.raises(pytest.skip.Exception, match="SIMPLEOB_TAXONOMY_ROOT"):
        taxonomy_entry_point("6.9")


def test_ambiguous_taxonomy_entry_points_fail(tmp_path, monkeypatch):
    monkeypatch.setenv("SIMPLEOB_TAXONOMY_ROOT", str(tmp_path))
    for package in ("one", "two"):
        path = tmp_path / "6.9" / package / "de-gaap-ci-2025-04-01-shell-fiscal.xsd"
        path.parent.mkdir(parents=True)
        path.touch()
    with pytest.raises(ValueError, match="multiple"):
        taxonomy_entry_point("6.9")

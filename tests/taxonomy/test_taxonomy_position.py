"""Tests für Positionen der E-Bilanz-Taxonomie."""

import pytest

from simpleob.taxonomy.taxonomy import TaxonomyPosition


def test_taxonomy_position_stores_name_and_label() -> None:
    """Eine Taxonomieposition speichert Name und Bezeichnung."""

    position = TaxonomyPosition(
        name="bs.ass",
        label="Aktiva",
    )

    assert position.name == "bs.ass"
    assert position.label == "Aktiva"
    assert position.children == ()


def test_taxonomy_position_can_have_children() -> None:
    """Eine Taxonomieposition kann Unterpositionen enthalten."""

    child = TaxonomyPosition(
        name="bs.ass.fixAss",
        label="Anlagevermögen",
    )

    parent = TaxonomyPosition(
        name="bs.ass",
        label="Aktiva",
        children=(child,),
    )

    assert parent.children == (
        child,
    )


def test_taxonomy_position_rejects_blank_name() -> None:
    """Ein leerer technischer Name ist unzulässig."""

    with pytest.raises(
        ValueError,
        match="name must not be blank",
    ):
        TaxonomyPosition(
            name="",
            label="Aktiva",
        )


def test_taxonomy_position_rejects_blank_label() -> None:
    """Eine leere Bezeichnung ist unzulässig."""

    with pytest.raises(
        ValueError,
        match="label must not be blank",
    ):
        TaxonomyPosition(
            name="bs.ass",
            label="",
        )

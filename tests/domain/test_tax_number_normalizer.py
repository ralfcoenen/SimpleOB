import pytest

from openbilanz.domain.tax_number_normalizer import (
    TaxNumberNormalizer,
)


def test_normalizes_north_rhine_westphalia_tax_number() -> None:
    result = TaxNumberNormalizer().normalize(
        federal_state="NW",
        tax_number="123/4567/8901",
    )

    assert result == "5123045678901"


def test_accepts_nrw_tax_number_without_separators() -> None:
    result = TaxNumberNormalizer().normalize(
        federal_state="NW",
        tax_number="12345678901",
    )

    assert result == "5123045678901"


def test_rejects_invalid_nrw_tax_number() -> None:
    with pytest.raises(
        ValueError,
        match="Ungültige Steuernummer für Nordrhein-Westfalen",
    ):
        TaxNumberNormalizer().normalize(
            federal_state="NW",
            tax_number="1234/5678/9012",
        )


def test_rejects_unsupported_federal_state() -> None:
    with pytest.raises(
        ValueError,
        match="Bundesland wird noch nicht unterstützt",
    ):
        TaxNumberNormalizer().normalize(
            federal_state="BE",
            tax_number="12/345/67890",
        )


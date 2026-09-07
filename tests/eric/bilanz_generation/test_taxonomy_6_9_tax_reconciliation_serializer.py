"""Tests für die HGBM-Überleitungsserialisierung der Taxonomie 6.9."""

from decimal import Decimal
from xml.etree import ElementTree as ET

import pytest

from openbilanz.eric.bilanz_generation.tax_reconciliation import (
    TaxReconciliationChange,
    TaxReconciliationKind,
    TaxReconciliationTransfer,
)
from openbilanz.eric.bilanz_generation.taxonomy_6_9_tax_reconciliation_serializer import (
    GAAP_CI_69_NAMESPACE,
    Taxonomy69TaxReconciliationSerializer,
)


def _qname(local_name: str) -> str:
    return (
        f"{{{GAAP_CI_69_NAMESPACE}}}"
        f"{local_name}"
    )


def test_serializes_confirmed_hgbm_change_value_transfer() -> None:
    transfer = TaxReconciliationTransfer(
        kind=TaxReconciliationKind.CHANGE_VALUE,
        asset_changes=(
            TaxReconciliationChange(
                concept_name=(
                    "bs.ass.fixAss.tan."
                    "otherEquipm.otherbga"
                ),
                actual_period=Decimal("-13.26"),
                previous_period=Decimal("0.00"),
            ),
        ),
        equity_liability_changes=(
            TaxReconciliationChange(
                concept_name=(
                    "bs.eqLiab.equity.netIncome"
                ),
                actual_period=Decimal("-13.26"),
                previous_period=Decimal("0.00"),
            ),
        ),
        income_statement_changes=(
            TaxReconciliationChange(
                concept_name=(
                    "is.netIncome.regular."
                    "operatingTC.deprAmort."
                    "fixAss.tan.other"
                ),
                actual_period=Decimal("13.26"),
            ),
            TaxReconciliationChange(
                concept_name=(
                    "is.netIncome.regular."
                    "operatingTC"
                ),
                actual_period=Decimal("-13.26"),
            ),
        ),
    )

    element = (
        Taxonomy69TaxReconciliationSerializer.serialize(
            transfer=transfer,
            context_id="D-2026",
            unit_id="EUR",
        )
    )

    assert element.tag == _qname(
        "hbst.transfer"
    )

    kind = element.find(
        _qname(
            "hbst.transfer.kind.changeValue"
        )
    )
    assert kind is not None
    assert kind.attrib == {
        "contextRef": "D-2026",
    }
    assert kind.text == "true"

    bs_ass = element.find(
        _qname("hbst.transfer.bsAss")
    )
    assert bs_ass is not None

    bs_ass_name = bs_ass.find(
        _qname("hbst.transfer.bsAss.name")
    )
    assert bs_ass_name is not None
    assert bs_ass_name.text == (
        "de-gaap-ci:"
        "bs.ass.fixAss.tan."
        "otherEquipm.otherbga"
    )

    bs_ass_actual = bs_ass.find(
        _qname(
            "hbst.transfer.bsAss."
            "changeValueActualPeriod"
        )
    )
    assert bs_ass_actual is not None
    assert bs_ass_actual.text == "-13.26"

    bs_ass_previous = bs_ass.find(
        _qname(
            "hbst.transfer.bsAss."
            "changeValuePreviousPeriod"
        )
    )
    assert bs_ass_previous is not None
    assert bs_ass_previous.text == "0.00"

    bs_eq_liab = element.find(
        _qname("hbst.transfer.bsEqLiab")
    )
    assert bs_eq_liab is not None

    income_changes = element.findall(
        _qname(
            "hbst.transfer.isChangeNetIncome"
        )
    )
    assert len(income_changes) == 2

    xml = ET.tostring(
        element,
        encoding="unicode",
    )
    assert "13.26" in xml
    assert "otherEquipm.otherbga" in xml
    assert "operatingTC" in xml


def test_transfer_requires_at_least_one_change() -> None:
    with pytest.raises(
        ValueError,
        match="at least one change",
    ):
        TaxReconciliationTransfer(
            kind=(
                TaxReconciliationKind.CHANGE_VALUE
            ),
        )


def test_change_rejects_blank_concept_name() -> None:
    with pytest.raises(
        ValueError,
        match="must not be blank",
    ):
        TaxReconciliationChange(
            concept_name=" ",
            actual_period=Decimal("1.00"),
        )

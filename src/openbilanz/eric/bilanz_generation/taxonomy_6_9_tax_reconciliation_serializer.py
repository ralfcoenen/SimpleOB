"""XBRL-Serialisierung der HGBM-Überleitungsrechnung für 6.9."""

from __future__ import annotations

from decimal import Decimal
from xml.etree import ElementTree as ET

from openbilanz.eric.bilanz_generation.tax_reconciliation import (
    TaxReconciliationChange,
    TaxReconciliationTransfer,
)

GAAP_CI_69_NAMESPACE = (
    "http://www.xbrl.de/taxonomies/"
    "de-gaap-ci-2025-04-01"
)


class Taxonomy69TaxReconciliationSerializer:
    """Serialisiert bestätigte Taxonomie-6.9-hbst.transfer-Tuples."""

    @classmethod
    def serialize(
        cls,
        *,
        transfer: TaxReconciliationTransfer,
        context_id: str,
        unit_id: str,
    ) -> ET.Element:
        """Erzeugt genau ein hbst.transfer-Tuple."""

        if not isinstance(
            transfer,
            TaxReconciliationTransfer,
        ):
            raise TypeError(
                "transfer must be a "
                "TaxReconciliationTransfer"
            )

        cls._validate_id(
            value=context_id,
            name="context_id",
        )
        cls._validate_id(
            value=unit_id,
            name="unit_id",
        )

        element = ET.Element(
            cls._qname("hbst.transfer")
        )

        kind = ET.SubElement(
            element,
            cls._qname("hbst.transfer.kind"),
        )

        kind_value = ET.SubElement(
            kind,
            cls._qname(transfer.kind.value),
            {
                "contextRef": context_id,
            },
        )
        kind_value.text = "true"

        for change in transfer.asset_changes:
            element.append(
                cls._balance_change_element(
                    tuple_name="hbst.transfer.bsAss",
                    change=change,
                    context_id=context_id,
                    unit_id=unit_id,
                )
            )

        for change in transfer.equity_liability_changes:
            element.append(
                cls._balance_change_element(
                    tuple_name="hbst.transfer.bsEqLiab",
                    change=change,
                    context_id=context_id,
                    unit_id=unit_id,
                )
            )

        for change in transfer.income_statement_changes:
            element.append(
                cls._income_statement_change_element(
                    change=change,
                    context_id=context_id,
                    unit_id=unit_id,
                )
            )

        return element

    @classmethod
    def _balance_change_element(
        cls,
        *,
        tuple_name: str,
        change: TaxReconciliationChange,
        context_id: str,
        unit_id: str,
    ) -> ET.Element:
        element = ET.Element(
            cls._qname(tuple_name)
        )

        name = ET.SubElement(
            element,
            cls._qname(f"{tuple_name}.name"),
            {
                "contextRef": context_id,
            },
        )
        name.text = (
            f"de-gaap-ci:{change.concept_name}"
        )

        actual = ET.SubElement(
            element,
            cls._qname(
                f"{tuple_name}.changeValueActualPeriod"
            ),
            {
                "contextRef": context_id,
                "unitRef": unit_id,
                "decimals": "2",
            },
        )
        actual.text = cls._decimal_text(
            change.actual_period
        )

        if change.previous_period is not None:
            previous = ET.SubElement(
                element,
                cls._qname(
                    f"{tuple_name}."
                    "changeValuePreviousPeriod"
                ),
                {
                    "contextRef": context_id,
                    "unitRef": unit_id,
                    "decimals": "2",
                },
            )
            previous.text = cls._decimal_text(
                change.previous_period
            )

        return element

    @classmethod
    def _income_statement_change_element(
        cls,
        *,
        change: TaxReconciliationChange,
        context_id: str,
        unit_id: str,
    ) -> ET.Element:
        tuple_name = (
            "hbst.transfer.isChangeNetIncome"
        )
        element = ET.Element(
            cls._qname(tuple_name)
        )

        name = ET.SubElement(
            element,
            cls._qname(f"{tuple_name}.name"),
            {
                "contextRef": context_id,
            },
        )
        name.text = (
            f"de-gaap-ci:{change.concept_name}"
        )

        actual = ET.SubElement(
            element,
            cls._qname(
                f"{tuple_name}.changeValueActualPeriod"
            ),
            {
                "contextRef": context_id,
                "unitRef": unit_id,
                "decimals": "2",
            },
        )
        actual.text = cls._decimal_text(
            change.actual_period
        )

        return element

    @staticmethod
    def _decimal_text(value: Decimal) -> str:
        return format(
            value.quantize(Decimal("0.01")),
            "f",
        )

    @staticmethod
    def _validate_id(
        *,
        value: str,
        name: str,
    ) -> None:
        if not isinstance(value, str):
            raise TypeError(
                f"{name} must be a string"
            )

        if not value.strip():
            raise ValueError(
                f"{name} must not be blank"
            )

    @staticmethod
    def _qname(local_name: str) -> str:
        return (
            f"{{{GAAP_CI_69_NAMESPACE}}}"
            f"{local_name}"
        )

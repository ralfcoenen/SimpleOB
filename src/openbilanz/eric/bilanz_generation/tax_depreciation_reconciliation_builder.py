"""Fachlicher Builder für bestätigte HGBM-AfA-Überleitungen."""

from __future__ import annotations

from decimal import Decimal

from openbilanz.eric.bilanz_generation.tax_reconciliation import (
    TaxReconciliationChange,
    TaxReconciliationKind,
    TaxReconciliationTransfer,
)


class TaxDepreciationReconciliationBuilder:
    """Erzeugt die bestätigte HGBM-Überleitung einer AfA-Wertänderung.

    Der Builder berechnet keine steuerlich zulässige AfA. Er erhält nur
    die bereits fachlich bestimmte zusätzliche steuerliche AfA und bildet
    daraus die für Taxonomie 6.9 bestätigte Überleitungsstruktur.
    """

    _ASSET_CONCEPTS = (
        "bs.ass.fixAss.tan.otherEquipm.otherbga",
        "bs.ass.fixAss.tan.otherEquipm",
        "bs.ass.fixAss.tan",
        "bs.ass.fixAss",
        "bs.ass",
    )

    _EQUITY_LIABILITY_CONCEPTS = (
        "bs.eqLiab.equity.netIncome",
        "bs.eqLiab.equity",
        "bs.eqLiab",
    )

    _DEPRECIATION_EXPENSE_CONCEPTS = (
        (
            "is.netIncome.regular.operatingTC."
            "deprAmort.fixAss.tan.other"
        ),
        (
            "is.netIncome.regular.operatingTC."
            "deprAmort.fixAss.tan"
        ),
        (
            "is.netIncome.regular.operatingTC."
            "deprAmort.fixAss"
        ),
        (
            "is.netIncome.regular.operatingTC."
            "deprAmort"
        ),
    )

    _RESULT_CONCEPTS = (
        "is.netIncome.regular.operatingTC",
        "is.netIncome.eat",
        "is.netIncome",
    )

    @classmethod
    def build(
        cls,
        *,
        additional_tax_depreciation: Decimal,
    ) -> TaxReconciliationTransfer:
        """Erzeugt die Überleitung für zusätzliche steuerliche AfA."""

        if not isinstance(
            additional_tax_depreciation,
            Decimal,
        ):
            raise TypeError(
                "additional_tax_depreciation must be a Decimal"
            )

        if additional_tax_depreciation <= Decimal("0"):
            raise ValueError(
                "additional_tax_depreciation must be greater than zero"
            )

        amount = additional_tax_depreciation.quantize(
            Decimal("0.01")
        )
        negative_amount = -amount

        return TaxReconciliationTransfer(
            kind=TaxReconciliationKind.CHANGE_VALUE,
            asset_changes=tuple(
                TaxReconciliationChange(
                    concept_name=concept_name,
                    actual_period=negative_amount,
                )
                for concept_name in cls._ASSET_CONCEPTS
            ),
            equity_liability_changes=tuple(
                TaxReconciliationChange(
                    concept_name=concept_name,
                    actual_period=negative_amount,
                )
                for concept_name in cls._EQUITY_LIABILITY_CONCEPTS
            ),
            income_statement_changes=(
                *(
                    TaxReconciliationChange(
                        concept_name=concept_name,
                        actual_period=amount,
                    )
                    for concept_name in (
                        cls._DEPRECIATION_EXPENSE_CONCEPTS
                    )
                ),
                *(
                    TaxReconciliationChange(
                        concept_name=concept_name,
                        actual_period=negative_amount,
                    )
                    for concept_name in cls._RESULT_CONCEPTS
                ),
            ),
        )

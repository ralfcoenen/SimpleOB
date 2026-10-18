"""Fachlicher Builder für bestätigte HGBM-AfA-Überleitungen."""

from __future__ import annotations

from decimal import Decimal

from simpleob.eric.bilanz_generation.tax_reconciliation import (
    TaxReconciliationChange,
    TaxReconciliationKind,
    TaxReconciliationTransfer,
)


class TaxDepreciationReconciliationBuilder:
    """Erzeugt die ERiC-bestätigte HGBM-Überleitung einer AfA-Differenz.

    Der Builder berechnet keine steuerlich zulässige AfA.

    Er erhält ausschließlich die bereits fachlich ermittelten
    Buchwertdifferenzen zwischen Steuerbilanz und Handelsbilanz:

    current_book_value_difference
        Steuerlicher Buchwert minus HGB-Buchwert aus dem laufenden
        Geschäftsjahr.

    previous_book_value_difference
        Steuerlicher Buchwert minus HGB-Buchwert, der bereits zu Beginn
        des Geschäftsjahres aus Vorjahren bestand.

    Die erzeugte Struktur entspricht den real mit ERiC bestätigten
    Taxonomie-6.9-Fällen für Erstjahr und Folgejahr.
    """

    _ASSET_CONCEPTS = (
        "bs.ass.fixAss.tan.otherEquipm.otherbga",
        "bs.ass.fixAss.tan.otherEquipm",
        "bs.ass.fixAss.tan",
        "bs.ass.fixAss",
        "bs.ass",
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
        current_book_value_difference: Decimal,
        previous_book_value_difference: Decimal = Decimal("0.00"),
    ) -> TaxReconciliationTransfer:
        """Erzeugt die bestätigte HGBM-AfA-Überleitungsstruktur."""

        if not isinstance(
            current_book_value_difference,
            Decimal,
        ):
            raise TypeError(
                "current_book_value_difference must be a Decimal"
            )

        if not isinstance(
            previous_book_value_difference,
            Decimal,
        ):
            raise TypeError(
                "previous_book_value_difference must be a Decimal"
            )

        current_difference = current_book_value_difference.quantize(
            Decimal("0.01")
        )
        previous_difference = previous_book_value_difference.quantize(
            Decimal("0.01")
        )

        if (
            current_difference == Decimal("0.00")
            and previous_difference == Decimal("0.00")
        ):
            raise ValueError(
                "at least one book value difference must be non-zero"
            )

        zero = Decimal("0.00")

        return TaxReconciliationTransfer(
            kind=TaxReconciliationKind.CHANGE_VALUE,
            asset_changes=tuple(
                TaxReconciliationChange(
                    concept_name=concept_name,
                    actual_period=current_difference,
                    previous_period=previous_difference,
                )
                for concept_name in cls._ASSET_CONCEPTS
            ),
            equity_liability_changes=(
                TaxReconciliationChange(
                    concept_name="bs.eqLiab.equity.netIncome",
                    actual_period=current_difference,
                    previous_period=zero,
                ),
                TaxReconciliationChange(
                    concept_name="bs.eqLiab.equity.retainedEarnings",
                    actual_period=zero,
                    previous_period=previous_difference,
                ),
                TaxReconciliationChange(
                    concept_name="bs.eqLiab.equity",
                    actual_period=current_difference,
                    previous_period=previous_difference,
                ),
                TaxReconciliationChange(
                    concept_name="bs.eqLiab",
                    actual_period=current_difference,
                    previous_period=previous_difference,
                ),
            ),
            income_statement_changes=(
                *(
                    TaxReconciliationChange(
                        concept_name=concept_name,
                        actual_period=-current_difference,
                    )
                    for concept_name in (
                        cls._DEPRECIATION_EXPENSE_CONCEPTS
                    )
                ),
                *(
                    TaxReconciliationChange(
                        concept_name=concept_name,
                        actual_period=current_difference,
                    )
                    for concept_name in cls._RESULT_CONCEPTS
                ),
            ),
        )

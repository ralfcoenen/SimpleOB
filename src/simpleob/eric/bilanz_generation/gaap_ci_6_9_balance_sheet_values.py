"""GAAP-CI-Bilanzwerte für den ERiC-Fact-Plan der Taxonomie 6.9."""

from __future__ import annotations

from decimal import Decimal

from simpleob.accounting.balance_sheet import BalanceSheet
from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.domain.balance_sheet_presentation import (
    BalanceSheetPresentation,
)
from simpleob.domain.money import ZERO
from simpleob.eric.bilanz_generation.fact_plan_resolver import (
    FactPlanPath,
    FactPlanValue,
)
from simpleob.taxonomy.hgb_gaap_ci_mapping import (
    create_hgb_gaap_ci_mapping,
)
from simpleob.taxonomy.mapping_set import TaxonomyMappingSet


class GaapCi69BalanceSheetValueBuilder:
    """Übersetzt eine SimpleOB-Bilanz in GAAP-CI-FactPlan-Werte."""

    @classmethod
    def build(
        cls,
        *,
        balance_sheet: BalanceSheet,
        income_statement: FinancialStatementPosition,
        presentation: BalanceSheetPresentation = (
            BalanceSheetPresentation.BEFORE_APPROPRIATION
        ),
    ) -> dict[FactPlanPath, FactPlanValue]:
        """Erzeugt GAAP-CI-Werte aus den vorhandenen HGB-Bilanzwerten."""

        if not isinstance(balance_sheet, BalanceSheet):
            raise TypeError(
                "balance_sheet must be a BalanceSheet"
            )

        if not isinstance(
            income_statement,
            FinancialStatementPosition,
        ):
            raise TypeError(
                "income_statement must be a FinancialStatementPosition"
            )

        mappings = create_hgb_gaap_ci_mapping(
            assets=balance_sheet.assets,
            liabilities=balance_sheet.liabilities,
            income_statement=income_statement,
        )

        values: dict[
            FactPlanPath,
            FactPlanValue,
        ] = {}

        for position, amount in balance_sheet.amounts.items():
            cls._add_position_value(
                values=values,
                mappings=mappings,
                position=position,
                amount=amount,
                presentation=presentation,
            )

        return values

    @staticmethod
    def _add_position_value(
        *,
        values: dict[FactPlanPath, FactPlanValue],
        mappings: TaxonomyMappingSet,
        position: FinancialStatementPosition,
        amount: Decimal,
        presentation: BalanceSheetPresentation,
    ) -> None:
        if amount == ZERO:
            return

        if (
            presentation
            is BalanceSheetPresentation.AFTER_APPROPRIATION
            and position.code == "HGB.266.PASSIVA.A.V"
        ):
            values[("bs.eqLiab.equity.profitLoss",)] = amount
            return

        mapping = mappings.for_position(position)

        if mapping is None:
            return

        values[(mapping.concept_name,)] = amount

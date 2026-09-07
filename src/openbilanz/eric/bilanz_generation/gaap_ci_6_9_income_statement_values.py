"""GAAP-CI-GuV-Werte für den ERiC-Fact-Plan der Taxonomie 6.9."""

from __future__ import annotations

from decimal import Decimal

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.domain.money import ZERO
from openbilanz.eric.bilanz_generation.fact_plan_resolver import (
    FactPlanPath,
    FactPlanValue,
)
from openbilanz.services.fixed_asset_schedule_service import (
    FixedAssetSchedulePosition,
)
from openbilanz.taxonomy.hgb_gaap_ci_mapping import (
    create_hgb_gaap_ci_mapping,
)
from openbilanz.taxonomy.mapping_set import TaxonomyMappingSet


_TANGIBLE_FIXED_ASSET_PREFIX = (
    "HGB.266.AKTIVA.A.II"
)

_TANGIBLE_FIXED_ASSET_DEPRECIATION_CONCEPT = (
    "is.netIncome.regular.operatingTC."
    "deprAmort.fixAss.tan"
)

_TANGIBLE_FIXED_ASSET_OTHER_DEPRECIATION_CONCEPT = (
    "is.netIncome.regular.operatingTC."
    "deprAmort.fixAss.tan.other"
)

class GaapCi69IncomeStatementValueBuilder:
    """Übersetzt eine SimpleOB-GuV in GAAP-CI-FactPlan-Werte."""

    @classmethod
    def build(
        cls,
        *,
        income_statement: IncomeStatement,
        assets: FinancialStatementPosition,
        liabilities: FinancialStatementPosition,
        fixed_asset_schedule: tuple[
            FixedAssetSchedulePosition,
            ...
        ] = (),
    ) -> dict[FactPlanPath, FactPlanValue]:
        """Erzeugt GAAP-CI-Werte aus vorhandenen HGB-Daten."""

        if not isinstance(
            income_statement,
            IncomeStatement,
        ):
            raise TypeError(
                "income_statement must be an IncomeStatement"
            )

        if not isinstance(
            assets,
            FinancialStatementPosition,
        ):
            raise TypeError(
                "assets must be a FinancialStatementPosition"
            )

        if not isinstance(
            liabilities,
            FinancialStatementPosition,
        ):
            raise TypeError(
                "liabilities must be a FinancialStatementPosition"
            )

        if not isinstance(
            fixed_asset_schedule,
            tuple,
        ):
            raise TypeError(
                "fixed_asset_schedule must be a tuple"
            )

        if not all(
            isinstance(
                position,
                FixedAssetSchedulePosition,
            )
            for position in fixed_asset_schedule
        ):
            raise TypeError(
                "fixed_asset_schedule must contain only "
                "FixedAssetSchedulePosition objects"
            )

        mappings = create_hgb_gaap_ci_mapping(
            assets=assets,
            liabilities=liabilities,
            income_statement=(
                income_statement.income_statement
            ),
        )

        values: dict[
            FactPlanPath,
            FactPlanValue,
        ] = {}

        for position, amount in income_statement.amounts.items():
            cls._add_position_value(
                values=values,
                mappings=mappings,
                position=position,
                amount=amount,
            )

        cls._add_fixed_asset_depreciation_values(
            values=values,
            fixed_asset_schedule=fixed_asset_schedule,
        )

        return values

    @staticmethod
    def _add_position_value(
        *,
        values: dict[FactPlanPath, FactPlanValue],
        mappings: TaxonomyMappingSet,
        position: FinancialStatementPosition,
        amount: Decimal,
    ) -> None:
        if amount == ZERO:
            return

        mapping = mappings.for_position(position)

        if mapping is None:
            return

        values[(mapping.concept_name,)] = amount

    @staticmethod
    def _add_fixed_asset_depreciation_values(
        *,
        values: dict[FactPlanPath, FactPlanValue],
        fixed_asset_schedule: tuple[
            FixedAssetSchedulePosition,
            ...
        ],
    ) -> None:
        tangible_depreciation = sum(
            (
                position.depreciation_current_year
                for position in fixed_asset_schedule
                if position.position_code.startswith(
                    _TANGIBLE_FIXED_ASSET_PREFIX
                )
            ),
            ZERO,
        )

        if tangible_depreciation == ZERO:
            return

        values[
            (
                _TANGIBLE_FIXED_ASSET_DEPRECIATION_CONCEPT,
            )
        ] = tangible_depreciation

        values[
            (
                _TANGIBLE_FIXED_ASSET_OTHER_DEPRECIATION_CONCEPT,
            )
        ] = tangible_depreciation

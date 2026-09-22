"""GAAP-CI-GuV-Werte für den ERiC-Fact-Plan der Taxonomie 6.9."""

from __future__ import annotations

from decimal import Decimal

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.domain.fixed_asset_disposal_detail import (
    FixedAssetDisposalDetail,
)
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

_FIXED_ASSET_DISPOSAL_LOSS_CONCEPT = (
    "is.netIncome.regular.operatingTC."
    "otherCost.disposFixAss"
)

_FIXED_ASSET_DISPOSAL_LOSS_SALE_CONCEPT = (
    "is.netIncome.regular.operatingTC."
    "otherCost.disposFixAss.sale"
)

_FIXED_ASSET_DISPOSAL_LOSS_BOOK_VALUE_CONCEPT = (
    "is.netIncome.regular.operatingTC."
    "otherCost.disposFixAss.bookValue"
)

_FIXED_ASSET_DISPOSAL_GAIN_CONCEPT = (
    "is.netIncome.regular.operatingTC."
    "otherOpRevenue.disposFixAss"
)

_FIXED_ASSET_DISPOSAL_GAIN_SALE_CONCEPT = (
    "is.netIncome.regular.operatingTC."
    "otherOpRevenue.disposFixAss.sale"
)

_FIXED_ASSET_DISPOSAL_GAIN_BOOK_VALUE_CONCEPT = (
    "is.netIncome.regular.operatingTC."
    "otherOpRevenue.disposFixAss.bookValue"
)

_FIXED_ASSET_TAXONOMY_SUFFIXES = (
    (
        "HGB.266.AKTIVA.A.I",
        "intan",
    ),
    (
        "HGB.266.AKTIVA.A.II",
        "tan",
    ),
    (
        "HGB.266.AKTIVA.A.III",
        "fin",
    ),
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
        fixed_asset_disposal_details: tuple[
            FixedAssetDisposalDetail,
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
        if not isinstance(
            fixed_asset_disposal_details,
            tuple,
        ):
            raise TypeError(
                "fixed_asset_disposal_details must be a tuple"
            )

        if not all(
            isinstance(
                detail,
                FixedAssetDisposalDetail,
            )
            for detail in fixed_asset_disposal_details
        ):
            raise TypeError(
                "fixed_asset_disposal_details must contain only "
                "FixedAssetDisposalDetail objects"
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

        cls._add_fixed_asset_disposal_values(
            values=values,
            fixed_asset_disposal_details=(
                fixed_asset_disposal_details
            ),
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

    @classmethod
    def _add_fixed_asset_disposal_values(
        cls,
        *,
        values: dict[FactPlanPath, FactPlanValue],
        fixed_asset_disposal_details: tuple[
            FixedAssetDisposalDetail,
            ...
        ],
    ) -> None:
        loss_sale = ZERO
        loss_book_value = ZERO
        gain_sale = ZERO
        gain_book_value = ZERO

        loss_sale_by_suffix: dict[str, Decimal] = {}
        loss_book_value_by_suffix: dict[str, Decimal] = {}
        gain_sale_by_suffix: dict[str, Decimal] = {}
        gain_book_value_by_suffix: dict[str, Decimal] = {}

        for detail in fixed_asset_disposal_details:
            suffix = cls._fixed_asset_taxonomy_suffix(
                detail.position_code
            )

            if detail.carrying_amount > detail.net_proceeds:
                loss_sale += detail.net_proceeds
                loss_book_value += detail.carrying_amount

                loss_sale_by_suffix[suffix] = (
                    loss_sale_by_suffix.get(suffix, ZERO)
                    + detail.net_proceeds
                )
                loss_book_value_by_suffix[suffix] = (
                    loss_book_value_by_suffix.get(suffix, ZERO)
                    + detail.carrying_amount
                )

            elif detail.net_proceeds > detail.carrying_amount:
                gain_sale += detail.net_proceeds
                gain_book_value += detail.carrying_amount

                gain_sale_by_suffix[suffix] = (
                    gain_sale_by_suffix.get(suffix, ZERO)
                    + detail.net_proceeds
                )
                gain_book_value_by_suffix[suffix] = (
                    gain_book_value_by_suffix.get(suffix, ZERO)
                    + detail.carrying_amount
                )

        loss = loss_book_value - loss_sale

        if loss > ZERO:
            values[
                (_FIXED_ASSET_DISPOSAL_LOSS_CONCEPT,)
            ] = loss

            values[
                (_FIXED_ASSET_DISPOSAL_LOSS_SALE_CONCEPT,)
            ] = loss_sale

            values[
                (
                    _FIXED_ASSET_DISPOSAL_LOSS_BOOK_VALUE_CONCEPT,
                )
            ] = loss_book_value

            for suffix, amount in loss_sale_by_suffix.items():
                values[
                    (
                        f"{_FIXED_ASSET_DISPOSAL_LOSS_SALE_CONCEPT}."
                        f"{suffix}",
                    )
                ] = amount

            for suffix, amount in (
                loss_book_value_by_suffix.items()
            ):
                values[
                    (
                        f"{_FIXED_ASSET_DISPOSAL_LOSS_BOOK_VALUE_CONCEPT}."
                        f"{suffix}",
                    )
                ] = amount

        gain = gain_sale - gain_book_value

        if gain > ZERO:
            values[
                (_FIXED_ASSET_DISPOSAL_GAIN_CONCEPT,)
            ] = gain

            values[
                (_FIXED_ASSET_DISPOSAL_GAIN_SALE_CONCEPT,)
            ] = gain_sale

            values[
                (
                    _FIXED_ASSET_DISPOSAL_GAIN_BOOK_VALUE_CONCEPT,
                )
            ] = gain_book_value

            for suffix, amount in gain_sale_by_suffix.items():
                values[
                    (
                        f"{_FIXED_ASSET_DISPOSAL_GAIN_SALE_CONCEPT}."
                        f"{suffix}",
                    )
                ] = amount

            for suffix, amount in (
                gain_book_value_by_suffix.items()
            ):
                values[
                    (
                        f"{_FIXED_ASSET_DISPOSAL_GAIN_BOOK_VALUE_CONCEPT}."
                        f"{suffix}",
                    )
                ] = amount

    @staticmethod
    def _fixed_asset_taxonomy_suffix(
        position_code: str,
    ) -> str:
        for prefix, suffix in _FIXED_ASSET_TAXONOMY_SUFFIXES:
            if (
                position_code == prefix
                or position_code.startswith(
                    f"{prefix}."
                )
            ):
                return suffix

        raise ValueError(
            "unsupported fixed asset position for "
            "Taxonomy 6.9 disposal details: "
            f"{position_code}"
        )

"""Aufbereitung eines HGB-Abschlusses als GAAP-CI-Facts."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.taxonomy.concept import TaxonomyPeriodType
from openbilanz.taxonomy.context import TaxonomyContext
from openbilanz.taxonomy.fact import TaxonomyFact
from openbilanz.taxonomy.fact_builder import TaxonomyFactBuilder
from openbilanz.taxonomy.hgb_gaap_ci_mapping import (
    create_hgb_gaap_ci_mapping,
)
from openbilanz.taxonomy.mapper import TaxonomyMapper
from openbilanz.taxonomy.model import TaxonomyModel
from openbilanz.taxonomy.unit import TaxonomyUnit


@dataclass(frozen=True, slots=True)
class GaapCiStatement:
    """Vollständig aufbereitete GAAP-CI-Facts eines HGB-Abschlusses."""

    balance_sheet_facts: tuple[TaxonomyFact, ...]
    income_statement_facts: tuple[TaxonomyFact, ...]
    instant_context: TaxonomyContext
    duration_context: TaxonomyContext
    unit: TaxonomyUnit

    @property
    def facts(self) -> tuple[TaxonomyFact, ...]:
        """Liefert sämtliche GAAP-CI-Facts."""

        return self.balance_sheet_facts + self.income_statement_facts

class GaapCiStatementBuilder:
    """Überführt HGB-Abschlusswerte in GAAP-CI-Facts."""

    def __init__(
        self,
        *,
        taxonomy_model: TaxonomyModel,
        assets: FinancialStatementPosition,
        liabilities: FinancialStatementPosition,
        income_statement: FinancialStatementPosition,
    ) -> None:
        self._taxonomy_model = taxonomy_model
        self._assets = assets
        self._liabilities = liabilities
        self._income_statement = income_statement

        self._mappings = create_hgb_gaap_ci_mapping(
            assets=assets,
            liabilities=liabilities,
            income_statement=income_statement,
        )

    def build(
        self,
        *,
        amounts: Mapping[FinancialStatementPosition, Decimal],
        entity_identifier: str,
        entity_scheme: str,
        fiscal_year_start: date,
        fiscal_year_end: date,
        unit: TaxonomyUnit | None = None,
    ) -> GaapCiStatement:
        """Erzeugt GAAP-CI-Facts aus HGB-Abschlusswerten."""

        validation = self._mappings.validate(
            self._taxonomy_model
        )

        if not validation.is_valid:
            missing = ", ".join(
                validation.missing_concept_names
            )
            raise ValueError(
                "GAAP-CI mapping is not valid for the loaded taxonomy: "
                f"{missing}"
            )

        mapper = TaxonomyMapper(
            mappings=self._mappings,
            taxonomy_model=self._taxonomy_model,
        )
        fact_builder = TaxonomyFactBuilder(
            mapper=mapper
        )

        balance_positions = set(
            self._walk(self._assets)
            + self._walk(self._liabilities)
        )
        income_positions = set(
            self._walk(self._income_statement)
        )

        balance_amounts = {
            position: amount
            for position, amount in amounts.items()
            if (
                position in balance_positions
                and self._mappings.for_position(position)
                is not None
            )
        }

        income_amounts = {
            position: amount
            for position, amount in amounts.items()
            if (
                position in income_positions
                and self._mappings.for_position(position)
                is not None
            )
        }
        
        unknown_positions = set(amounts) - (
            balance_positions | income_positions
        )

        if unknown_positions:
            codes = ", ".join(
                sorted(
                    position.code
                    for position in unknown_positions
                )
            )
            raise ValueError(
                "amounts contain positions outside the HGB statement: "
                f"{codes}"
            )

        instant_context = TaxonomyContext(
            entity_identifier=entity_identifier,
            entity_scheme=entity_scheme,
            period_type=TaxonomyPeriodType.INSTANT,
            start_date=None,
            end_date=fiscal_year_end,
        )

        duration_context = TaxonomyContext(
            entity_identifier=entity_identifier,
            entity_scheme=entity_scheme,
            period_type=TaxonomyPeriodType.DURATION,
            start_date=fiscal_year_start,
            end_date=fiscal_year_end,
        )

        fact_unit = unit or TaxonomyUnit.eur()

        balance_sheet_facts = fact_builder.build(
            amounts=balance_amounts,
            context=instant_context,
            unit=fact_unit,
        )

        income_statement_facts = fact_builder.build(
            amounts=income_amounts,
            context=duration_context,
            unit=fact_unit,
        )

        return GaapCiStatement(
            balance_sheet_facts=balance_sheet_facts,
            income_statement_facts=income_statement_facts,
            instant_context=instant_context,
            duration_context=duration_context,
            unit=fact_unit,
        )
        
    @staticmethod
    def _walk(
        position: FinancialStatementPosition,
    ) -> tuple[FinancialStatementPosition, ...]:
        """Liefert eine Abschlussposition einschließlich aller Kinder."""

        result = [position]

        for child in position.children:
            result.extend(
                GaapCiStatementBuilder._walk(child)
            )

        return tuple(result)
    

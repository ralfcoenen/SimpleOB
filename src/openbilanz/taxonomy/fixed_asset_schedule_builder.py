"""Überführung des Anlagenspiegels in GAAP-CI-XBRL-Facts."""

from dataclasses import dataclass
from datetime import date

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.services.fixed_asset_schedule_service import (
    FixedAssetSchedulePosition,
)
from openbilanz.taxonomy.concept import TaxonomyConcept
from openbilanz.taxonomy.context import (
    TaxonomyContext,
    TaxonomyDimension,
)
from openbilanz.taxonomy.fact import TaxonomyFact
from openbilanz.taxonomy.mapper import TaxonomyMapper
from openbilanz.taxonomy.model import TaxonomyModel
from openbilanz.taxonomy.unit import TaxonomyUnit


@dataclass(frozen=True, slots=True)
class FixedAssetScheduleXbrl:
    """XBRL-Bestandteile des Anlagenspiegels."""

    contexts: dict[str, TaxonomyContext]
    facts: tuple[TaxonomyFact, ...]


class FixedAssetScheduleBuilder:
    """Erzeugt dimensionale GAAP-CI-Facts des Anlagenspiegels."""

    _FACT_NAMES = (
        "grossCost.beginning",
        "gross.addition",
        "gross.release",
        "accDepr.beginning",
        "accDepr.DeprPeriod.regular",
        "accDepr.release",
    )

    def __init__(
        self,
        *,
        taxonomy_model: TaxonomyModel,
        taxonomy_mapper: TaxonomyMapper,
    ) -> None:
        if not isinstance(
            taxonomy_model,
            TaxonomyModel,
        ):
            raise TypeError(
                "taxonomy_model must be a TaxonomyModel"
            )

        if not isinstance(
            taxonomy_mapper,
            TaxonomyMapper,
        ):
            raise TypeError(
                "taxonomy_mapper must be a TaxonomyMapper"
            )

        self._taxonomy_model = taxonomy_model
        self._taxonomy_mapper = taxonomy_mapper

    def build(
        self,
        *,
        positions: tuple[FixedAssetSchedulePosition, ...],
        entity_identifier: str,
        entity_scheme: str,
        fiscal_year_start: date,
        fiscal_year_end: date,
    ) -> FixedAssetScheduleXbrl:
        """Erzeugt Kontexte und Facts für den Anlagenspiegel."""

        if not isinstance(
            positions,
            tuple,
        ):
            raise TypeError(
                "positions must be a tuple"
            )

        if not all(
            isinstance(
                position,
                FixedAssetSchedulePosition,
            )
            for position in positions
        ):
            raise TypeError(
                "positions must contain only "
                "FixedAssetSchedulePosition objects"
            )

        if not isinstance(
            fiscal_year_start,
            date,
        ):
            raise TypeError(
                "fiscal_year_start must be a date"
            )

        if not isinstance(
            fiscal_year_end,
            date,
        ):
            raise TypeError(
                "fiscal_year_end must be a date"
            )

        if fiscal_year_end < fiscal_year_start:
            raise ValueError(
                "fiscal_year_end must not be before "
                "fiscal_year_start"
            )

        contexts: dict[str, TaxonomyContext] = {}
        facts: list[TaxonomyFact] = []

        unit = TaxonomyUnit.eur()

        fact_concepts = {
            fact_name: self._concept_by_name(
                fact_name
            )
            for fact_name in self._FACT_NAMES
        }

        for index, position in enumerate(
            positions,
            start=1,
        ):
            asset_concept = self._asset_concept_for(
                position.position_code
            )

            context_id = (
                f"ctx-fixed-assets-{index}"
            )

            context = TaxonomyContext(
                entity_identifier=entity_identifier,
                entity_scheme=entity_scheme,
                period_type=(
                    fact_concepts[
                        "grossCost.beginning"
                    ].period_type
                ),
                start_date=fiscal_year_start,
                end_date=fiscal_year_end,
                dimensions=(
                    TaxonomyDimension(
                        dimension_name=(
                            "de-gaap-ci:dim_taxTrans"
                        ),
                        member_name=(
                            "de-gaap-ci:dim_comBal"
                        ),
                    ),
                    TaxonomyDimension(
                        dimension_name=(
                            "de-gaap-ci:"
                            "dim_changes.nt.ass.gross"
                        ),
                        member_name=(
                            "de-gaap-ci:"
                            f"{asset_concept.name}"
                        ),
                    ),
                ),
            )

            contexts[context_id] = context

            facts.extend(
                (
                    TaxonomyFact(
                        concept=fact_concepts[
                            "grossCost.beginning"
                        ],
                        amount=(
                            position
                            .acquisition_cost_beginning
                        ),
                        context=context,
                        unit=unit,
                    ),
                    TaxonomyFact(
                        concept=fact_concepts[
                            "gross.addition"
                        ],
                        amount=position.additions,
                        context=context,
                        unit=unit,
                    ),
                    TaxonomyFact(
                        concept=fact_concepts[
                            "gross.release"
                        ],
                        amount=position.disposals,
                        context=context,
                        unit=unit,
                    ),
                    TaxonomyFact(
                        concept=fact_concepts[
                            "accDepr.beginning"
                        ],
                        amount=(
                            position
                            .accumulated_depreciation_beginning
                        ),
                        context=context,
                        unit=unit,
                    ),
                    TaxonomyFact(
                        concept=fact_concepts[
                            "accDepr.DeprPeriod.regular"
                        ],
                        amount=(
                            position
                            .depreciation_current_year
                        ),
                        context=context,
                        unit=unit,
                    ),
                    TaxonomyFact(
                        concept=fact_concepts[
                            "accDepr.release"
                        ],
                        amount=(
                            position
                            .depreciation_disposals
                        ),
                        context=context,
                        unit=unit,
                    ),
                )
            )

        return FixedAssetScheduleXbrl(
            contexts=contexts,
            facts=tuple(facts),
        )

    def _asset_concept_for(
        self,
        position_code: str,
    ) -> TaxonomyConcept:
        position = FinancialStatementPosition(
            code=position_code,
            name=position_code,
        )

        return self._taxonomy_mapper.concept_for(
            position
        )

    def _concept_by_name(
        self,
        concept_name: str,
    ) -> TaxonomyConcept:
        for concept in (
            self._taxonomy_model
            .concepts
            .concepts
        ):
            if concept.name == concept_name:
                return concept

        raise ValueError(
            "GAAP-CI taxonomy concept not found: "
            f"{concept_name}"
        )

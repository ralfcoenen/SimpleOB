"""Überführung des Anlagenspiegels in GAAP-CI-XBRL-Facts."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

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
from openbilanz.taxonomy.nil_fact import TaxonomyNilFact
from openbilanz.taxonomy.unit import TaxonomyUnit


@dataclass(frozen=True, slots=True)
class FixedAssetScheduleXbrl:
    """XBRL-Bestandteile des Anlagenspiegels."""

    contexts: dict[str, TaxonomyContext]
    facts: tuple[TaxonomyFact, ...]
    nil_facts: tuple[TaxonomyNilFact, ...]


@dataclass(frozen=True, slots=True)
class _AggregatedScheduleValues:
    """Aggregierte Bewegungswerte für eine taxonomische Anlagenposition."""

    acquisition_cost_beginning: Decimal = Decimal("0")
    additions: Decimal = Decimal("0")
    disposals: Decimal = Decimal("0")
    acquisition_cost_ending: Decimal = Decimal("0")
    accumulated_depreciation_beginning: Decimal = Decimal("0")
    depreciation_current_year: Decimal = Decimal("0")
    depreciation_disposals: Decimal = Decimal("0")
    accumulated_depreciation_ending: Decimal = Decimal("0")
    carrying_amount_ending: Decimal = Decimal("0")

    def plus(
        self,
        position: FixedAssetSchedulePosition,
    ) -> "_AggregatedScheduleValues":
        return _AggregatedScheduleValues(
            acquisition_cost_beginning=(
                self.acquisition_cost_beginning
                + position.acquisition_cost_beginning
            ),
            additions=self.additions + position.additions,
            disposals=self.disposals + position.disposals,
            acquisition_cost_ending=(
                self.acquisition_cost_ending
                + position.acquisition_cost_ending
            ),
            accumulated_depreciation_beginning=(
                self.accumulated_depreciation_beginning
                + position.accumulated_depreciation_beginning
            ),
            depreciation_current_year=(
                self.depreciation_current_year
                + position.depreciation_current_year
            ),
            depreciation_disposals=(
                self.depreciation_disposals
                + position.depreciation_disposals
            ),
            accumulated_depreciation_ending=(
                self.accumulated_depreciation_ending
                + position.accumulated_depreciation_ending
            ),
            carrying_amount_ending=(
                self.carrying_amount_ending
                + position.carrying_amount_ending
            ),
        )


class FixedAssetScheduleBuilder:
    """Erzeugt dimensionale GAAP-CI-Facts des Anlagenspiegels."""

    _NOTES_ROLE = (
        "http://www.xbrl.de/taxonomies/"
        "de-gaap-ci/role/notes"
    )

    _ASSET_CONCEPT_PREFIX = "bs.ass.fixAss"

    _FACT_NAMES = (
        "grossCost.beginning",
        "gross.addition",
        "gross.release",
        "gross",
        "accDepr.beginning",
        "accDepr.DeprPeriod.regular",
        "accDepr.DeprPeriod",
        "accDepr.release",
        "accDepr",
        "all",
    )

    # Kontrollierter Stage-9-Praxistest:
    # Die vier in Stage 8 bestätigten BAL-Bewegungsfelder plus
    # die vier diagnostisch bestätigten Pflichtkinder von
    # accDepr.DeprPeriod werden als NIL übertragen.
    _BAL_NIL_FACT_NAMES = (
        "gross.movements",
        "revaluation",
        "accDepr.addition",
        "accDepr.movements",
        "accDepr.DeprPeriod.extraordinary",
        "accDepr.DeprPeriod.impairment",
        "accDepr.DeprPeriod.EStG7g_2",
        "accDepr.DeprPeriod.EStG6b_3",
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

        if not positions:
            return FixedAssetScheduleXbrl(
                contexts={},
                facts=(),
                nil_facts=(),
            )

        fact_concepts = {
            fact_name: self._concept_by_name(
                fact_name
            )
            for fact_name in self._FACT_NAMES
        }

        nil_fact_concepts = {
            fact_name: self._concept_by_name(
                fact_name
            )
            for fact_name in self._BAL_NIL_FACT_NAMES
        }

        values_by_asset_concept = self._aggregate_by_asset_concept(
            positions
        )

        contexts: dict[str, TaxonomyContext] = {}
        facts: list[TaxonomyFact] = []
        nil_facts: list[TaxonomyNilFact] = []
        unit = TaxonomyUnit.eur()

        for index, asset_concept_name in enumerate(
            sorted(values_by_asset_concept),
            start=1,
        ):
            values = values_by_asset_concept[
                asset_concept_name
            ]
            context_id = f"ctx-fixed-assets-{index}"
            context = self._build_context(
                entity_identifier=entity_identifier,
                entity_scheme=entity_scheme,
                fiscal_year_start=fiscal_year_start,
                fiscal_year_end=fiscal_year_end,
                asset_concept_name=asset_concept_name,
                period_type=(
                    fact_concepts[
                        "grossCost.beginning"
                    ].period_type
                ),
            )
            contexts[context_id] = context

            facts.extend(
                self._facts_for_values(
                    values=values,
                    context=context,
                    unit=unit,
                    concepts=fact_concepts,
                )
            )

            nil_facts.extend(
                self._nil_facts_for_context(
                    context=context,
                    unit=unit,
                    concepts=nil_fact_concepts,
                )
            )

        return FixedAssetScheduleXbrl(
            contexts=contexts,
            facts=tuple(facts),
            nil_facts=tuple(nil_facts),
        )

    def _aggregate_by_asset_concept(
        self,
        positions: tuple[FixedAssetSchedulePosition, ...],
    ) -> dict[str, _AggregatedScheduleValues]:
        values_by_asset_concept: dict[
            str,
            _AggregatedScheduleValues,
        ] = {}

        for position in positions:
            asset_concept = self._asset_concept_for(
                position.position_code
            )

            for concept_name in self._asset_concept_and_parents(
                asset_concept
            ):
                current = values_by_asset_concept.get(
                    concept_name,
                    _AggregatedScheduleValues(),
                )
                values_by_asset_concept[
                    concept_name
                ] = current.plus(position)

        return values_by_asset_concept

    def _asset_concept_and_parents(
        self,
        asset_concept: TaxonomyConcept,
    ) -> tuple[str, ...]:
        relations = (
            self._taxonomy_model.presentation
            .relations_for_role(self._NOTES_ROLE)
        )

        parents_by_child: dict[str, tuple[str, ...]] = {}
        mutable_parents: dict[str, list[str]] = {}

        for relation in relations:
            mutable_parents.setdefault(
                relation.child_concept_id,
                [],
            ).append(relation.parent_concept_id)

        parents_by_child = {
            child_id: tuple(parent_ids)
            for child_id, parent_ids in mutable_parents.items()
        }

        concepts_by_id = {
            concept.concept_id: concept
            for concept in (
                self._taxonomy_model
                .concepts
                .concepts
            )
        }

        result: list[str] = []
        visited: set[str] = set()

        def walk(concept: TaxonomyConcept) -> None:
            if concept.concept_id in visited:
                return

            visited.add(concept.concept_id)

            if (
                not concept.abstract
                and concept.name.startswith(
                    self._ASSET_CONCEPT_PREFIX
                )
            ):
                result.append(concept.name)

            for parent_id in parents_by_child.get(
                concept.concept_id,
                (),
            ):
                parent = concepts_by_id.get(parent_id)
                if parent is not None:
                    walk(parent)

        walk(asset_concept)

        if not result:
            raise ValueError(
                "No reportable fixed-asset concept found "
                f"for taxonomy concept {asset_concept.name!r}"
            )

        return tuple(result)

    def _build_context(
        self,
        *,
        entity_identifier: str,
        entity_scheme: str,
        fiscal_year_start: date,
        fiscal_year_end: date,
        asset_concept_name: str,
        period_type,
    ) -> TaxonomyContext:
        return TaxonomyContext(
            entity_identifier=entity_identifier,
            entity_scheme=entity_scheme,
            period_type=period_type,
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
                        f"{asset_concept_name}"
                    ),
                ),
            ),
        )

    @staticmethod
    def _facts_for_values(
        *,
        values: _AggregatedScheduleValues,
        context: TaxonomyContext,
        unit: TaxonomyUnit,
        concepts: dict[str, TaxonomyConcept],
    ) -> tuple[TaxonomyFact, ...]:
        amounts = {
            "grossCost.beginning": (
                values.acquisition_cost_beginning
            ),
            "gross.addition": values.additions,
            "gross.release": values.disposals,
            "gross": values.acquisition_cost_ending,
            "accDepr.beginning": (
                values.accumulated_depreciation_beginning
            ),
            "accDepr.DeprPeriod.regular": (
                values.depreciation_current_year
            ),
            "accDepr.DeprPeriod": (
                values.depreciation_current_year
            ),
            "accDepr.release": (
                values.depreciation_disposals
            ),
            "accDepr": (
                values.accumulated_depreciation_ending
            ),
            "all": values.carrying_amount_ending,
        }

        return tuple(
            TaxonomyFact(
                concept=concepts[concept_name],
                amount=amounts[concept_name],
                context=context,
                unit=unit,
            )
            for concept_name in FixedAssetScheduleBuilder._FACT_NAMES
        )

    @staticmethod
    def _nil_facts_for_context(
        *,
        context: TaxonomyContext,
        unit: TaxonomyUnit,
        concepts: dict[str, TaxonomyConcept],
    ) -> tuple[TaxonomyNilFact, ...]:
        """Erzeugt die acht kontrollierten Stage-9-BAL-NIL-Facts."""

        return tuple(
            TaxonomyNilFact(
                concept=concepts[concept_name],
                context=context,
                unit=unit,
            )
            for concept_name in (
                FixedAssetScheduleBuilder._BAL_NIL_FACT_NAMES
            )
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

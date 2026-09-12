"""HGBM-Ergänzung eines handelsrechtlichen Anlagenspiegels."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from openbilanz.taxonomy.context import (
    TaxonomyContext,
    TaxonomyDimension,
)
from openbilanz.taxonomy.fact import TaxonomyFact
from openbilanz.taxonomy.nil_fact import TaxonomyNilFact


@dataclass(frozen=True, slots=True)
class HgbmFixedAssetScheduleXbrl:
    """Zusätzliche HGBM-XBRL-Bestandteile des Anlagenspiegels."""

    contexts: dict[str, TaxonomyContext]
    facts: tuple[TaxonomyFact, ...]
    nil_facts: tuple[TaxonomyNilFact, ...]


class HgbmFixedAssetScheduleBuilder:
    """Erzeugt diffComToTaxBal und taxBal aus einem comBal-Anlagenspiegel.

    Der Builder berechnet keine steuerliche AfA.

    Er erhält ausschließlich die bereits fachlich ermittelten
    AfA-Differenzen zwischen Steuerbilanz und Handelsbilanz:

    current_depreciation_difference
        Steuerliche AfA minus HGB-AfA des laufenden Geschäftsjahres.

    previous_depreciation_difference
        Kumulierte steuerliche AfA minus kumulierte HGB-AfA,
        die bereits zu Beginn des Geschäftsjahres aus Vorjahren bestand.

    Daraus werden die real mit ERiC bestätigten Taxonomie-6.9-
    Differenzwerte für Erstjahr und Folgejahr erzeugt.
    """

    _TAX_TRANS_DIMENSION = "de-gaap-ci:dim_taxTrans"
    _COMMERCIAL_MEMBER = "de-gaap-ci:dim_comBal"
    _DIFFERENCE_MEMBER = "de-gaap-ci:dim_diffComToTaxBal"
    _TAX_MEMBER = "de-gaap-ci:dim_taxBal"

    @classmethod
    def build(
        cls,
        *,
        commercial_contexts: dict[str, TaxonomyContext],
        commercial_facts: tuple[TaxonomyFact, ...],
        commercial_nil_facts: tuple[TaxonomyNilFact, ...],
        current_depreciation_difference: Decimal,
        previous_depreciation_difference: Decimal = Decimal("0.00"),
    ) -> HgbmFixedAssetScheduleXbrl:
        """Erzeugt die zusätzlichen HGBM-Dimensionen."""

        if not isinstance(commercial_contexts, dict):
            raise TypeError(
                "commercial_contexts must be a dict"
            )

        if not isinstance(commercial_facts, tuple):
            raise TypeError(
                "commercial_facts must be a tuple"
            )

        if not all(
            isinstance(fact, TaxonomyFact)
            for fact in commercial_facts
        ):
            raise TypeError(
                "commercial_facts must contain only TaxonomyFact"
            )

        if not isinstance(commercial_nil_facts, tuple):
            raise TypeError(
                "commercial_nil_facts must be a tuple"
            )

        if not all(
            isinstance(fact, TaxonomyNilFact)
            for fact in commercial_nil_facts
        ):
            raise TypeError(
                "commercial_nil_facts must contain only TaxonomyNilFact"
            )

        if not isinstance(
            current_depreciation_difference,
            Decimal,
        ):
            raise TypeError(
                "current_depreciation_difference must be a Decimal"
            )

        if not isinstance(
            previous_depreciation_difference,
            Decimal,
        ):
            raise TypeError(
                "previous_depreciation_difference must be a Decimal"
            )

        current_difference = current_depreciation_difference.quantize(
            Decimal("0.01")
        )
        previous_difference = previous_depreciation_difference.quantize(
            Decimal("0.01")
        )

        if (
            current_difference == Decimal("0.00")
            and previous_difference == Decimal("0.00")
        ):
            raise ValueError(
                "at least one depreciation difference must be non-zero"
            )

        difference_context_by_commercial: dict[
            TaxonomyContext,
            TaxonomyContext,
        ] = {}
        tax_context_by_commercial: dict[
            TaxonomyContext,
            TaxonomyContext,
        ] = {}
        contexts: dict[str, TaxonomyContext] = {}

        for context_id, commercial_context in commercial_contexts.items():
            if not isinstance(context_id, str) or not context_id.strip():
                raise ValueError(
                    "commercial context ids must be non-blank strings"
                )

            if not isinstance(commercial_context, TaxonomyContext):
                raise TypeError(
                    "commercial_contexts values must be "
                    "TaxonomyContext"
                )

            cls._validate_commercial_context(
                commercial_context
            )

            difference_context = cls._replace_tax_member(
                context=commercial_context,
                member_name=cls._DIFFERENCE_MEMBER,
            )
            tax_context = cls._replace_tax_member(
                context=commercial_context,
                member_name=cls._TAX_MEMBER,
            )

            difference_context_by_commercial[
                commercial_context
            ] = difference_context
            tax_context_by_commercial[
                commercial_context
            ] = tax_context

            contexts[
                f"{context_id}-diff-tax"
            ] = difference_context
            contexts[
                f"{context_id}-tax"
            ] = tax_context

        facts: list[TaxonomyFact] = []

        for commercial_fact in commercial_facts:
            difference_context = (
                difference_context_by_commercial.get(
                    commercial_fact.context
                )
            )
            tax_context = tax_context_by_commercial.get(
                commercial_fact.context
            )

            if difference_context is None or tax_context is None:
                raise ValueError(
                    "commercial fact references a context "
                    "not present in commercial_contexts"
                )

            difference = cls._difference_for_concept(
                concept_name=commercial_fact.concept.name,
                current_depreciation_difference=(
                    current_difference
                ),
                previous_depreciation_difference=(
                    previous_difference
                ),
            )

            facts.append(
                TaxonomyFact(
                    concept=commercial_fact.concept,
                    amount=difference,
                    context=difference_context,
                    unit=commercial_fact.unit,
                    decimals=commercial_fact.decimals,
                )
            )
            facts.append(
                TaxonomyFact(
                    concept=commercial_fact.concept,
                    amount=(
                        commercial_fact.amount
                        + difference
                    ),
                    context=tax_context,
                    unit=commercial_fact.unit,
                    decimals=commercial_fact.decimals,
                )
            )

        nil_facts: list[TaxonomyNilFact] = []

        for commercial_nil_fact in commercial_nil_facts:
            difference_context = (
                difference_context_by_commercial.get(
                    commercial_nil_fact.context
                )
            )
            tax_context = tax_context_by_commercial.get(
                commercial_nil_fact.context
            )

            if difference_context is None or tax_context is None:
                raise ValueError(
                    "commercial NIL fact references a context "
                    "not present in commercial_contexts"
                )

            nil_facts.append(
                TaxonomyNilFact(
                    concept=commercial_nil_fact.concept,
                    context=difference_context,
                    unit=commercial_nil_fact.unit,
                )
            )
            nil_facts.append(
                TaxonomyNilFact(
                    concept=commercial_nil_fact.concept,
                    context=tax_context,
                    unit=commercial_nil_fact.unit,
                )
            )

        return HgbmFixedAssetScheduleXbrl(
            contexts=contexts,
            facts=tuple(facts),
            nil_facts=tuple(nil_facts),
        )

    @staticmethod
    def _difference_for_concept(
        *,
        concept_name: str,
        current_depreciation_difference: Decimal,
        previous_depreciation_difference: Decimal,
    ) -> Decimal:
        cumulative_depreciation_difference = (
            previous_depreciation_difference
            + current_depreciation_difference
        )

        if concept_name == "accDepr.beginning":
            return previous_depreciation_difference

        if concept_name in {
            "accDepr.DeprPeriod.regular",
            "accDepr.DeprPeriod",
        }:
            return current_depreciation_difference

        if concept_name == "accDepr":
            return cumulative_depreciation_difference

        if concept_name == "all":
            return -cumulative_depreciation_difference

        return Decimal("0.00")

    @classmethod
    def _validate_commercial_context(
        cls,
        context: TaxonomyContext,
    ) -> None:
        tax_dimensions = tuple(
            dimension
            for dimension in context.dimensions
            if (
                dimension.dimension_name
                == cls._TAX_TRANS_DIMENSION
            )
        )

        if len(tax_dimensions) != 1:
            raise ValueError(
                "commercial BAL context must contain exactly "
                "one dim_taxTrans dimension"
            )

        if (
            tax_dimensions[0].member_name
            != cls._COMMERCIAL_MEMBER
        ):
            raise ValueError(
                "commercial BAL context must use dim_comBal"
            )

    @classmethod
    def _replace_tax_member(
        cls,
        *,
        context: TaxonomyContext,
        member_name: str,
    ) -> TaxonomyContext:
        dimensions = tuple(
            TaxonomyDimension(
                dimension_name=dimension.dimension_name,
                member_name=(
                    member_name
                    if (
                        dimension.dimension_name
                        == cls._TAX_TRANS_DIMENSION
                    )
                    else dimension.member_name
                ),
            )
            for dimension in context.dimensions
        )

        return TaxonomyContext(
            entity_identifier=context.entity_identifier,
            entity_scheme=context.entity_scheme,
            period_type=context.period_type,
            start_date=context.start_date,
            end_date=context.end_date,
            dimensions=dimensions,
        )

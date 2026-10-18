"""Zuordnung interner Abschlusspositionen zu Taxonomie-Concepts."""

from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.taxonomy.concept import TaxonomyConcept
from simpleob.taxonomy.mapping_set import TaxonomyMappingSet
from simpleob.taxonomy.model import TaxonomyModel


class TaxonomyMapper:
    """Ordnet interne Abschlusspositionen Taxonomie-Concepts zu."""

    def __init__(
        self,
        mappings: TaxonomyMappingSet,
        taxonomy_model: TaxonomyModel,
    ) -> None:
        if not isinstance(
            mappings,
            TaxonomyMappingSet,
        ):
            raise TypeError(
                "mappings must be a TaxonomyMappingSet"
            )

        if not isinstance(
            taxonomy_model,
            TaxonomyModel,
        ):
            raise TypeError(
                "taxonomy_model must be a TaxonomyModel"
            )

        self._mappings = mappings
        self._taxonomy_model = taxonomy_model

    def concept_for(
        self,
        position: FinancialStatementPosition,
    ) -> TaxonomyConcept:
        """Liefert das Taxonomie-Concept einer Abschlussposition."""

        rule = self._mappings.for_position(
            position
        )

        if rule is None:
            raise ValueError(
                "no taxonomy mapping found for position "
                f"{position.code}"
            )

        for concept in self._taxonomy_model.concepts.concepts:
            if concept.name == rule.concept_name:
                return concept

        raise ValueError(
            "mapped taxonomy concept not found: "
            f"{rule.concept_name}"
        )
"""Zuordnung interner Abschlusspositionen zu Taxonomie-Concepts."""

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.taxonomy.concept import TaxonomyConcept
from openbilanz.taxonomy.mapping_set import TaxonomyMappingSet


class TaxonomyMapper:
    """Ordnet interne Abschlusspositionen Taxonomie-Concepts zu."""

    def __init__(
        self,
        mappings: TaxonomyMappingSet,
    ) -> None:
        if not isinstance(
            mappings,
            TaxonomyMappingSet,
        ):
            raise TypeError(
                "mappings must be a TaxonomyMappingSet"
            )

        self._mappings = mappings

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

        return rule.concept


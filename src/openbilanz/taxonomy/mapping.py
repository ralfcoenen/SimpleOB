"""Zuordnung interner Abschlusspositionen zu Taxonomie-Concepts."""

from dataclasses import dataclass

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.taxonomy.concept import TaxonomyConcept


@dataclass(frozen=True, slots=True)
class TaxonomyMappingRule:
    """Ordnet eine interne Abschlussposition einem Taxonomie-Concept zu."""

    position: FinancialStatementPosition
    concept: TaxonomyConcept


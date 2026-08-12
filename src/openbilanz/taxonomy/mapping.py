"""Zuordnung interner Abschlusspositionen zu Taxonomie-Concepts."""

from dataclasses import dataclass

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)


@dataclass(frozen=True, slots=True)
class TaxonomyMappingRule:
    """Ordnet eine interne Abschlussposition einem Taxonomie-Concept zu."""

    position: FinancialStatementPosition
    concept_name: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.position,
            FinancialStatementPosition,
        ):
            raise TypeError(
                "position must be a FinancialStatementPosition"
            )

        if not isinstance(
            self.concept_name,
            str,
        ):
            raise TypeError(
                "concept_name must be a string"
            )

        if not self.concept_name.strip():
            raise ValueError(
                "concept_name must not be blank"
            )

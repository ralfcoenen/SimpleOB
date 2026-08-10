"""Sammlung von Taxonomie-Zuordnungen."""

from dataclasses import dataclass

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.taxonomy.mapping import TaxonomyMappingRule


@dataclass(frozen=True, slots=True)
class TaxonomyMappingSet:
    """Enthält Zuordnungen zu Taxonomie-Concepts."""

    rules: tuple[TaxonomyMappingRule, ...]

    def __post_init__(self) -> None:
        if not isinstance(
            self.rules,
            tuple,
        ):
            raise TypeError(
                "rules must be a tuple"
            )

        if not all(
            isinstance(
                rule,
                TaxonomyMappingRule,
            )
            for rule in self.rules
        ):
            raise TypeError(
                "rules must contain only "
                "TaxonomyMappingRule objects"
            )
        position_codes = [
            rule.position.code
            for rule in self.rules
        ]

        if len(position_codes) != len(set(position_codes)):
            raise ValueError(
                "duplicate position codes are not allowed"
            )

    def for_position(
        self,
        position: FinancialStatementPosition,
    ) -> TaxonomyMappingRule | None:
        """Liefert die Zuordnung einer Abschlussposition."""

        for rule in self.rules:
            if rule.position.code == position.code:
                return rule

        return None


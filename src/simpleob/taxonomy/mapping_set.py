"""Sammlung von Taxonomie-Zuordnungen."""

from dataclasses import dataclass

from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.taxonomy.mapping import TaxonomyMappingRule
from simpleob.taxonomy.model import TaxonomyModel


@dataclass(frozen=True, slots=True)
class MappingValidationResult:
    """Ergebnis der Prüfung eines Mapping-Sets gegen eine Taxonomie."""

    valid_count: int
    missing_count: int
    missing_concept_names: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        """Gibt an, ob alle Mapping-Ziele vorhanden sind."""

        return self.missing_count == 0

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

    def missing_concept_names(
        self,
        taxonomy_model: TaxonomyModel,
    ) -> tuple[str, ...]:
        """Liefert Mapping-Ziele, die in der Taxonomie nicht existieren."""

        if not isinstance(
            taxonomy_model,
            TaxonomyModel,
        ):
            raise TypeError(
                "taxonomy_model must be a TaxonomyModel"
            )

        available_names = {
            concept.name
            for concept in taxonomy_model.concepts.concepts
        }

        missing_names = {
            rule.concept_name
            for rule in self.rules
            if rule.concept_name not in available_names
        }

        return tuple(
            sorted(missing_names)
        )
        
    def validate(
        self,
        taxonomy_model: TaxonomyModel,
    ) -> MappingValidationResult:
        """Prüft die Mapping-Ziele gegen eine Taxonomie."""

        missing_names = self.missing_concept_names(
            taxonomy_model
        )

        missing_name_set = set(
            missing_names
        )

        missing_count = sum(
            1
            for rule in self.rules
            if rule.concept_name in missing_name_set
        )

        return MappingValidationResult(
            valid_count=len(self.rules) - missing_count,
            missing_count=missing_count,
            missing_concept_names=missing_names,
        )
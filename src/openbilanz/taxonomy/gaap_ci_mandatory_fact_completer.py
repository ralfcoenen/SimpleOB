"""Vervollständigung verpflichtender GAAP-CI-Facts."""

from openbilanz.taxonomy.concept import (
    TaxonomyPeriodType,
)
from openbilanz.taxonomy.context import TaxonomyContext
from openbilanz.taxonomy.fact import TaxonomyFact
from openbilanz.taxonomy.fiscal_requirement_reader import (
    FiscalConceptRequirement,
    FiscalRequirement,
)
from openbilanz.taxonomy.model import TaxonomyModel
from openbilanz.taxonomy.nil_fact import TaxonomyNilFact
from openbilanz.taxonomy.unit import TaxonomyUnit


class GaapCiMandatoryFactCompleter:
    """Erzeugt NIL-Facts für fehlende verpflichtende GAAP-CI-Concepts."""

    def __init__(
        self,
        *,
        taxonomy_model: TaxonomyModel,
    ) -> None:
        if not isinstance(
            taxonomy_model,
            TaxonomyModel,
        ):
            raise TypeError(
                "taxonomy_model must be a TaxonomyModel"
            )

        self._taxonomy_model = taxonomy_model

    def build_missing_nil_facts(
        self,
        *,
        requirements: tuple[
            FiscalConceptRequirement,
            ...,
        ],
        existing_facts: tuple[
            TaxonomyFact,
            ...,
        ],
        instant_context: TaxonomyContext,
        duration_context: TaxonomyContext,
        unit: TaxonomyUnit,
        active_report_element_roles: tuple[str, ...] | None = None,
    ) -> tuple[TaxonomyNilFact, ...]:
        """Erzeugt NIL-Facts für fehlende KSt-relevante Mussfelder."""

        if (
            active_report_element_roles is not None
            and not isinstance(
                active_report_element_roles,
                tuple,
            )
        ):
            raise TypeError(
                "active_report_element_roles must be a tuple or None"
            )

        existing_concept_names = {
            fact.concept.name
            for fact in existing_facts
        }

        nil_facts: list[TaxonomyNilFact] = []

        for requirement in requirements:
            if not requirement.legal_form_kst:
                continue

            if requirement.requirement not in {
                FiscalRequirement.REQUIRED,
                FiscalRequirement.SUM_REQUIRED,
            }:
                continue

            if requirement.concept_name in existing_concept_names:
                continue

            concept = next(
                (
                    candidate
                    for candidate
                    in self._taxonomy_model.concepts.concepts
                    if candidate.name
                    == requirement.concept_name
                ),
                None,
            )

            if concept is None:
                raise ValueError(
                    "mandatory taxonomy concept not found: "
                    f"{requirement.concept_name}"
                )

            if (
                active_report_element_roles is not None
                and not self._belongs_to_active_report_element(
                    concept_id=concept.concept_id,
                    active_report_element_roles=(
                        active_report_element_roles
                    ),
                )
            ):
                continue

            if not concept.is_numeric:
                raise ValueError(
                    "mandatory taxonomy concept is not numeric: "
                    f"{concept.name}"
                )

            if concept.abstract:
                raise ValueError(
                    "mandatory taxonomy concept is abstract: "
                    f"{concept.name}"
                )

            if not concept.nillable:
                raise ValueError(
                    "mandatory taxonomy concept is not nillable: "
                    f"{concept.name}"
                )

            if concept.period_type is TaxonomyPeriodType.INSTANT:
                context = instant_context
            elif concept.period_type is TaxonomyPeriodType.DURATION:
                context = duration_context
            else:
                raise ValueError(
                    "mandatory taxonomy concept has unknown "
                    f"period type: {concept.name}"
                )

            nil_facts.append(
                TaxonomyNilFact(
                    concept=concept,
                    context=context,
                    unit=unit,
                )
            )

        return tuple(nil_facts)

    def _belongs_to_active_report_element(
        self,
        *,
        concept_id: str,
        active_report_element_roles: tuple[str, ...],
    ) -> bool:
        """Prüft die Presentation-Zugehörigkeit zu einem aktiven Berichtsteil."""

        active_roles = set(
            active_report_element_roles
        )

        return any(
            relation.role_uri in active_roles
            and (
                relation.parent_concept_id == concept_id
                or relation.child_concept_id == concept_id
            )
            for relation in self._taxonomy_model.presentation.relations
        )

"""Fachliche Anforderungsregeln für GCD-Concepts."""

from dataclasses import dataclass
from enum import Enum


class GcdRequirement(Enum):
    """Fachliche Relevanz eines GCD-Concepts."""

    REQUIRED = "required"
    CONDITIONAL = "conditional"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class GcdRequirementPolicy:
    """Klassifiziert GCD-Concepts für einen Berichtsfall."""

    requirements: dict[str, GcdRequirement]

    @classmethod
    def standard_corporation(
        cls,
    ) -> "GcdRequirementPolicy":
        """Liefert die Regeln für eine normale UG/GmbH."""

        return cls(
            requirements={
                "genInfo.company.id.shareholder": (
                    GcdRequirement.REQUIRED
                ),
                "genInfo.company.id.idNo": (
                    GcdRequirement.REQUIRED
                ),
                "genInfo.report.id.accordingTo": (
                    GcdRequirement.NOT_APPLICABLE
                ),
                "genInfo.company.id.domesticBranchOfForeignCompany": (
                    GcdRequirement.CONDITIONAL
                ),
                "genInfo.company.id.entityWithTaxablePurposeBusiness": (
                    GcdRequirement.CONDITIONAL
                ),
            }
        )

    def requirement_for(
        self,
        concept_name: str,
    ) -> GcdRequirement:
        """Liefert die fachliche Einstufung eines GCD-Concepts."""

        if not isinstance(
            concept_name,
            str,
        ):
            raise TypeError(
                "concept_name must be a string"
            )

        if not concept_name.strip():
            raise ValueError(
                "concept_name must not be blank"
            )

        try:
            return self.requirements[
                concept_name
            ]
        except KeyError as exc:
            raise KeyError(
                "GCD requirement not defined: "
                f"{concept_name}"
            ) from exc

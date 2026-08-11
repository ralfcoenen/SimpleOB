"""Adapter für die Nutzung von Arelle."""

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from arelle import XbrlConst
from arelle.api.Session import Session
from arelle.RuntimeOptions import RuntimeOptions

from openbilanz.taxonomy.concept import (
    TaxonomyBalance,
    TaxonomyConcept,
    TaxonomyPeriodType,
)
from openbilanz.taxonomy.concept_set import TaxonomyConceptSet
from openbilanz.taxonomy.label import (
    TaxonomyLabel,
    TaxonomyLabelRole,
)
from openbilanz.taxonomy.label_set import TaxonomyLabelSet
from openbilanz.taxonomy.model import TaxonomyModel
from openbilanz.taxonomy.presentation import (
    TaxonomyPresentationRelation,
)
from openbilanz.taxonomy.presentation_set import (
    TaxonomyPresentationSet,
)


@dataclass(frozen=True, slots=True)
class ArelleTaxonomy:
    """Kleine Openbilanz-Sicht auf eine von Arelle geladene Taxonomie."""

    concept_count: int
    namespaces: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ArelleValidationResult:
    """Ergebnis einer Arelle-Validierung."""

    is_valid: bool
    errors: tuple[str, ...]


class ArelleAdapter:
    """Kapselt den Zugriff auf die Arelle-XBRL-Engine."""

    def __init__(self) -> None:
        self._session = Session()
        self._session.__enter__()

    def load_taxonomy(
        self,
        entry_point: Path,
    ) -> ArelleTaxonomy:
        """Lädt eine Taxonomie über Arelle."""

        model_xbrl = self._load_model_xbrl(
            entry_point
        )

        namespaces = tuple(
            sorted(
                {
                    str(qname.namespaceURI)
                    for qname in model_xbrl.qnameConcepts
                    if qname.namespaceURI
                }
            )
        )

        return ArelleTaxonomy(
            concept_count=len(
                model_xbrl.qnameConcepts
            ),
            namespaces=namespaces,
        )

    def validate(
        self,
        entry_point: Path,
    ) -> ArelleValidationResult:
        """Validiert eine Taxonomie oder XBRL-Datei über Arelle."""

        options = RuntimeOptions(
            entrypointFile=str(entry_point),
            internetConnectivity="offline",
            keepOpen=True,
            validate=True,
            logFile="logToStructuredMessage",
        )

        self._session.run(options)

        models = self._session.get_models()

        if not models:
            raise RuntimeError(
                "Arelle could not load document"
            )

        model_xbrl = models[-1]

        errors = tuple(
            str(error)
            for error in model_xbrl.errors
        )

        return ArelleValidationResult(
            is_valid=not errors,
            errors=errors,
        )

    def concept(
        self,
        entry_point: Path,
        name: str,
    ) -> TaxonomyConcept | None:
        """Lädt ein Concept und überführt es ins Openbilanz-Modell."""

        model_xbrl = self._load_model_xbrl(
            entry_point
        )

        for model_concept in model_xbrl.qnameConcepts.values():
            if not (
                model_concept.isItem
                or model_concept.isTuple
            ):
                continue

            if model_concept.id is None:
                continue

            if model_concept.name != name:
                continue

            return self._convert_concept(
                model_concept
            )

        return None

    def concepts(
        self,
        entry_point: Path,
    ) -> TaxonomyConceptSet:
        """Lädt relevante Concepts einer Taxonomie über Arelle."""

        model_xbrl = self._load_model_xbrl(
            entry_point
        )

        return self._concepts_from_model(
            model_xbrl
        )

    def label(
        self,
        entry_point: Path,
        name: str,
        *,
        language: str = "de",
    ) -> TaxonomyLabel | None:
        """Liefert das Standardlabel eines Concepts über Arelle."""

        model_xbrl = self._load_model_xbrl(
            entry_point
        )

        role_uri = (
            "http://www.xbrl.org/2003/role/label"
        )

        for model_concept in model_xbrl.qnameConcepts.values():
            if not (
                model_concept.isItem
                or model_concept.isTuple
            ):
                continue

            if model_concept.id is None:
                continue

            if model_concept.name != name:
                continue

            text = model_concept.label(
                preferredLabel=role_uri,
                lang=language,
                fallbackToQname=False,
            )

            if text is None:
                return None

            return TaxonomyLabel(
                concept_id=model_concept.id,
                text=text,
                role=TaxonomyLabelRole.LABEL,
                role_uri=role_uri,
                language=language,
            )

        return None

    def labels(
        self,
        entry_point: Path,
        *,
        language: str = "de",
    ) -> TaxonomyLabelSet:
        """Lädt Standardlabels einer Taxonomie über Arelle."""

        model_xbrl = self._load_model_xbrl(
            entry_point
        )

        return self._labels_from_model(
            model_xbrl,
            language=language,
        )

    def presentation(
        self,
        entry_point: Path,
    ) -> TaxonomyPresentationSet:
        """Lädt Presentation-Beziehungen einer Taxonomie über Arelle."""

        model_xbrl = self._load_model_xbrl(
            entry_point
        )

        return self._presentation_from_model(
            model_xbrl
        )

    def model(
        self,
        entry_point: Path,
    ) -> TaxonomyModel:
        """Baut ein vollständiges TaxonomyModel aus Arelle-Daten."""

        model_xbrl = self._load_model_xbrl(
            entry_point
        )

        return TaxonomyModel(
            concepts=self._concepts_from_model(
                model_xbrl
            ),
            labels=self._labels_from_model(
                model_xbrl
            ),
            presentation=self._presentation_from_model(
                model_xbrl
            ),
        )

    def _load_model_xbrl(
        self,
        entry_point: Path,
    ):
        """Lädt ein Arelle-ModelXbrl."""

        options = RuntimeOptions(
            entrypointFile=str(entry_point),
            internetConnectivity="offline",
            keepOpen=True,
        )

        self._session.run(options)

        models = self._session.get_models()

        if not models:
            raise RuntimeError(
                "Arelle could not load taxonomy"
            )

        return models[-1]

    def _convert_concept(
        self,
        model_concept,
    ) -> TaxonomyConcept:
        """Überführt ein Arelle-Concept ins Openbilanz-Modell."""

        period_type = TaxonomyPeriodType.UNKNOWN

        if model_concept.periodType == "instant":
            period_type = TaxonomyPeriodType.INSTANT
        elif model_concept.periodType == "duration":
            period_type = TaxonomyPeriodType.DURATION

        balance = TaxonomyBalance.NONE

        if model_concept.balance == "debit":
            balance = TaxonomyBalance.DEBIT
        elif model_concept.balance == "credit":
            balance = TaxonomyBalance.CREDIT

        return TaxonomyConcept(
            name=model_concept.name,
            concept_id=model_concept.id,
            type_name=(
                str(model_concept.typeQname)
                if model_concept.typeQname is not None
                else None
            ),
            substitution_group=(
                str(model_concept.substitutionGroupQname)
                if model_concept.substitutionGroupQname
                is not None
                else None
            ),
            period_type=period_type,
            balance=balance,
            abstract=bool(
                model_concept.isAbstract
            ),
            nillable=bool(
                model_concept.isNillable
            ),
        )

    def _concepts_from_model(
        self,
        model_xbrl,
    ) -> TaxonomyConceptSet:
        """Überführt relevante XBRL-Concepts in ein ConceptSet."""

        concepts = tuple(
            self._convert_concept(
                model_concept
            )
            for model_concept
            in model_xbrl.qnameConcepts.values()
            if (
                (
                    model_concept.isItem
                    or model_concept.isTuple
                )
                and model_concept.id is not None
            )
        )

        return TaxonomyConceptSet(
            concepts=concepts
        )

    def _labels_from_model(
        self,
        model_xbrl,
        *,
        language: str = "de",
    ) -> TaxonomyLabelSet:
        """Überführt Standardlabels in ein LabelSet."""

        role_uri = (
            "http://www.xbrl.org/2003/role/label"
        )

        labels: list[TaxonomyLabel] = []

        for model_concept in model_xbrl.qnameConcepts.values():
            if not (
                model_concept.isItem
                or model_concept.isTuple
            ):
                continue

            if model_concept.id is None:
                continue

            text = model_concept.label(
                preferredLabel=role_uri,
                lang=language,
                fallbackToQname=False,
            )

            if text is None:
                continue

            labels.append(
                TaxonomyLabel(
                    concept_id=model_concept.id,
                    text=text,
                    role=TaxonomyLabelRole.LABEL,
                    role_uri=role_uri,
                    language=language,
                )
            )

        return TaxonomyLabelSet(
            labels=tuple(labels)
        )

    def _presentation_from_model(
        self,
        model_xbrl,
    ) -> TaxonomyPresentationSet:
        """Überführt Presentation-Beziehungen in ein PresentationSet."""

        relationship_set = model_xbrl.relationshipSet(
            XbrlConst.parentChild
        )

        relations: list[
            TaxonomyPresentationRelation
        ] = []

        for relationship in relationship_set.modelRelationships:
            parent = relationship.fromModelObject
            child = relationship.toModelObject

            if parent is None or child is None:
                continue

            if parent.id is None or child.id is None:
                continue

            relations.append(
                TaxonomyPresentationRelation(
                    parent_concept_id=parent.id,
                    child_concept_id=child.id,
                    order=Decimal(
                        str(relationship.order)
                    ),
                    role_uri=relationship.linkrole,
                    preferred_label_role_uri=(
                        relationship.preferredLabel
                    ),
                )
            )

        return TaxonomyPresentationSet(
            relations=tuple(relations)
        )

    def close(self) -> None:
        """Schließt die Arelle-Session."""

        if self._session is not None:
            self._session.__exit__(
                None,
                None,
                None,
            )
            self._session = None

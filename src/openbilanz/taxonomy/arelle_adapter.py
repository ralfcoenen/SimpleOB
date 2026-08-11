"""Adapter für die Nutzung von Arelle."""

from dataclasses import dataclass
from pathlib import Path

from arelle.api.Session import Session
from arelle.RuntimeOptions import RuntimeOptions


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

        model_xbrl = models[-1]

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

    def close(self) -> None:
        """Schließt die Arelle-Session."""

        if self._session is not None:
            self._session.__exit__(
                None,
                None,
                None,
            )
            self._session = None

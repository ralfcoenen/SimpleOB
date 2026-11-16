"""Fachliche und technische Fehler beim Taxonomieabgleich."""


class TaxonomyModelNotInstalledError(FileNotFoundError):
    """Das benötigte Taxonomiemodell ist lokal nicht installiert."""


class TaxonomyModelLoadError(RuntimeError):
    """Das installierte Taxonomiemodell konnte nicht geladen werden."""


class TaxonomyConceptNotFoundError(ValueError):
    """Ein Taxonomie-Concept ist im geladenen Modell nicht vorhanden."""


class CalculationPathNotFoundError(ValueError):
    """Zwischen HGB-Position und Concept existiert kein Calculation-Pfad."""


class AmbiguousCalculationPathError(ValueError):
    """Zwischen HGB-Position und Concept existieren mehrere Pfade."""

"""
Domänenspezifische Ausnahmen.
"""


class DomainError(Exception):
    """Basisklasse aller fachlichen Fehler."""


class UnknownAccountError(DomainError):
    """Eine Buchung verwendet ein unbekanntes Konto."""
    
  

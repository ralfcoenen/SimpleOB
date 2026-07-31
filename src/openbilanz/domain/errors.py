"""
Domänenspezifische Ausnahmen.
"""


class DomainError(Exception):
    """Basisklasse aller fachlichen Fehler."""


class UnknownAccountError(DomainError):
    """Eine Buchung verwendet ein unbekanntes Konto."""
    
class UnbalancedBookingError(DomainError):
    """Wird ausgelöst, wenn eine Buchung nicht ausgeglichen ist."""  

"""
Domänenspezifische Ausnahmen.
"""


class DomainError(Exception):
    """Basisklasse für fachliche Fehler."""


class DuplicateBookingError(DomainError):
    """Wird ausgelöst, wenn eine Buchung bereits im Journal enthalten ist."""


class UnbalancedBookingError(DomainError):
    """Wird ausgelöst, wenn eine Buchung nicht ausgeglichen ist."""


class UnknownAccountError(DomainError):
    """Wird ausgelöst, wenn ein Konto nicht bekannt ist."""

class DomainError(Exception):
    """Basisklasse aller fachlichen Fehler."""


class UnknownAccountError(DomainError):
    """Eine Buchung verwendet ein unbekanntes Konto."""
    
class UnbalancedBookingError(DomainError):
    """Wird ausgelöst, wenn eine Buchung nicht ausgeglichen ist."""  
    


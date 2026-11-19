"""
Domänenspezifische Ausnahmen.
"""


class DomainError(Exception):
    """Basisklasse für fachliche Fehler."""


class DuplicateBookingError(DomainError):
    """Wird ausgelöst, wenn eine Buchung bereits im Journal enthalten ist."""


class UnbalancedBookingError(DomainError):
    """Wird ausgelöst, wenn eine Buchung nicht ausgeglichen ist."""


class DomainError(Exception):
    """Basisklasse aller fachlichen Fehler."""


class UnknownAccountError(DomainError):
    """Eine Buchung verwendet ein unbekanntes Konto."""


class UnsupportedPersonAccountBalanceError(ValueError):
    """Personenkontensalden sind in dieser HGB-Auswertung noch nicht integriert."""


class InvalidPersonAccountClassificationError(ValueError):
    """Die Klassifikation oder Stammdaten eines Personenkontos sind widersprüchlich."""

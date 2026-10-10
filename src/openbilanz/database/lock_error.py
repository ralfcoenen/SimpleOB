"""Fehler bei konkurrierenden Datenbankzugriffen."""


class DatabaseLockError(RuntimeError):
    """Eine benötigte Datenbanksperre konnte nicht erworben werden."""

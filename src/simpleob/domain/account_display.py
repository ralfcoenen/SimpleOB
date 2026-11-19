"""Gemeinsame Kontendarstellung für Auswahlfelder und Buchungszeilen."""

from simpleob.domain.account import Account
from simpleob.domain.person_account_role import PersonAccountRole


def account_display_name(account: Account) -> str:
    """Liefert Kontonummer, Personenkontenrolle und Kontoname."""

    if account.person_account_role is PersonAccountRole.DEBITOR:
        return f"{account.number} – Debitor – {account.name}"
    if account.person_account_role is PersonAccountRole.KREDITOR:
        return f"{account.number} – Kreditor – {account.name}"
    return f"{account.number} – {account.name}"


def account_name_with_role(account: Account) -> str:
    """Liefert den Kontonamen für eine separate Namensspalte."""

    if account.person_account_role is PersonAccountRole.DEBITOR:
        return f"Debitor – {account.name}"
    if account.person_account_role is PersonAccountRole.KREDITOR:
        return f"Kreditor – {account.name}"
    return account.name

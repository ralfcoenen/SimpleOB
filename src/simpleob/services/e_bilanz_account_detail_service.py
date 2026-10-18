"""Erzeugung der Kontennachweise für die E-Bilanz."""

from simpleob.accounting.ledger import Ledger
from simpleob.accounting.mapper import AccountMapper
from simpleob.domain.account import Account
from simpleob.domain.account_type import AccountType
from simpleob.domain.e_bilanz_account_detail import (
    EBilanzAccountDetail,
)
from simpleob.domain.money import ZERO


class EBilanzAccountDetailService:
    """Erzeugt unverdichtete Kontennachweise aus dem Hauptbuch."""

    def __init__(
        self,
        *,
        account_mapper: AccountMapper,
        accounts: tuple[Account, ...],
    ) -> None:
        self._account_mapper = account_mapper
        self._accounts = {
            account.number: account
            for account in accounts
        }
        self._account_types = {
            account.number: account.account_type
            for account in accounts
        }

    def build(
        self,
        *,
        ledger: Ledger,
    ) -> tuple[EBilanzAccountDetail, ...]:
        """Erzeugt die Kontennachweise aller werthaltigen Konten."""

        details: list[EBilanzAccountDetail] = []

        for balance in ledger:
            if balance.balance == ZERO:
                continue

            try:
                account = self._accounts[
                    balance.account_number
                ]
            except KeyError as exc:
                raise ValueError(
                    "Keine Kontenbezeichnung für Konto "
                    f"{balance.account_number} vorhanden."
                ) from exc

            position = self._account_mapper.position_for(
                balance
            )

            details.append(
                EBilanzAccountDetail(
                    position=position,
                    account_number=balance.account_number,
                    account_description=account.name,
                    balance=balance.balance,
                )
            )

        return tuple(details)

    def build_for_e_bilanz(
        self,
        *,
        pre_closing_ledger: Ledger,
        closed_ledger: Ledger,
    ) -> tuple[EBilanzAccountDetail, ...]:
        """Erzeugt Kontennachweise aus Vor- und Nachabschlussdaten."""

        income_account_types = (
            AccountType.REVENUE,
            AccountType.EXPENSE,
        )

        balance_sheet_account_types = (
            AccountType.ASSET,
            AccountType.LIABILITY,
            AccountType.EQUITY,
        )

        details: list[EBilanzAccountDetail] = []

        for ledger, allowed_types in (
            (
                pre_closing_ledger,
                income_account_types,
            ),
            (
                closed_ledger,
                balance_sheet_account_types,
            ),
        ):
            for balance in ledger:
                if balance.balance == ZERO:
                    continue

                account_type = self._account_types.get(
                    balance.account_number
                )

                if account_type not in allowed_types:
                    continue

                try:
                    account = self._accounts[
                        balance.account_number
                    ]
                except KeyError as exc:
                    raise ValueError(
                        "Keine Kontenbezeichnung für Konto "
                        f"{balance.account_number} vorhanden."
                    ) from exc

                position = self._account_mapper.position_for(
                    balance
                )

                details.append(
                    EBilanzAccountDetail(
                        position=position,
                        account_number=balance.account_number,
                        account_description=account.name,
                        balance=balance.balance,
                    )
                )

        return tuple(details)

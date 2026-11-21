from decimal import Decimal

from simpleob.accounting.account_balance import AccountBalance
from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from simpleob.domain.account_type import AccountType
from simpleob.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from simpleob.domain.errors import (
    InvalidPersonAccountClassificationError,
    UnknownAccountError,
)
from simpleob.domain.money import ZERO
from simpleob.domain.person_account_role import PersonAccountRole
from simpleob.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)


class AccountMapper:
    def __init__(
        self,
        chart_of_accounts: ChartOfAccountsTemplate,
        *,
        bank_account_numbers: frozenset[str] = frozenset(),
    ) -> None:
        self._chart_of_accounts = chart_of_accounts
        assets, liabilities = create_hgb_balance_sheet_structure()
        position_provider = HgbFinancialStatementPositionProvider(
            (assets, liabilities)
        )
        self._person_account_positions = {
            "receivable": position_provider.get(
                "HGB.266.AKTIVA.B.II.1"
            ),
            "payable": position_provider.get(
                "HGB.266.PASSIVA.C.4"
            ),
        }
        self._bank_account_positions = {
            "asset": position_provider.get(
                "HGB.266.AKTIVA.B.IV"
            ),
            "liability": position_provider.get(
                "HGB.266.PASSIVA.C.2"
            ),
        }
        self._bank_account_numbers = frozenset()
        self.update_bank_account_numbers(bank_account_numbers)

    @property
    def bank_account_numbers(self) -> frozenset[str]:
        """Liefert die für diese Bilanzberechnung konfigurierten Bankkonten."""

        return self._bank_account_numbers

    def validate_bank_account_numbers(
        self,
        account_numbers: frozenset[str],
    ) -> None:
        """Prüft Bankrollen und individuelle HGB-Regeln auf Konflikte."""

        if not isinstance(account_numbers, frozenset):
            raise TypeError("bank account numbers must be a frozenset")

        expected_positions = {
            "Soll": self._bank_account_positions["asset"].code,
            "Haben": self._bank_account_positions["liability"].code,
        }
        for number in sorted(account_numbers):
            if not isinstance(number, str) or not number.isdigit():
                raise ValueError(
                    "Bankkontonummern müssen aus Ziffern bestehen."
                )

            try:
                account = self._chart_of_accounts.get(number)
            except UnknownAccountError as exc:
                raise ValueError(
                    f"Das als Bank konfigurierte Konto {number} "
                    "fehlt im Kontenrahmen."
                ) from exc

            if account.account_type is not AccountType.ASSET:
                raise ValueError(
                    f"Das als Bank konfigurierte Konto {number} muss "
                    "ein Aktivkonto sein."
                )

            if self._chart_of_accounts.is_person_account(number):
                raise ValueError(
                    f"Konflikt bei Konto {number}: Das Konto ist zugleich "
                    "als Bank- und als Personenkonto klassifiziert."
                )

            for rule in self._chart_of_accounts.account_mapping_rules:
                if rule.account_number != number:
                    continue
                for side, position, expected_code in (
                    (
                        "Soll",
                        rule.debit_position,
                        expected_positions["Soll"],
                    ),
                    (
                        "Haben",
                        rule.credit_position,
                        expected_positions["Haben"],
                    ),
                ):
                    if position is not None and position.code != expected_code:
                        raise ValueError(
                            f"Konflikt bei Bankkonto {number}: Die "
                            f"individuelle HGB-{side}zuordnung "
                            f"{position.code} widerspricht der Bankregel "
                            f"{expected_code}."
                        )

    def update_bank_account_numbers(
        self,
        account_numbers: frozenset[str],
    ) -> None:
        """Übernimmt eine validierte, aktualisierte Bankkontenrolle."""

        self.validate_bank_account_numbers(account_numbers)
        self._bank_account_numbers = account_numbers

    def map_balance(
        self,
        balance: AccountBalance,
    ) -> tuple[FinancialStatementPosition, Decimal]:
        """Liefert Abschlussposition und vorzeichenbehafteten Betrag."""

        is_person_account = self._chart_of_accounts.is_person_account(
            balance.account_number
        )
        role = self._chart_of_accounts.person_account_role(
            balance.account_number
        )
        if is_person_account != (role is not None):
            raise InvalidPersonAccountClassificationError(
                "Die Personenkontenklassifikation ist widersprüchlich für "
                f"Konto {balance.account_number}."
            )

        if role is not None:
            return self._map_person_account_balance(
                balance=balance,
                role=role,
            )

        is_bank_account = (
            balance.account_number in self._bank_account_numbers
        )
        if (
            self._is_reserved_person_account_number(
                balance.account_number
            )
            and not is_bank_account
        ):
            raise InvalidPersonAccountClassificationError(
                f"Konto {balance.account_number} liegt im reservierten "
                "Personenkonten-Nummernkreis, hat aber keine gültige "
                "Personenkontenzuordnung. Die Kontonummer allein bestimmt "
                "keine Debitoren- oder Kreditorenrolle."
            )

        if balance.balance == ZERO:
            raise ValueError(
                f"Konto {balance.account_number} hat einen Nullsaldo und "
                "keine HGB-Bilanzposition."
            )

        if is_bank_account:
            position_key = (
                "asset"
                if balance.debit_balance > ZERO
                else "liability"
            )
            amount = (
                balance.debit_balance
                if position_key == "asset"
                else balance.credit_balance
            )
            return self._bank_account_positions[position_key], amount

        for rule in self._chart_of_accounts.account_mapping_rules:
            if rule.account_number != balance.account_number:
                continue

            account = self._chart_of_accounts.get(
                balance.account_number
            )
            if balance.debit_balance > ZERO:
                if rule.debit_position is not None:
                    return (
                        rule.debit_position,
                        (
                            -balance.debit_balance
                            if account.account_type is AccountType.EQUITY
                            else balance.debit_balance
                        ),
                    )

                if (
                    account.account_type
                    in (
                        AccountType.REVENUE,
                        AccountType.EQUITY,
                    )
                    and rule.credit_position is not None
                ):
                    return (
                        rule.credit_position,
                        -balance.debit_balance,
                    )

                raise ValueError(
                    "no debit position defined for account "
                    f"{balance.account_number}"
                )

            if balance.credit_balance > ZERO:
                if rule.credit_position is not None:
                    return (
                        rule.credit_position,
                        balance.credit_balance,
                    )

                if (
                    account.account_type is AccountType.EXPENSE
                    and rule.debit_position is not None
                ):
                    return (
                        rule.debit_position,
                        -balance.credit_balance,
                    )

                raise ValueError(
                    "no credit position defined for account "
                    f"{balance.account_number}"
                )

        raise ValueError(
            f"Konto {balance.account_number} ist keiner HGB-"
            "Abschlussposition zugeordnet. Prüfen Sie die Konten- und "
            "Personenkontenklassifikation."
        )

    @staticmethod
    def _is_reserved_person_account_number(number: str) -> bool:
        """Erkennt verwaiste Nummern im reservierten PK-Kreis ohne Rolle abzuleiten."""

        if len(number) != 5 or not number.isdigit():
            return False

        account_number = int(number)
        return any(
            lower <= account_number <= upper
            for role in PersonAccountRole
            for lower, upper in (role.number_range,)
        )

    def _map_person_account_balance(
        self,
        *,
        balance: AccountBalance,
        role: PersonAccountRole,
    ) -> tuple[FinancialStatementPosition, Decimal]:
        """Ordnet einen Personenkontosaldo exklusiv nach Rolle und Richtung zu."""

        number = balance.account_number
        self._validate_person_account_classification(
            number=number,
            role=role,
        )

        if balance.balance == ZERO:
            raise ValueError(
                f"Personenkonto {number} hat einen Nullsaldo und "
                "keine HGB-Bilanzposition."
            )

        is_debit_balance = balance.debit_balance > ZERO
        position_key_by_role_and_side = {
            (PersonAccountRole.DEBITOR, True): "receivable",
            (PersonAccountRole.DEBITOR, False): "payable",
            (PersonAccountRole.KREDITOR, True): "receivable",
            (PersonAccountRole.KREDITOR, False): "payable",
        }
        try:
            position_key = position_key_by_role_and_side[
                (role, is_debit_balance)
            ]
        except KeyError as exc:
            raise InvalidPersonAccountClassificationError(
                f"Ungültige Personenkontenrolle für Konto {number}."
            ) from exc
        position = self._person_account_positions[
            position_key
        ]
        amount = (
            balance.debit_balance
            if is_debit_balance
            else balance.credit_balance
        )
        return position, amount

    def _validate_person_account_classification(
        self,
        *,
        number: str,
        role: PersonAccountRole,
    ) -> None:
        """Prüft Kontenstamm und Rolle eines klassifizierten Kontos."""

        try:
            account = self._chart_of_accounts.get(number)
        except UnknownAccountError as exc:
            raise InvalidPersonAccountClassificationError(
                f"Das klassifizierte Personenkonto {number} fehlt im Kontenrahmen."
            ) from exc

        if not isinstance(role, PersonAccountRole):
            raise InvalidPersonAccountClassificationError(
                f"Ungültige Personenkontenrolle für Konto {number}."
            )

        number_range = role.number_range
        if (
            len(number) != 5
            or not number.isdigit()
            or not number_range[0] <= int(number) <= number_range[1]
        ):
            raise InvalidPersonAccountClassificationError(
                f"Kontonummer {number} liegt nicht im Nummernkreis der "
                f"Rolle {role.value}."
            )

        expected_account_type = (
            AccountType.ASSET
            if role is PersonAccountRole.DEBITOR
            else AccountType.LIABILITY
        )
        if account.account_type is not expected_account_type:
            raise InvalidPersonAccountClassificationError(
                f"Personenkonto {number} mit Rolle {role.value} muss den "
                f"Kontotyp {expected_account_type.name} haben."
            )

        if any(
            rule.account_number == number
            for rule in self._chart_of_accounts.account_mapping_rules
        ):
            raise InvalidPersonAccountClassificationError(
                f"Personenkonto {number} darf keine individuelle "
                "HGB-Zuordnung besitzen."
            )

    def position_for(
        self,
        balance: AccountBalance,
    ) -> FinancialStatementPosition:
        position, _ = self.map_balance(
            balance
        )

        return position

    def ensure_person_account_balances_supported(
        self,
        balances: tuple[AccountBalance, ...],
    ) -> None:
        """Validiert, dass erkannte Personenkonten vollständig klassifiziert sind."""
        for balance in balances:
            role = self._chart_of_accounts.person_account_role(
                balance.account_number
            )
            is_person_account = self._chart_of_accounts.is_person_account(
                balance.account_number
            )
            if is_person_account or role is not None:
                if is_person_account != (role is not None):
                    raise InvalidPersonAccountClassificationError(
                        "Die Personenkontenklassifikation ist "
                        "widersprüchlich für Konto "
                        f"{balance.account_number}."
                    )
                assert role is not None
                self._validate_person_account_classification(
                    number=balance.account_number,
                    role=role,
                )
                if balance.balance != ZERO:
                    self.map_balance(balance)

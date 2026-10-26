"""Fachliche Kontenrollen eines Mandanten."""

from dataclasses import dataclass


def _validate_account_numbers(
    *,
    field_name: str,
    account_numbers: frozenset[str],
) -> None:
    if not isinstance(account_numbers, frozenset):
        raise TypeError(
            f"{field_name} must be a frozenset"
        )

    for account_number in account_numbers:
        if not isinstance(account_number, str):
            raise TypeError(
                f"{field_name} must contain str values"
            )

        if not account_number.strip():
            raise ValueError(
                f"{field_name} must not contain blank values"
            )

        if account_number != account_number.strip():
            raise ValueError(
                f"{field_name} must not contain values "
                "with surrounding whitespace"
            )

        if not account_number.isdigit():
            raise ValueError(
                f"{field_name} must contain digits only"
            )


@dataclass(frozen=True, slots=True)
class AccountingAccountRoles:
    """Konfiguriert fachliche Rollen von Mandantenkonten."""

    cash_accounts: frozenset[str]
    bank_accounts: frozenset[str]
    general_rate_sales_accounts: frozenset[str]
    customer_receivables: frozenset[str] = frozenset()
    supplier_payables: frozenset[str] = frozenset()
    customer_credit_balances: frozenset[str] = frozenset()
    supplier_credit_balances: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        _validate_account_numbers(
            field_name="cash_accounts",
            account_numbers=self.cash_accounts,
        )
        _validate_account_numbers(
            field_name="bank_accounts",
            account_numbers=self.bank_accounts,
        )
        _validate_account_numbers(
            field_name="general_rate_sales_accounts",
            account_numbers=self.general_rate_sales_accounts,
        )
        _validate_account_numbers(
            field_name="customer_receivables",
            account_numbers=self.customer_receivables,
        )
        _validate_account_numbers(
            field_name="supplier_payables",
            account_numbers=self.supplier_payables,
        )
        _validate_account_numbers(
            field_name="customer_credit_balances",
            account_numbers=self.customer_credit_balances,
        )
        _validate_account_numbers(
            field_name="supplier_credit_balances",
            account_numbers=self.supplier_credit_balances,
        )
        if len(self.customer_receivables) > 1:
            raise ValueError(
                "Es darf höchstens ein Kundenforderungskonto "
                "konfiguriert sein."
            )
        if len(self.supplier_payables) > 1:
            raise ValueError(
                "Es darf höchstens ein Lieferantenverbindlichkeitskonto "
                "konfiguriert sein."
            )
        if len(self.customer_credit_balances) > 1:
            raise ValueError(
                "Es darf höchstens ein Kundenguthabenkonto konfiguriert sein."
            )
        if len(self.supplier_credit_balances) > 1:
            raise ValueError(
                "Es darf höchstens ein Lieferantenguthabenkonto "
                "konfiguriert sein."
            )

        role_sets = (
            self.cash_accounts,
            self.bank_accounts,
            self.general_rate_sales_accounts,
            self.customer_receivables,
            self.supplier_payables,
            self.customer_credit_balances,
            self.supplier_credit_balances,
        )

        for index, account_numbers in enumerate(role_sets):
            for other_account_numbers in role_sets[index + 1:]:
                overlap = (
                    account_numbers
                    & other_account_numbers
                )

                if overlap:
                    accounts = ", ".join(
                        sorted(overlap)
                    )

                    raise ValueError(
                        "Konten dürfen nicht mehreren "
                        "fachlichen Rollen zugeordnet sein: "
                        f"{accounts}"
                    )

    @property
    def account_numbers(self) -> frozenset[str]:
        """Liefert alle Konten mit fachlicher Rollenbelegung."""

        return frozenset().union(
            self.cash_accounts,
            self.bank_accounts,
            self.general_rate_sales_accounts,
            self.customer_receivables,
            self.supplier_payables,
            self.customer_credit_balances,
            self.supplier_credit_balances,
        )

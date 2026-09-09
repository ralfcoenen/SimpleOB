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

        role_sets = (
            self.cash_accounts,
            self.bank_accounts,
            self.general_rate_sales_accounts,
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
        )

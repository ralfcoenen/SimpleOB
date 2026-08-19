"""Technische Steuerkonten einer Buchhaltung."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AccountingControlAccounts:
    """Konfiguriert die technischen Konten eines Mandanten."""

    opening_balance_account: str
    income_summary_account: str
    profit_account: str
    loss_account: str

    def __post_init__(self) -> None:
        for field_name, account_number in (
            (
                "opening_balance_account",
                self.opening_balance_account,
            ),
            (
                "income_summary_account",
                self.income_summary_account,
            ),
            (
                "profit_account",
                self.profit_account,
            ),
            (
                "loss_account",
                self.loss_account,
            ),
        ):
            if not isinstance(account_number, str):
                raise TypeError(
                    f"{field_name} must be a str"
                )

            if not account_number.strip():
                raise ValueError(
                    f"{field_name} must not be blank"
                )

            if account_number != account_number.strip():
                raise ValueError(
                    f"{field_name} must not contain "
                    "surrounding whitespace"
                )

            if not account_number.isdigit():
                raise ValueError(
                    f"{field_name} must contain digits only"
                )

    @property
    def technical_account_numbers(
        self,
    ) -> frozenset[str]:
        """Liefert alle technisch reservierten Kontonummern."""

        return frozenset(
            (
                self.opening_balance_account,
                self.income_summary_account,
                self.profit_account,
                self.loss_account,
            )
        )

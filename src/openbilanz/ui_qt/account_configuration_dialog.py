"""Dialog für die mandantenbezogene Kontenkonfiguration."""

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QVBoxLayout,
)

from openbilanz.domain.account import Account
from openbilanz.domain.accounting_control_accounts import (
    AccountingControlAccounts,
)
from openbilanz.domain.vat_accounts import VatAccounts


@dataclass(frozen=True, slots=True)
class AccountConfigurationResult:
    """Ergebnis des Dialogs für technische Konten."""

    control_accounts: AccountingControlAccounts
    vat_accounts: VatAccounts


class AccountConfigurationDialog(QDialog):
    """Bearbeitet technische Konten und Umsatzsteuerkonten."""

    def __init__(
        self,
        *,
        accounts: tuple[Account, ...],
        control_accounts: AccountingControlAccounts,
        vat_accounts: VatAccounts,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.result: AccountConfigurationResult | None = None

        self.setWindowTitle("Technische Konten")

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._opening_balance = self._create_account_combo(accounts)
        self._income_summary = self._create_account_combo(accounts)
        self._profit = self._create_account_combo(accounts)
        self._loss = self._create_account_combo(accounts)
        self._retained_earnings = self._create_account_combo(
            accounts
        )
        self._input_tax_7 = self._create_account_combo(accounts)
        self._input_tax_19 = self._create_account_combo(accounts)
        self._output_tax_7 = self._create_account_combo(accounts)
        self._output_tax_19 = self._create_account_combo(accounts)
        self._retained_earnings = self._create_account_combo(
            accounts
        )

        self._select_account(
            self._opening_balance,
            control_accounts.opening_balance_account,
        )
        self._select_account(
            self._income_summary,
            control_accounts.income_summary_account,
        )
        self._select_account(
            self._profit,
            control_accounts.profit_account,
        )
        self._select_account(
            self._loss,
            control_accounts.loss_account,
        )
        self._select_account(
            self._retained_earnings,
            control_accounts.retained_earnings_account,
        )
        self._select_account(
            self._retained_earnings,
            control_accounts.retained_earnings_account,
        )


        self._select_account(
            self._input_tax_7,
            vat_accounts.input_tax_7,
        )
        self._select_account(
            self._input_tax_19,
            vat_accounts.input_tax_19,
        )
        self._select_account(
            self._output_tax_7,
            vat_accounts.output_tax_7,
        )
        self._select_account(
            self._output_tax_19,
            vat_accounts.output_tax_19,
        )

        form.addRow(
            "Eröffnungsbilanzkonto:",
            self._opening_balance,
        )
        form.addRow(
            "GuV-Sammelkonto:",
            self._income_summary,
        )
        form.addRow(
            "Jahresüberschuss:",
            self._profit,
        )
        form.addRow(
            "Jahresfehlbetrag:",
            self._loss,
        )
        form.addRow(
            "Gewinn-/Verlustvortrag:",
            self._retained_earnings,
        )
        form.addRow(
            "Vorsteuer 7 %:",
            self._input_tax_7,
        )
        form.addRow(
            "Vorsteuer 19 %:",
            self._input_tax_19,
        )
        form.addRow(
            "Umsatzsteuer 7 %:",
            self._output_tax_7,
        )
        form.addRow(
            "Umsatzsteuer 19 %:",
            self._output_tax_19,
        )

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

    @staticmethod
    def _create_account_combo(
        accounts: tuple[Account, ...],
    ) -> QComboBox:
        combo = QComboBox()

        for account in sorted(
            accounts,
            key=lambda item: item.number,
        ):
            combo.addItem(
                f"{account.number} - {account.name}",
                account.number,
            )

        return combo

    @staticmethod
    def _select_account(
        combo: QComboBox,
        account_number: str,
    ) -> None:
        index = combo.findData(account_number)

        if index >= 0:
            combo.setCurrentIndex(index)

    @staticmethod
    def _account_number(
        combo: QComboBox,
    ) -> str:
        value = combo.currentData()

        if not isinstance(value, str):
            raise ValueError(
                "Es wurde kein gültiges Konto ausgewählt."
            )

        return value

    def _accept(self) -> None:
        control_accounts = AccountingControlAccounts(
            opening_balance_account=self._account_number(
                self._opening_balance
            ),
            income_summary_account=self._account_number(
                self._income_summary
            ),
            profit_account=self._account_number(
                self._profit
            ),
            loss_account=self._account_number(
                self._loss
            ),
            retained_earnings_account=self._account_number(
                self._retained_earnings
            ),
        )

        vat_accounts = VatAccounts(
            input_tax_7=self._account_number(
                self._input_tax_7
            ),
            input_tax_19=self._account_number(
                self._input_tax_19
            ),
            output_tax_7=self._account_number(
                self._output_tax_7
            ),
            output_tax_19=self._account_number(
                self._output_tax_19
            ),
        )

        self.result = AccountConfigurationResult(
            control_accounts=control_accounts,
            vat_accounts=vat_accounts,
        )

        self.accept()

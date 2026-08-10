"""Konsistenzprüfung für Jahresabschlüsse."""

from openbilanz.accounting.account_balance import AccountBalance
from openbilanz.accounting.balance_sheet import BalanceSheet
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.accounting.mapper import AccountMapper
from openbilanz.accounting.trial_balance import TrialBalance
from openbilanz.domain.closing_consistency_result import (
    ClosingConsistencyResult,
)
from openbilanz.domain.money import ZERO
from openbilanz.services.closing_result import ClosingResult


class ClosingConsistencyService:
    """Prüft die fachliche Konsistenz eines Jahresabschlusses."""

    def validate_trial_balance(
        self,
        trial_balance: TrialBalance,
    ) -> ClosingConsistencyResult:
        """Prüft die Konsistenz einer Summen- und Saldenliste."""

        if not isinstance(
            trial_balance,
            TrialBalance,
        ):
            raise TypeError(
                "trial_balance muss eine TrialBalance sein."
            )

        errors: list[str] = []

        if not trial_balance.is_turnover_balanced:
            errors.append(
                "Soll- und Habenumsätze stimmen nicht überein."
            )

        if not trial_balance.is_balance_balanced:
            errors.append(
                "Soll- und Habensalden stimmen nicht überein."
            )

        return ClosingConsistencyResult(
            errors=tuple(errors)
        )

    def validate_balance_sheet(
        self,
        balance_sheet: BalanceSheet,
    ) -> ClosingConsistencyResult:
        """Prüft die Konsistenz einer Bilanz."""

        if not isinstance(
            balance_sheet,
            BalanceSheet,
        ):
            raise TypeError(
                "balance_sheet muss eine BalanceSheet sein."
            )

        errors: list[str] = []

        if not balance_sheet.is_balanced():
            errors.append(
                "Aktiva und Passiva stimmen nicht überein."
            )

        return ClosingConsistencyResult(
            errors=tuple(errors)
        )
    
    def validate_net_income(
        self,
        *,
        income_statement: IncomeStatement,
        closing_result: ClosingResult,
    ) -> ClosingConsistencyResult:
        """Prüft die Übereinstimmung des Jahresergebnisses."""

        if not isinstance(
            income_statement,
            IncomeStatement,
        ):
            raise TypeError(
                "income_statement muss eine IncomeStatement sein."
            )

        if not isinstance(
            closing_result,
            ClosingResult,
        ):
            raise TypeError(
                "closing_result muss ein ClosingResult sein."
            )

        errors: list[str] = []

        income_statement_result = (
            income_statement.amount_for(
                income_statement.income_statement
            )
        )

        if (
            income_statement_result
            != closing_result.net_income
        ):
            errors.append(
                "GuV-Ergebnis und Jahresabschlussergebnis "
                "stimmen nicht überein."
            )

        return ClosingConsistencyResult(
            errors=tuple(errors)
        )
        
    def validate_account_mappings(
        self,
        *,
        balances: tuple[AccountBalance, ...],
        mapper: AccountMapper,
    ) -> ClosingConsistencyResult:
        """Prüft die vollständige Zuordnung relevanter Kontensalden."""

        errors: list[str] = []

        for balance in balances:
            if (
                balance.debit_balance == ZERO
                and balance.credit_balance == ZERO
            ):
                continue

            try:
                mapper.position_for(
                    balance
                )
            except ValueError:
                errors.append(
                    f"Konto {balance.account_number} "
                    "ist keiner Abschlussposition zugeordnet."
                )

        return ClosingConsistencyResult(
            errors=tuple(errors)
        )
        
    def validate(
        self,
        *,
        trial_balance: TrialBalance,
        balance_sheet: BalanceSheet,
        income_statement: IncomeStatement,
        closing_result: ClosingResult,
        balances: tuple[AccountBalance, ...],
        mapper: AccountMapper,
    ) -> ClosingConsistencyResult:
        """Prüft die vollständige Abschlusskonsistenz."""

        results = (
            self.validate_trial_balance(
                trial_balance
            ),
            self.validate_balance_sheet(
                balance_sheet
            ),
            self.validate_net_income(
                income_statement=income_statement,
                closing_result=closing_result,
            ),
            self.validate_account_mappings(
                balances=balances,
                mapper=mapper,
            ),
        )

        errors = tuple(
            error
            for result in results
            for error in result.errors
        )

        return ClosingConsistencyResult(
            errors=errors
        )
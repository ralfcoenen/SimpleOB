"""Fachlogik für die Ergebnisverwendung."""

from decimal import Decimal

from openbilanz.domain.closing_consistency_result import (
    ClosingConsistencyResult,
)
from openbilanz.domain.money import ZERO
from openbilanz.domain.profit_appropriation_annual_data import (
    ProfitAppropriationAnnualData,
)
from openbilanz.reporting.trial_balance_report import (
    TrialBalanceReport,
)


class ProfitAppropriationService:
    """Berechnet und prüft Angaben zur Ergebnisverwendung."""

    def previous_profit_loss_carryforward(
        self,
        *,
        trial_balance_report: TrialBalanceReport,
        profit_loss_carryforward_account: str,
    ) -> Decimal:
        """Ermittelt den Gewinn-/Verlustvortrag zu Jahresbeginn."""

        if not isinstance(
            trial_balance_report,
            TrialBalanceReport,
        ):
            raise TypeError(
                "trial_balance_report muss ein "
                "TrialBalanceReport sein."
            )

        if not isinstance(
            profit_loss_carryforward_account,
            str,
        ):
            raise TypeError(
                "profit_loss_carryforward_account muss "
                "ein str sein."
            )

        account_number = (
            profit_loss_carryforward_account.strip()
        )

        if not account_number:
            raise ValueError(
                "profit_loss_carryforward_account darf "
                "nicht leer sein."
            )

        for row in trial_balance_report.rows:
            if row.account_number != account_number:
                continue

            return (
                row.opening_credit
                - row.opening_debit
            )

        return ZERO

    def validate(
        self,
        *,
        net_income: Decimal,
        previous_profit_loss_carryforward: Decimal,
        data: ProfitAppropriationAnnualData,
    ) -> ClosingConsistencyResult:
        """Prüft die rechnerische Konsistenz der Ergebnisverwendung."""

        if not isinstance(net_income, Decimal):
            raise TypeError(
                "net_income muss ein Decimal sein."
            )

        if not isinstance(
            previous_profit_loss_carryforward,
            Decimal,
        ):
            raise TypeError(
                "previous_profit_loss_carryforward muss "
                "ein Decimal sein."
            )

        if not isinstance(
            data,
            ProfitAppropriationAnnualData,
        ):
            raise TypeError(
                "data muss ein "
                "ProfitAppropriationAnnualData sein."
            )

        available_amount = (
            net_income
            + previous_profit_loss_carryforward
            + data.statutory_reserve_release
            + data.other_revenue_reserves_release
        )

        appropriated_amount = (
            data.statutory_reserve_addition
            + data.other_revenue_reserves_addition
            + data.distribution
            + data.profit_loss_carryforward
        )

        errors: list[str] = []

        if available_amount != appropriated_amount:
            errors.append(
                "Die Ergebnisverwendung ist rechnerisch "
                "nicht ausgeglichen."
            )

        return ClosingConsistencyResult(
            errors=tuple(errors)
        )

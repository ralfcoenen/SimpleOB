"""Fachlogik für die Ergebnisverwendung."""

from decimal import Decimal

from simpleob.domain.closing_consistency_result import (
    ClosingConsistencyResult,
)
from simpleob.domain.money import ZERO
from simpleob.domain.profit_appropriation_annual_data import (
    ProfitAppropriationAnnualData,
)
from simpleob.reporting.trial_balance_report import (
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

        return ClosingConsistencyResult(
            # Ein verbleibender Betrag ist der ausdrücklich darzustellende
            # Bilanzgewinn/-verlust und muss nicht als neuer Vortrag erfasst
            # werden.
            errors=(),
        )

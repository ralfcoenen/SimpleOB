"""Buchungsvorschläge zur Umsetzung einer Ergebnisverwendung."""

from datetime import date
from decimal import Decimal

from openbilanz.domain.accounting_control_accounts import (
    AccountingControlAccounts,
)
from openbilanz.domain.profit_appropriation_annual_data import (
    ProfitAppropriationAnnualData,
)
from openbilanz.domain.profit_appropriation_posting_proposal import (
    ProfitAppropriationPostingProposal,
)
from openbilanz.domain.profit_appropriation_posting_type import (
    ProfitAppropriationPostingType,
)


class ProfitAppropriationPostingService:
    """Erzeugt Buchungsvorschläge aus einem Ergebnisverwendungsbeschluss."""

    def build_proposals(
        self,
        *,
        data: ProfitAppropriationAnnualData,
        booking_date: date,
        control_accounts: AccountingControlAccounts,
    ) -> tuple[ProfitAppropriationPostingProposal, ...]:
        """Erzeugt die erforderlichen Buchungsvorschläge."""

        if not isinstance(
            data,
            ProfitAppropriationAnnualData,
        ):
            raise TypeError(
                "data must be a ProfitAppropriationAnnualData"
            )

        if not isinstance(booking_date, date):
            raise TypeError("booking_date must be a date")

        if not isinstance(
            control_accounts,
            AccountingControlAccounts,
        ):
            raise TypeError(
                "control_accounts must be an AccountingControlAccounts"
            )

        carryforward_account = (
            control_accounts.profit_loss_carryforward_account
        )

        proposals: list[
            ProfitAppropriationPostingProposal
        ] = []

        self._append_proposal(
            proposals=proposals,
            posting_type=(
                ProfitAppropriationPostingType.STATUTORY_RESERVE_ADDITION
            ),
            booking_date=booking_date,
            amount=data.statutory_reserve_addition,
            debit_account_number=carryforward_account,
            credit_account_number=(
                control_accounts.statutory_reserve_account
            ),
        )

        self._append_proposal(
            proposals=proposals,
            posting_type=(
                ProfitAppropriationPostingType.OTHER_REVENUE_RESERVES_ADDITION
            ),
            booking_date=booking_date,
            amount=data.other_revenue_reserves_addition,
            debit_account_number=carryforward_account,
            credit_account_number=(
                control_accounts.other_revenue_reserves_account
            ),
        )

        self._append_proposal(
            proposals=proposals,
            posting_type=(
                ProfitAppropriationPostingType.STATUTORY_RESERVE_RELEASE
            ),
            booking_date=booking_date,
            amount=data.statutory_reserve_release,
            debit_account_number=(
                control_accounts.statutory_reserve_account
            ),
            credit_account_number=carryforward_account,
        )

        self._append_proposal(
            proposals=proposals,
            posting_type=(
                ProfitAppropriationPostingType.OTHER_REVENUE_RESERVES_RELEASE
            ),
            booking_date=booking_date,
            amount=data.other_revenue_reserves_release,
            debit_account_number=(
                control_accounts.other_revenue_reserves_account
            ),
            credit_account_number=carryforward_account,
        )

        self._append_proposal(
            proposals=proposals,
            posting_type=(
                ProfitAppropriationPostingType.DISTRIBUTION
            ),
            booking_date=booking_date,
            amount=data.distribution,
            debit_account_number=carryforward_account,
            credit_account_number=(
                control_accounts.distribution_liability_account
            ),
        )

        return tuple(proposals)

    @staticmethod
    def _append_proposal(
        *,
        proposals: list[ProfitAppropriationPostingProposal],
        posting_type: ProfitAppropriationPostingType,
        booking_date: date,
        amount: Decimal,
        debit_account_number: str,
        credit_account_number: str,
    ) -> None:
        """Fügt für einen positiven Betrag einen Vorschlag hinzu."""

        if amount <= Decimal("0.00"):
            return

        proposals.append(
            ProfitAppropriationPostingProposal(
                posting_type=posting_type,
                booking_date=booking_date,
                amount=amount,
                debit_account_number=debit_account_number,
                credit_account_number=credit_account_number,
            )
        )

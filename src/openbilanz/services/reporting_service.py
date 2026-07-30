"""Application Service für die Erstellung von Berichten."""

from decimal import Decimal

from openbilanz.accounting.ledger import Ledger
from openbilanz.domain.entry_side import EntrySide
from openbilanz.reporting.account_statement import AccountStatement
from openbilanz.reporting.account_statement_line import AccountStatementLine


class ReportingService:
    """Erzeugt unveränderliche Auswertungen aus dem Hauptbuch."""

    def account_statement(
        self,
        ledger: Ledger,
        account_no: str,
    ) -> AccountStatement:
        """Erzeugt ein Kontoblatt für ein Konto."""

        entries = ledger.entries_for_account(account_no)

        running_balance = Decimal("0")
        lines: list[AccountStatementLine] = []

        for entry in entries:
            if entry.side is EntrySide.DEBIT:
                running_balance += entry.amount
            else:
                running_balance -= entry.amount

            lines.append(
                AccountStatementLine(
                    entry=entry,
                    running_balance=running_balance,
                )
            )

        return AccountStatement(
            account_no=account_no,
            lines=tuple(lines),
        )


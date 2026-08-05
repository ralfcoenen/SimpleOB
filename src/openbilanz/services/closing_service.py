"""Services für den Jahresabschluss."""

"""Services für den Jahresabschluss."""

from decimal import Decimal

from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.accounting.statement_category import StatementCategory
from openbilanz.services.closing_result import ClosingResult



class ClosingService:
    """Führt Abschlussberechnungen durch."""

    @staticmethod
    def calculate_net_income(
        *,
        income: Decimal | None = None,
        expenses: Decimal | None = None,
        income_statement: IncomeStatement | None = None,
    ) -> Decimal:
        """Berechnet Jahresüberschuss oder Jahresfehlbetrag."""
        if income_statement is not None:
            income_total = Decimal("0.00")
            expense_total = Decimal("0.00")

            

            income_total = Decimal("0.00")
            expense_total = Decimal("0.00")

            for position, amount in income_statement.amounts.items():
                if position.category is StatementCategory.INCOME:
                    income_total += amount

                elif position.category is StatementCategory.EXPENSE:
                    expense_total += amount

            return income_total - expense_total

        if income is None or expenses is None:
            raise ValueError(
                "income und expenses müssen gemeinsam angegeben werden."
            )

        return income - expenses

    def close(
        self,
        *,
        income_statement: IncomeStatement,
    ) -> ClosingResult:
        """Führt den GuV-Abschluss durch."""

        net_income = self.calculate_net_income(
            income_statement=income_statement,
        )

        return ClosingResult(
            net_income=net_income,
        )
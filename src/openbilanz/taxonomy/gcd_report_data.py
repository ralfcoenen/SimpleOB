"""Variable GCD-Berichtsdaten."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GcdReportData:
    """Enthält variable Angaben eines GCD-Berichts."""

    income_statement_ends_with_balance_profit: bool

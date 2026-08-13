"""Tests für variable GCD-Berichtsdaten."""

import pytest

from openbilanz.taxonomy.gcd_report_data import (
    GcdReportData,
)


@pytest.mark.parametrize(
    "value",
    (
        True,
        False,
    ),
)
def test_gcd_report_data_contains_balance_profit_setting(
    value: bool,
) -> None:
    """Der Bericht enthält die Angabe zum Bilanzgewinn/-verlust."""

    data = GcdReportData(
        income_statement_ends_with_balance_profit=value,
    )

    assert (
        data.income_statement_ends_with_balance_profit
        is value
    )

from decimal import Decimal

import pytest

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.domain.e_bilanz_account_detail import (
    EBilanzAccountDetail,
)


def _position() -> FinancialStatementPosition:
    return FinancialStatementPosition(
        code="assets.cash",
        name="Kassenbestand",
    )


def test_creates_e_bilanz_account_detail() -> None:
    detail = EBilanzAccountDetail(
        position=_position(),
        account_number="1200",
        account_description="Bank",
        balance=Decimal("1000.00"),
    )

    assert detail.account_number == "1200"
    assert detail.account_description == "Bank"
    assert detail.balance == Decimal("1000.00")


def test_normalizes_account_text() -> None:
    detail = EBilanzAccountDetail(
        position=_position(),
        account_number=" 1200 ",
        account_description=" Bank ",
        balance=Decimal("1000.00"),
    )

    assert detail.account_number == "1200"
    assert detail.account_description == "Bank"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("account_number", ""),
        ("account_number", "   "),
        ("account_description", ""),
        ("account_description", "   "),
    ],
)
def test_rejects_empty_account_text(
    field: str,
    value: str,
) -> None:
    values = {
        "position": _position(),
        "account_number": "1200",
        "account_description": "Bank",
        "balance": Decimal("1000.00"),
    }
    values[field] = value

    with pytest.raises(ValueError):
        EBilanzAccountDetail(**values)

from openbilanz.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from openbilanz.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)


def test_returns_revenue_position() -> None:
    provider = HgbFinancialStatementPositionProvider(
        create_hgb_income_statement_structure(),
    )

    position = provider.get(
        "HGB.275.GKV.1",
    )

    assert position.code == "HGB.275.GKV.1"
    assert position.name == "Umsatzerlöse"

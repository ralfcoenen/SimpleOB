from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)


def test_financial_statement_position_stores_legal_identity() -> None:
    position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B",
        name="Umlaufvermögen",
    )

    assert position.code == "HGB.266.AKTIVA.B"
    assert position.name == "Umlaufvermögen"
    assert position.children == ()


def test_financial_statement_position_is_immutable() -> None:
    position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B",
        name="Umlaufvermögen",
    )

    assert position.children == ()
    
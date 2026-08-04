from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)


def create_hgb_balance_sheet_structure() -> tuple[
    FinancialStatementPosition,
    FinancialStatementPosition,
]:
    cash_and_bank = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.IV",
        name=(
            "Kassenbestand, Bundesbankguthaben, "
            "Guthaben bei Kreditinstituten und Schecks"
        ),
    )

    current_assets = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B",
        name="Umlaufvermögen",
        children=(cash_and_bank,),
    )

    assets = FinancialStatementPosition(
        code="HGB.266.AKTIVA",
        name="Aktiva",
        children=(current_assets,),
    )

    liabilities = FinancialStatementPosition(
        code="HGB.266.PASSIVA",
        name="Passiva",
    )

    return assets, liabilities


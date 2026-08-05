from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.statement_category import StatementCategory


def create_hgb_income_statement_structure() -> FinancialStatementPosition:
    revenue = FinancialStatementPosition(
        code="HGB.275.GKV.1",
        name="Umsatzerlöse",
        category=StatementCategory.INCOME,
    )

    inventory_changes = FinancialStatementPosition(
        code="HGB.275.GKV.2",
        name=(
            "Erhöhung oder Verminderung des Bestands an fertigen "
            "und unfertigen Erzeugnissen"
        ),
        category=StatementCategory.INCOME,
    )

    own_work_capitalized = FinancialStatementPosition(
        code="HGB.275.GKV.3",
        name="Andere aktivierte Eigenleistungen",
        category=StatementCategory.INCOME,
    )

    other_operating_income = FinancialStatementPosition(
        code="HGB.275.GKV.4",
        name="Sonstige betriebliche Erträge",
        category=StatementCategory.INCOME,
    )

    material_costs_for_goods = FinancialStatementPosition(
        code="HGB.275.GKV.5.a",
        name=(
            "Aufwendungen für Roh-, Hilfs- und Betriebsstoffe "
            "und für bezogene Waren"
        ),
        category=StatementCategory.EXPENSE,
    )

    material_costs_for_services = FinancialStatementPosition(
        code="HGB.275.GKV.5.b",
        name="Aufwendungen für bezogene Leistungen",
        category=StatementCategory.EXPENSE,
    )

    material_expense = FinancialStatementPosition(
        code="HGB.275.GKV.5",
        name="Materialaufwand",
        children=(
            material_costs_for_goods,
            material_costs_for_services,
        ),
        category=StatementCategory.EXPENSE,
    )

    personnel_wages = FinancialStatementPosition(
        code="HGB.275.GKV.6.a",
        name="Löhne und Gehälter",
        category=StatementCategory.EXPENSE,
    )

    social_security = FinancialStatementPosition(
        code="HGB.275.GKV.6.b",
        name=(
            "Soziale Abgaben und Aufwendungen "
            "für Altersversorgung und für Unterstützung"
        ),
        category=StatementCategory.EXPENSE,
    )

    personnel_expense = FinancialStatementPosition(
        code="HGB.275.GKV.6",
        name="Personalaufwand",
        children=(
            personnel_wages,
            social_security,
        ),
        category=StatementCategory.EXPENSE,
    )

    depreciation_on_fixed_assets = FinancialStatementPosition(
        code="HGB.275.GKV.7.a",
        name=(
            "auf immaterielle Vermögensgegenstände "
            "des Anlagevermögens und Sachanlagen"
        ),
        category=StatementCategory.EXPENSE,
    )

    depreciation_on_current_assets = FinancialStatementPosition(
        code="HGB.275.GKV.7.b",
        name=(
            "auf Vermögensgegenstände des Umlaufvermögens, "
            "soweit diese die in der Kapitalgesellschaft "
            "üblichen Abschreibungen überschreiten"
        ),
        category=StatementCategory.EXPENSE,
    )

    depreciation = FinancialStatementPosition(
        code="HGB.275.GKV.7",
        name="Abschreibungen",
        children=(
            depreciation_on_fixed_assets,
            depreciation_on_current_assets,
        ),
        category=StatementCategory.EXPENSE,
    )

    other_operating_expenses = FinancialStatementPosition(
        code="HGB.275.GKV.8",
        name="Sonstige betriebliche Aufwendungen",
        category=StatementCategory.EXPENSE,
    )

    income_from_participations = FinancialStatementPosition(
        code="HGB.275.GKV.9",
        name="Erträge aus Beteiligungen",
        category=StatementCategory.INCOME,
    )

    income_from_other_securities_and_loans = FinancialStatementPosition(
        code="HGB.275.GKV.10",
        name=(
            "Erträge aus anderen Wertpapieren und Ausleihungen "
            "des Finanzanlagevermögens"
        ),
        category=StatementCategory.INCOME,
    )

    other_interest_and_similar_income = FinancialStatementPosition(
        code="HGB.275.GKV.11",
        name="Sonstige Zinsen und ähnliche Erträge",
        category=StatementCategory.INCOME,
    )

    depreciation_on_financial_assets = FinancialStatementPosition(
        code="HGB.275.GKV.12",
        name=(
            "Abschreibungen auf Finanzanlagen "
            "und auf Wertpapiere des Umlaufvermögens"
        ),
        category=StatementCategory.EXPENSE,
    )

    interest_and_similar_expenses = FinancialStatementPosition(
        code="HGB.275.GKV.13",
        name="Zinsen und ähnliche Aufwendungen",
        category=StatementCategory.EXPENSE,
    )

    income_taxes = FinancialStatementPosition(
        code="HGB.275.GKV.14",
        name="Steuern vom Einkommen und vom Ertrag",
        category=StatementCategory.EXPENSE,
    )

    profit_after_tax = FinancialStatementPosition(
        code="HGB.275.GKV.15",
        name="Ergebnis nach Steuern",
        category=StatementCategory.RESULT,
    )

    other_taxes = FinancialStatementPosition(
        code="HGB.275.GKV.16",
        name="Sonstige Steuern",
        category=StatementCategory.EXPENSE,
    )

    net_income = FinancialStatementPosition(
        code="HGB.275.GKV.17",
        name="Jahresüberschuss/Jahresfehlbetrag",
        category=StatementCategory.RESULT,
    )

    return FinancialStatementPosition(
        code="HGB.275.GKV",
        name="Gewinn- und Verlustrechnung nach dem Gesamtkostenverfahren",
        children=(
            revenue,
            inventory_changes,
            own_work_capitalized,
            other_operating_income,
            material_expense,
            personnel_expense,
            depreciation,
            other_operating_expenses,
            income_from_participations,
            income_from_other_securities_and_loans,
            other_interest_and_similar_income,
            depreciation_on_financial_assets,
            interest_and_similar_expenses,
            income_taxes,
            profit_after_tax,
            other_taxes,
            net_income,
        ),
        category=StatementCategory.NEUTRAL,
    )
    
    
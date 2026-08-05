from openbilanz.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)

from openbilanz.accounting.statement_category import StatementCategory

def test_income_statement_starts_with_operating_income_positions() -> None:
    income_statement = create_hgb_income_statement_structure()

    assert income_statement.code == "HGB.275.GKV"
    assert income_statement.name == (
        "Gewinn- und Verlustrechnung nach dem Gesamtkostenverfahren"
    )

    assert tuple(
        (position.code, position.name)
        for position in income_statement.children[:4]
    ) == (
        (
            "HGB.275.GKV.1",
            "Umsatzerlöse",
        ),
        (
            "HGB.275.GKV.2",
            "Erhöhung oder Verminderung des Bestands an fertigen "
            "und unfertigen Erzeugnissen",
        ),
        (
            "HGB.275.GKV.3",
            "Andere aktivierte Eigenleistungen",
        ),
        (
            "HGB.275.GKV.4",
            "Sonstige betriebliche Erträge",
        ),
    )
    
def test_material_expense_contains_all_hgb_positions() -> None:
    income_statement = create_hgb_income_statement_structure()

    material_expense = next(
        position
        for position in income_statement.children
        if position.code == "HGB.275.GKV.5"
    )

    assert material_expense.name == "Materialaufwand"

    assert tuple(
        (child.code, child.name)
        for child in material_expense.children
    ) == (
        (
            "HGB.275.GKV.5.a",
            "Aufwendungen für Roh-, Hilfs- und Betriebsstoffe "
            "und für bezogene Waren",
        ),
        (
            "HGB.275.GKV.5.b",
            "Aufwendungen für bezogene Leistungen",
        ),
    )
    

def test_personnel_expense_contains_all_hgb_positions() -> None:
    income_statement = create_hgb_income_statement_structure()

    personnel_expense = next(
        position
        for position in income_statement.children
        if position.code == "HGB.275.GKV.6"
    )

    assert personnel_expense.name == "Personalaufwand"

    assert tuple(
        (child.code, child.name)
        for child in personnel_expense.children
    ) == (
        (
            "HGB.275.GKV.6.a",
            "Löhne und Gehälter",
        ),
        (
            "HGB.275.GKV.6.b",
            "Soziale Abgaben und Aufwendungen "
            "für Altersversorgung und für Unterstützung",
        ),
    )
    
def test_depreciation_contains_all_hgb_positions() -> None:
    income_statement = create_hgb_income_statement_structure()

    depreciation = next(
        position
        for position in income_statement.children
        if position.code == "HGB.275.GKV.7"
    )

    assert depreciation.name == "Abschreibungen"

    assert tuple(
        (child.code, child.name)
        for child in depreciation.children
    ) == (
        (
            "HGB.275.GKV.7.a",
            "auf immaterielle Vermögensgegenstände "
            "des Anlagevermögens und Sachanlagen",
        ),
        (
            "HGB.275.GKV.7.b",
            "auf Vermögensgegenstände des Umlaufvermögens, "
            "soweit diese die in der Kapitalgesellschaft "
            "üblichen Abschreibungen überschreiten",
        ),
    )

def test_income_statement_contains_other_operating_expenses() -> None:
    income_statement = create_hgb_income_statement_structure()

    other_operating_expenses = next(
        position
        for position in income_statement.children
        if position.code == "HGB.275.GKV.8"
    )

    assert other_operating_expenses.name == (
        "Sonstige betriebliche Aufwendungen"
    )
    assert other_operating_expenses.children == ()
    

def test_income_statement_contains_financial_income_positions() -> None:
    income_statement = create_hgb_income_statement_structure()

    assert tuple(
        (position.code, position.name)
        for position in income_statement.children[8:11]
    ) == (
        (
            "HGB.275.GKV.9",
            "Erträge aus Beteiligungen",
        ),
        (
            "HGB.275.GKV.10",
            "Erträge aus anderen Wertpapieren und Ausleihungen "
            "des Finanzanlagevermögens",
        ),
        (
            "HGB.275.GKV.11",
            "Sonstige Zinsen und ähnliche Erträge",
        ),
    )
    
def test_income_statement_contains_financial_expense_positions() -> None:
    income_statement = create_hgb_income_statement_structure()

    assert tuple(
        (position.code, position.name)
        for position in income_statement.children[11:13]
    ) == (
        (
            "HGB.275.GKV.12",
            "Abschreibungen auf Finanzanlagen "
            "und auf Wertpapiere des Umlaufvermögens",
        ),
        (
            "HGB.275.GKV.13",
            "Zinsen und ähnliche Aufwendungen",
        ),
    )
    
def test_income_statement_contains_final_hgb_positions() -> None:
    income_statement = create_hgb_income_statement_structure()

    assert tuple(
        (position.code, position.name)
        for position in income_statement.children[13:]
    ) == (
        (
            "HGB.275.GKV.14",
            "Steuern vom Einkommen und vom Ertrag",
        ),
        (
            "HGB.275.GKV.15",
            "Ergebnis nach Steuern",
        ),
        (
            "HGB.275.GKV.16",
            "Sonstige Steuern",
        ),
        (
            "HGB.275.GKV.17",
            "Jahresüberschuss/Jahresfehlbetrag",
        ),
    )

def test_revenue_is_categorized_as_income() -> None:
    income_statement = create_hgb_income_statement_structure()

    revenue = next(
        position
        for position in income_statement.children
        if position.code == "HGB.275.GKV.1"
    )

    assert revenue.category is StatementCategory.INCOME
    

def test_all_income_positions_are_categorized_as_income() -> None:
    income_statement = create_hgb_income_statement_structure()

    income_codes = {
        "HGB.275.GKV.1",
        "HGB.275.GKV.2",
        "HGB.275.GKV.3",
        "HGB.275.GKV.4",
        "HGB.275.GKV.9",
        "HGB.275.GKV.10",
        "HGB.275.GKV.11",
    }

    for position in income_statement.children:
        if position.code in income_codes:
            assert position.category is StatementCategory.INCOME
            
def test_all_expense_positions_are_categorized_as_expense() -> None:
    income_statement = create_hgb_income_statement_structure()

    expense_codes = {
        "HGB.275.GKV.5",
        "HGB.275.GKV.5.a",
        "HGB.275.GKV.5.b",
        "HGB.275.GKV.6",
        "HGB.275.GKV.6.a",
        "HGB.275.GKV.6.b",
        "HGB.275.GKV.7",
        "HGB.275.GKV.7.a",
        "HGB.275.GKV.7.b",
        "HGB.275.GKV.8",
        "HGB.275.GKV.12",
        "HGB.275.GKV.13",
        "HGB.275.GKV.14",
        "HGB.275.GKV.16",
    }

    def walk(position):
        yield position
        for child in position.children:
            yield from walk(child)

    for position in walk(income_statement):
        if position.code in expense_codes:
            assert position.category is StatementCategory.EXPENSE


def test_all_result_positions_are_categorized_as_result() -> None:
    income_statement = create_hgb_income_statement_structure()

    result_codes = {
        "HGB.275.GKV.15",
        "HGB.275.GKV.17",
    }

    for position in income_statement.children:
        if position.code in result_codes:
            assert position.category is StatementCategory.RESULT
            


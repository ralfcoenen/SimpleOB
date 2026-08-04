from openbilanz.accounting.hgb_balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)


def test_hgb_balance_sheet_contains_cash_and_bank_position() -> None:
    assets, liabilities = create_hgb_balance_sheet_structure()

    assert assets.code == "HGB.266.AKTIVA"
    assert assets.name == "Aktiva"

    current_assets = assets.children[0]

    assert current_assets.code == "HGB.266.AKTIVA.B"
    assert current_assets.name == "Umlaufvermögen"

    cash_and_bank = current_assets.children[0]

    assert cash_and_bank.code == "HGB.266.AKTIVA.B.IV"
    assert cash_and_bank.name == (
        "Kassenbestand, Bundesbankguthaben, "
        "Guthaben bei Kreditinstituten und Schecks"
    )
    assert cash_and_bank.children == ()

    assert liabilities.code == "HGB.266.PASSIVA"
    assert liabilities.name == "Passiva"
    assert liabilities.children == ()
    
    
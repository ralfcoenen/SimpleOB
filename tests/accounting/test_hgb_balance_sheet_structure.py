from simpleob.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)


def test_hgb_balance_sheet_contains_cash_and_bank_position() -> None:
    assets, liabilities = create_hgb_balance_sheet_structure()

    assert assets.code == "HGB.266.AKTIVA"
    assert assets.name == "Aktiva"

    current_assets = next(
        position
        for position in assets.children
        if position.code == "HGB.266.AKTIVA.B"
    )

    assert current_assets.name == "Umlaufvermögen"

    cash_and_bank = next(
        position
        for position in current_assets.children
        if position.code == "HGB.266.AKTIVA.B.IV"
    )

    assert cash_and_bank.code == "HGB.266.AKTIVA.B.IV"
    assert cash_and_bank.name == (
        "Kassenbestand, Bundesbankguthaben, "
        "Guthaben bei Kreditinstituten und Schecks"
    )
    assert cash_and_bank.children == ()

    assert liabilities.code == "HGB.266.PASSIVA"
    assert liabilities.name == "Passiva"


def test_hgb_assets_contain_all_main_sections() -> None:
    assets, _ = create_hgb_balance_sheet_structure()

    assert tuple(
        (position.code, position.name)
        for position in assets.children
    ) == (
        (
            "HGB.266.AKTIVA.A",
            "Anlagevermögen",
        ),
        (
            "HGB.266.AKTIVA.B",
            "Umlaufvermögen",
        ),
        (
            "HGB.266.AKTIVA.C",
            "Rechnungsabgrenzungsposten",
        ),
        (
            "HGB.266.AKTIVA.D",
            "Aktive latente Steuern",
        ),
        (
            "HGB.266.AKTIVA.E",
            "Aktiver Unterschiedsbetrag aus der Vermögensverrechnung",
        ),
    )
    
def test_hgb_liabilities_start_with_equity() -> None:
    _, liabilities = create_hgb_balance_sheet_structure()

    first_position = liabilities.children[0]

    assert first_position.code == "HGB.266.PASSIVA.A"
    assert first_position.name == "Eigenkapital"

def test_equity_contains_all_hgb_positions() -> None:
    _, liabilities = create_hgb_balance_sheet_structure()

    equity = next(
        position
        for position in liabilities.children
        if position.code == "HGB.266.PASSIVA.A"
    )

    assert tuple(
        (position.code, position.name)
        for position in equity.children
    ) == (
        (
            "HGB.266.PASSIVA.A.I",
            "Gezeichnetes Kapital",
        ),
        (
            "HGB.266.PASSIVA.A.II",
            "Kapitalrücklage",
        ),
        (
            "HGB.266.PASSIVA.A.III",
            "Gewinnrücklagen",
        ),
        (
            "HGB.266.PASSIVA.A.IV",
            "Gewinnvortrag/Verlustvortrag",
        ),
        (
            "HGB.266.PASSIVA.A.V",
            "Jahresüberschuss/Jahresfehlbetrag",
        ),
    )

def test_retained_earnings_contains_all_hgb_positions() -> None:
    _, liabilities = create_hgb_balance_sheet_structure()

    equity = next(
        position
        for position in liabilities.children
        if position.code == "HGB.266.PASSIVA.A"
    )

    retained_earnings = next(
        position
        for position in equity.children
        if position.code == "HGB.266.PASSIVA.A.III"
    )

    assert tuple(
        (child.code, child.name)
        for child in retained_earnings.children
    ) == (
        (
            "HGB.266.PASSIVA.A.III.1",
            "Gesetzliche Rücklage",
        ),
        (
            "HGB.266.PASSIVA.A.III.2",
            "Rücklage für Anteile an einem herrschenden "
            "oder mehrheitlich beteiligten Unternehmen",
        ),
        (
            "HGB.266.PASSIVA.A.III.3",
            "Satzungsmäßige Rücklagen",
        ),
        (
            "HGB.266.PASSIVA.A.III.4",
            "Andere Gewinnrücklagen",
        ),
    )
    
def test_hgb_liabilities_contain_all_main_sections() -> None:
    _, liabilities = create_hgb_balance_sheet_structure()

    assert tuple(
        (position.code, position.name)
        for position in liabilities.children
    ) == (
        (
            "HGB.266.PASSIVA.A",
            "Eigenkapital",
        ),
        (
            "HGB.266.PASSIVA.B",
            "Rückstellungen",
        ),
        (
            "HGB.266.PASSIVA.C",
            "Verbindlichkeiten",
        ),
        (
            "HGB.266.PASSIVA.D",
            "Rechnungsabgrenzungsposten",
        ),
        (
            "HGB.266.PASSIVA.E",
            "Passive latente Steuern",
        ),
    )


def test_provisions_contain_all_hgb_positions() -> None:
    _, liabilities = create_hgb_balance_sheet_structure()

    provisions = next(
        position
        for position in liabilities.children
        if position.code == "HGB.266.PASSIVA.B"
    )

    assert tuple(
        (child.code, child.name)
        for child in provisions.children
    ) == (
        (
            "HGB.266.PASSIVA.B.1",
            "Rückstellungen für Pensionen und ähnliche Verpflichtungen",
        ),
        (
            "HGB.266.PASSIVA.B.2",
            "Steuerrückstellungen",
        ),
        (
            "HGB.266.PASSIVA.B.3",
            "Sonstige Rückstellungen",
        ),
    )


def test_liabilities_contain_all_hgb_positions() -> None:
    _, liabilities = create_hgb_balance_sheet_structure()

    liabilities_position = next(
        position
        for position in liabilities.children
        if position.code == "HGB.266.PASSIVA.C"
    )

    assert tuple(
        (child.code, child.name)
        for child in liabilities_position.children
    ) == (
        (
            "HGB.266.PASSIVA.C.1",
            "Anleihen",
        ),
        (
            "HGB.266.PASSIVA.C.2",
            "Verbindlichkeiten gegenüber Kreditinstituten",
        ),
        (
            "HGB.266.PASSIVA.C.3",
            "Erhaltene Anzahlungen auf Bestellungen",
        ),
        (
            "HGB.266.PASSIVA.C.4",
            "Verbindlichkeiten aus Lieferungen und Leistungen",
        ),
        (
            "HGB.266.PASSIVA.C.5",
            "Verbindlichkeiten aus der Annahme gezogener Wechsel und der Ausstellung eigener Wechsel",
        ),
        (
            "HGB.266.PASSIVA.C.6",
            "Verbindlichkeiten gegenüber verbundenen Unternehmen",
        ),
        (
            "HGB.266.PASSIVA.C.7",
            "Verbindlichkeiten gegenüber Unternehmen, mit denen ein Beteiligungsverhältnis besteht",
        ),
        (
            "HGB.266.PASSIVA.C.8",
            "Sonstige Verbindlichkeiten",
        ),
    )
    
def test_fixed_assets_contain_all_hgb_positions() -> None:
    assets, _ = create_hgb_balance_sheet_structure()

    fixed_assets = next(
        position
        for position in assets.children
        if position.code == "HGB.266.AKTIVA.A"
    )

    assert tuple(
        (child.code, child.name)
        for child in fixed_assets.children
    ) == (
        (
            "HGB.266.AKTIVA.A.I",
            "Immaterielle Vermögensgegenstände",
        ),
        (
            "HGB.266.AKTIVA.A.II",
            "Sachanlagen",
        ),
        (
            "HGB.266.AKTIVA.A.III",
            "Finanzanlagen",
        ),
    )
    
def test_intangible_assets_contain_all_hgb_positions() -> None:
    assets, _ = create_hgb_balance_sheet_structure()

    fixed_assets = next(
        position
        for position in assets.children
        if position.code == "HGB.266.AKTIVA.A"
    )

    intangible_assets = next(
        position
        for position in fixed_assets.children
        if position.code == "HGB.266.AKTIVA.A.I"
    )

    assert tuple(
        (child.code, child.name)
        for child in intangible_assets.children
    ) == (
        (
            "HGB.266.AKTIVA.A.I.1",
            "Selbst geschaffene gewerbliche Schutzrechte und ähnliche Rechte und Werte",
        ),
        (
            "HGB.266.AKTIVA.A.I.2",
            "Entgeltlich erworbene Konzessionen, gewerbliche Schutzrechte und ähnliche Rechte und Werte sowie Lizenzen an solchen Rechten und Werten",
        ),
        (
            "HGB.266.AKTIVA.A.I.3",
            "Geschäfts- oder Firmenwert",
        ),
        (
            "HGB.266.AKTIVA.A.I.4",
            "Geleistete Anzahlungen",
        ),
    )

def test_tangible_assets_contain_all_hgb_positions() -> None:
    assets, _ = create_hgb_balance_sheet_structure()

    fixed_assets = next(
        position
        for position in assets.children
        if position.code == "HGB.266.AKTIVA.A"
    )

    tangible_assets = next(
        position
        for position in fixed_assets.children
        if position.code == "HGB.266.AKTIVA.A.II"
    )

    assert tuple(
        (child.code, child.name)
        for child in tangible_assets.children
    ) == (
        (
            "HGB.266.AKTIVA.A.II.1",
            "Grundstücke, grundstücksgleiche Rechte und Bauten "
            "einschließlich der Bauten auf fremden Grundstücken",
        ),
        (
            "HGB.266.AKTIVA.A.II.2",
            "Technische Anlagen und Maschinen",
        ),
        (
            "HGB.266.AKTIVA.A.II.3",
            "Andere Anlagen, Betriebs- und Geschäftsausstattung",
        ),
        (
            "HGB.266.AKTIVA.A.II.4",
            "Geleistete Anzahlungen und Anlagen im Bau",
        ),
    )
    
def test_financial_assets_contain_all_hgb_positions() -> None:
    assets, _ = create_hgb_balance_sheet_structure()

    fixed_assets = next(
        position
        for position in assets.children
        if position.code == "HGB.266.AKTIVA.A"
    )

    financial_assets = next(
        position
        for position in fixed_assets.children
        if position.code == "HGB.266.AKTIVA.A.III"
    )

    assert tuple(
        (child.code, child.name)
        for child in financial_assets.children
    ) == (
        (
            "HGB.266.AKTIVA.A.III.1",
            "Anteile an verbundenen Unternehmen",
        ),
        (
            "HGB.266.AKTIVA.A.III.2",
            "Ausleihungen an verbundene Unternehmen",
        ),
        (
            "HGB.266.AKTIVA.A.III.3",
            "Beteiligungen",
        ),
        (
            "HGB.266.AKTIVA.A.III.4",
            "Ausleihungen an Unternehmen, mit denen ein Beteiligungsverhältnis besteht",
        ),
        (
            "HGB.266.AKTIVA.A.III.5",
            "Wertpapiere des Anlagevermögens",
        ),
        (
            "HGB.266.AKTIVA.A.III.6",
            "Sonstige Ausleihungen",
        ),
    )
    
def test_current_assets_contain_all_hgb_positions() -> None:
    assets, _ = create_hgb_balance_sheet_structure()

    current_assets = next(
        position
        for position in assets.children
        if position.code == "HGB.266.AKTIVA.B"
    )

    assert tuple(
        (child.code, child.name)
        for child in current_assets.children
    ) == (
        (
            "HGB.266.AKTIVA.B.I",
            "Vorräte",
        ),
        (
            "HGB.266.AKTIVA.B.II",
            "Forderungen und sonstige Vermögensgegenstände",
        ),
        (
            "HGB.266.AKTIVA.B.III",
            "Wertpapiere",
        ),
        (
            "HGB.266.AKTIVA.B.IV",
            "Kassenbestand, Bundesbankguthaben, "
            "Guthaben bei Kreditinstituten und Schecks",
        ),
    )
    
    def test_hgb_balance_sheet_contains_cash_and_bank_position() -> None:
        assets, liabilities = create_hgb_balance_sheet_structure()

        assert assets.code == "HGB.266.AKTIVA"
        assert assets.name == "Aktiva"

        current_assets = next(
            position
            for position in assets.children
            if position.code == "HGB.266.AKTIVA.B"
        )

        assert current_assets.name == "Umlaufvermögen"

        cash_and_bank = next(
            position
            for position in current_assets.children
            if position.code == "HGB.266.AKTIVA.B.IV"
        )

        assert cash_and_bank.code == "HGB.266.AKTIVA.B.IV"
        assert cash_and_bank.name == (
            "Kassenbestand, Bundesbankguthaben, "
            "Guthaben bei Kreditinstituten und Schecks"
        )
        assert cash_and_bank.children == ()

        assert liabilities.code == "HGB.266.PASSIVA"
        assert liabilities.name == "Passiva"

    
def test_inventories_contain_all_hgb_positions() -> None:
    assets, _ = create_hgb_balance_sheet_structure()

    current_assets = next(
        position
        for position in assets.children
        if position.code == "HGB.266.AKTIVA.B"
    )

    inventories = next(
        position
        for position in current_assets.children
        if position.code == "HGB.266.AKTIVA.B.I"
    )

    assert tuple(
        (child.code, child.name)
        for child in inventories.children
    ) == (
        (
            "HGB.266.AKTIVA.B.I.1",
            "Roh-, Hilfs- und Betriebsstoffe",
        ),
        (
            "HGB.266.AKTIVA.B.I.2",
            "Unfertige Erzeugnisse, unfertige Leistungen",
        ),
        (
            "HGB.266.AKTIVA.B.I.3",
            "Fertige Erzeugnisse und Waren",
        ),
        (
            "HGB.266.AKTIVA.B.I.4",
            "Geleistete Anzahlungen",
        ),
    )
    
def test_receivables_and_other_assets_contain_all_hgb_positions() -> None:
    assets, _ = create_hgb_balance_sheet_structure()

    current_assets = next(
        position
        for position in assets.children
        if position.code == "HGB.266.AKTIVA.B"
    )

    receivables = next(
        position
        for position in current_assets.children
        if position.code == "HGB.266.AKTIVA.B.II"
    )

    assert tuple(
        (child.code, child.name)
        for child in receivables.children
    ) == (
        (
            "HGB.266.AKTIVA.B.II.1",
            "Forderungen aus Lieferungen und Leistungen",
        ),
        (
            "HGB.266.AKTIVA.B.II.2",
            "Forderungen gegen verbundene Unternehmen",
        ),
        (
            "HGB.266.AKTIVA.B.II.3",
            "Forderungen gegen Unternehmen, mit denen ein Beteiligungsverhältnis besteht",
        ),
        (
            "HGB.266.AKTIVA.B.II.4",
            "Sonstige Vermögensgegenstände",
        ),
    )

def test_current_securities_contain_all_hgb_positions() -> None:
    assets, _ = create_hgb_balance_sheet_structure()

    current_assets = next(
        position
        for position in assets.children
        if position.code == "HGB.266.AKTIVA.B"
    )

    current_securities = next(
        position
        for position in current_assets.children
        if position.code == "HGB.266.AKTIVA.B.III"
    )

    assert tuple(
        (child.code, child.name)
        for child in current_securities.children
    ) == (
        (
            "HGB.266.AKTIVA.B.III.1",
            "Anteile an verbundenen Unternehmen",
        ),
        (
            "HGB.266.AKTIVA.B.III.2",
            "Sonstige Wertpapiere",
        ),
    )
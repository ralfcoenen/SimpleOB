from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)


def _create_fixed_assets() -> FinancialStatementPosition:
    self_created_intangibles = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A.I.1",
        name=(
            "Selbst geschaffene gewerbliche Schutzrechte "
            "und ähnliche Rechte und Werte"
        ),
    )

    acquired_intangibles = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A.I.2",
        name=(
            "Entgeltlich erworbene Konzessionen, "
            "gewerbliche Schutzrechte und ähnliche Rechte "
            "und Werte sowie Lizenzen an solchen Rechten "
            "und Werten"
        ),
    )

    goodwill = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A.I.3",
        name="Geschäfts- oder Firmenwert",
    )

    intangible_advance_payments = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A.I.4",
        name="Geleistete Anzahlungen",
    )

    intangible_assets = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A.I",
        name="Immaterielle Vermögensgegenstände",
        children=(
            self_created_intangibles,
            acquired_intangibles,
            goodwill,
            intangible_advance_payments,
        ),
    )

    land_and_buildings = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A.II.1",
        name=(
            "Grundstücke, grundstücksgleiche Rechte und Bauten "
            "einschließlich der Bauten auf fremden Grundstücken"
        ),
    )

    technical_equipment = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A.II.2",
        name="Technische Anlagen und Maschinen",
    )

    other_equipment = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A.II.3",
        name="Andere Anlagen, Betriebs- und Geschäftsausstattung",
    )

    assets_under_construction = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A.II.4",
        name="Geleistete Anzahlungen und Anlagen im Bau",
    )

    tangible_assets = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A.II",
        name="Sachanlagen",
        children=(
            land_and_buildings,
            technical_equipment,
            other_equipment,
            assets_under_construction,
        ),
    )

    shares_in_affiliated_companies = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A.III.1",
        name="Anteile an verbundenen Unternehmen",
    )

    loans_to_affiliated_companies = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A.III.2",
        name="Ausleihungen an verbundene Unternehmen",
    )

    participating_interests = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A.III.3",
        name="Beteiligungen",
    )

    loans_to_participating_interests = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A.III.4",
        name=(
            "Ausleihungen an Unternehmen, "
            "mit denen ein Beteiligungsverhältnis besteht"
        ),
    )

    investment_securities = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A.III.5",
        name="Wertpapiere des Anlagevermögens",
    )

    other_loans = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A.III.6",
        name="Sonstige Ausleihungen",
    )

    financial_assets = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A.III",
        name="Finanzanlagen",
        children=(
            shares_in_affiliated_companies,
            loans_to_affiliated_companies,
            participating_interests,
            loans_to_participating_interests,
            investment_securities,
            other_loans,
        ),
    )

    return FinancialStatementPosition(
        code="HGB.266.AKTIVA.A",
        name="Anlagevermögen",
        children=(
            intangible_assets,
            tangible_assets,
            financial_assets,
        ),
    )

def _create_current_assets() -> FinancialStatementPosition:
    raw_materials = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.I.1",
        name="Roh-, Hilfs- und Betriebsstoffe",
    )

    work_in_progress = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.I.2",
        name="Unfertige Erzeugnisse, unfertige Leistungen",
    )

    finished_goods = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.I.3",
        name="Fertige Erzeugnisse und Waren",
    )

    inventory_advance_payments = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.I.4",
        name="Geleistete Anzahlungen",
    )

    inventories = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.I",
        name="Vorräte",
        children=(
            raw_materials,
            work_in_progress,
            finished_goods,
            inventory_advance_payments,
        ),
    )

    trade_receivables = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.II.1",
        name="Forderungen aus Lieferungen und Leistungen",
    )

    receivables_from_affiliated_companies = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.II.2",
        name="Forderungen gegen verbundene Unternehmen",
    )

    receivables_from_participating_interests = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.II.3",
        name=(
            "Forderungen gegen Unternehmen, mit denen "
            "ein Beteiligungsverhältnis besteht"
        ),
    )

    other_current_assets = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.II.4",
        name="Sonstige Vermögensgegenstände",
    )

    receivables_and_other_assets = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.II",
        name="Forderungen und sonstige Vermögensgegenstände",
        children=(
            trade_receivables,
            receivables_from_affiliated_companies,
            receivables_from_participating_interests,
            other_current_assets,
        ),
    )

    shares_in_affiliated_companies = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.III.1",
        name="Anteile an verbundenen Unternehmen",
    )

    other_current_securities = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.III.2",
        name="Sonstige Wertpapiere",
    )

    current_securities = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.III",
        name="Wertpapiere",
        children=(
            shares_in_affiliated_companies,
            other_current_securities,
        ),
    )

    cash_and_bank = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.IV",
        name=(
            "Kassenbestand, Bundesbankguthaben, "
            "Guthaben bei Kreditinstituten und Schecks"
        ),
    )

    return FinancialStatementPosition(
        code="HGB.266.AKTIVA.B",
        name="Umlaufvermögen",
        children=(
            inventories,
            receivables_and_other_assets,
            current_securities,
            cash_and_bank,
        ),
    )

def _create_equity() -> FinancialStatementPosition:
    subscribed_capital = FinancialStatementPosition(
        code="HGB.266.PASSIVA.A.I",
        name="Gezeichnetes Kapital",
    )

    capital_reserve = FinancialStatementPosition(
        code="HGB.266.PASSIVA.A.II",
        name="Kapitalrücklage",
    )

    statutory_reserve = FinancialStatementPosition(
        code="HGB.266.PASSIVA.A.III.1",
        name="Gesetzliche Rücklage",
    )

    shares_in_controlling_company_reserve = FinancialStatementPosition(
        code="HGB.266.PASSIVA.A.III.2",
        name=(
            "Rücklage für Anteile an einem herrschenden "
            "oder mehrheitlich beteiligten Unternehmen"
        ),
    )

    articles_of_association_reserves = FinancialStatementPosition(
        code="HGB.266.PASSIVA.A.III.3",
        name="Satzungsmäßige Rücklagen",
    )

    other_retained_earnings = FinancialStatementPosition(
        code="HGB.266.PASSIVA.A.III.4",
        name="Andere Gewinnrücklagen",
    )

    retained_earnings = FinancialStatementPosition(
        code="HGB.266.PASSIVA.A.III",
        name="Gewinnrücklagen",
        children=(
            statutory_reserve,
            shares_in_controlling_company_reserve,
            articles_of_association_reserves,
            other_retained_earnings,
        ),
    )

    profit_or_loss_carried_forward = FinancialStatementPosition(
        code="HGB.266.PASSIVA.A.IV",
        name="Gewinnvortrag/Verlustvortrag",
    )

    net_income_or_loss = FinancialStatementPosition(
        code="HGB.266.PASSIVA.A.V",
        name="Jahresüberschuss/Jahresfehlbetrag",
    )

    return FinancialStatementPosition(
        code="HGB.266.PASSIVA.A",
        name="Eigenkapital",
        children=(
            subscribed_capital,
            capital_reserve,
            retained_earnings,
            profit_or_loss_carried_forward,
            net_income_or_loss,
        ),
    )

def _create_provisions() -> FinancialStatementPosition:
    pension_provisions = FinancialStatementPosition(
        code="HGB.266.PASSIVA.B.1",
        name="Rückstellungen für Pensionen und ähnliche Verpflichtungen",
    )

    tax_provisions = FinancialStatementPosition(
        code="HGB.266.PASSIVA.B.2",
        name="Steuerrückstellungen",
    )

    other_provisions = FinancialStatementPosition(
        code="HGB.266.PASSIVA.B.3",
        name="Sonstige Rückstellungen",
    )

    return FinancialStatementPosition(
        code="HGB.266.PASSIVA.B",
        name="Rückstellungen",
        children=(
            pension_provisions,
            tax_provisions,
            other_provisions,
        ),
    )

def _create_payables() -> FinancialStatementPosition:
    bonds = FinancialStatementPosition(
        code="HGB.266.PASSIVA.C.1",
        name="Anleihen",
    )

    liabilities_to_credit_institutions = FinancialStatementPosition(
        code="HGB.266.PASSIVA.C.2",
        name="Verbindlichkeiten gegenüber Kreditinstituten",
    )

    advance_payments_received = FinancialStatementPosition(
        code="HGB.266.PASSIVA.C.3",
        name="Erhaltene Anzahlungen auf Bestellungen",
    )

    trade_payables = FinancialStatementPosition(
        code="HGB.266.PASSIVA.C.4",
        name="Verbindlichkeiten aus Lieferungen und Leistungen",
    )

    bill_of_exchange_liabilities = FinancialStatementPosition(
        code="HGB.266.PASSIVA.C.5",
        name=(
            "Verbindlichkeiten aus der Annahme gezogener Wechsel "
            "und der Ausstellung eigener Wechsel"
        ),
    )

    liabilities_to_affiliated_companies = FinancialStatementPosition(
        code="HGB.266.PASSIVA.C.6",
        name="Verbindlichkeiten gegenüber verbundenen Unternehmen",
    )

    liabilities_to_participating_interests = FinancialStatementPosition(
        code="HGB.266.PASSIVA.C.7",
        name=(
            "Verbindlichkeiten gegenüber Unternehmen, mit denen "
            "ein Beteiligungsverhältnis besteht"
        ),
    )

    other_liabilities = FinancialStatementPosition(
        code="HGB.266.PASSIVA.C.8",
        name="Sonstige Verbindlichkeiten",
    )

    return FinancialStatementPosition(
        code="HGB.266.PASSIVA.C",
        name="Verbindlichkeiten",
        children=(
            bonds,
            liabilities_to_credit_institutions,
            advance_payments_received,
            trade_payables,
            bill_of_exchange_liabilities,
            liabilities_to_affiliated_companies,
            liabilities_to_participating_interests,
            other_liabilities,
        ),
    )

def _create_liabilities() -> FinancialStatementPosition:
    equity = _create_equity()
    provisions = _create_provisions()
    payables = _create_payables()

    deferred_income = FinancialStatementPosition(
        code="HGB.266.PASSIVA.D",
        name="Rechnungsabgrenzungsposten",
    )

    deferred_tax_liabilities = FinancialStatementPosition(
        code="HGB.266.PASSIVA.E",
        name="Passive latente Steuern",
    )

    return FinancialStatementPosition(
        code="HGB.266.PASSIVA",
        name="Passiva",
        children=(
            equity,
            provisions,
            payables,
            deferred_income,
            deferred_tax_liabilities,
        ),
    )

def _create_assets() -> FinancialStatementPosition:
    fixed_assets = _create_fixed_assets()
    current_assets = _create_current_assets()

    prepaid_expenses = FinancialStatementPosition(
        code="HGB.266.AKTIVA.C",
        name="Rechnungsabgrenzungsposten",
    )

    deferred_tax_assets = FinancialStatementPosition(
        code="HGB.266.AKTIVA.D",
        name="Aktive latente Steuern",
    )

    asset_difference_from_offsetting = FinancialStatementPosition(
        code="HGB.266.AKTIVA.E",
        name="Aktiver Unterschiedsbetrag aus der Vermögensverrechnung",
    )

    return FinancialStatementPosition(
        code="HGB.266.AKTIVA",
        name="Aktiva",
        children=(
            fixed_assets,
            current_assets,
            prepaid_expenses,
            deferred_tax_assets,
            asset_difference_from_offsetting,
        ),
    )

def create_hgb_balance_sheet_structure() -> tuple[
    FinancialStatementPosition,
    FinancialStatementPosition,
]:
    
    assets = _create_assets()
    liabilities = _create_liabilities()
 
    return assets, liabilities

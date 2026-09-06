#!/usr/bin/env python3
"""Manueller Praxistest des neuen SimpleOB-ERiC-Pfads für Taxonomie 6.9.

Der Test erzeugt die E-Bilanz vollständig aus den in SimpleOB
gespeicherten Fachdaten.

Ablauf:

1. SimpleOB-Datenbank öffnen.
2. Mandant auswählen.
3. Abgeschlossenes Geschäftsjahr auswählen.
4. Mandantenspezifischen Kontenrahmen laden.
5. Buchungen des Geschäftsjahres laden.
6. Pre-Closing-Ledger erzeugen.
7. GuV mit derselben Fachlogik wie die SimpleOB-Oberfläche erzeugen.
8. Bilanz mit derselben Fachlogik wie die SimpleOB-Oberfläche erzeugen.
9. ERiC-relevante GAAP-CI-Bilanzwerte diagnostisch ausgeben.
10. ERiC-relevante GAAP-CI-GuV-Summenwerte berechnen.
11. Taxonomie-6.9-FactPlan mit den bisherigen produktiven Werten auflösen.
12. Neue XBRL-6.9-Instanz erzeugen.
13. ELSTER-DatenTeil erzeugen.
14. TransferHeader mit EricCreateTH erzeugen.
15. Vollständiges ElsterXML lokal mit ERIC_VALIDIERE validieren.

Die diagnostisch ermittelten Bilanzwerte werden in diesem Schritt
bewusst noch nicht an den FactPlanResolver übergeben.

Der Test:

- liest keine alte XBRL-Datei,
- sendet keine Daten an ELSTER,
- verwendet kein Zertifikat,
- erzeugt keinen PDF-Druck,
- verwendet ausschließlich ERIC_VALIDIERE.
"""

from __future__ import annotations

from pathlib import Path

from openbilanz.accounting.balance_sheet import BalanceSheet
from openbilanz.accounting.financial_statement_context import (
    create_financial_statement_context,
    create_standard_financial_statement_context,
)
from openbilanz.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.accounting.ledger import Ledger
from openbilanz.core.config import load_config
from openbilanz.core.version import get_application_version
from openbilanz.database.booking_repository import BookingRepository
from openbilanz.database.chart_of_accounts_repository import (
    ChartOfAccountsRepository,
)
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.database.database import Database
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.booking_type import BookingType
from openbilanz.domain.company import Company
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.fiscal_year_status import FiscalYearStatus
from openbilanz.domain.managed_fiscal_year import ManagedFiscalYear
from openbilanz.domain.money import ZERO
from openbilanz.eric.bilanz_generation.fact_plan_resolver import (
    FactPlanResolver,
)
from openbilanz.eric.bilanz_generation.gaap_ci_6_9_account_detail_values import (
    GaapCi69AccountDetailValueBuilder,
)
from openbilanz.eric.bilanz_generation.gaap_ci_6_9_balance_sheet_values import (
    GaapCi69BalanceSheetValueBuilder,
)
from openbilanz.eric.bilanz_generation.gaap_ci_6_9_values import (
    GaapCi69ValueCalculator,
)
from openbilanz.eric.bilanz_generation.taxonomy_6_9 import (
    create_profile_6_9,
)
from openbilanz.eric.bilanz_generation.taxonomy_6_9_values import (
    Taxonomy69ValueBuilder,
)
from openbilanz.eric.bilanz_generation.taxonomy_6_9_xbrl_document_builder import (
    Taxonomy69XbrlDocumentBuilder,
)
from openbilanz.eric.elster_bilanz_payload_service import (
    ElsterBilanzPayloadService,
)
from openbilanz.eric.eric_create_th_adapter import (
    EricCreateThAdapter,
)
from openbilanz.eric.eric_validate_adapter import (
    EricValidateAdapter,
    EricValidateError,
)
from openbilanz.services.closing_result import ClosingResult
from openbilanz.services.closing_service import ClosingService
from openbilanz.services.e_bilanz_account_detail_service import (
    EBilanzAccountDetailService,
)
from openbilanz.services.posting_service import PostingService
from openbilanz.taxonomy.arelle_adapter import ArelleAdapter
from openbilanz.taxonomy.concept import TaxonomyPeriodType
from openbilanz.taxonomy.concept_set import TaxonomyConceptSet
from openbilanz.taxonomy.context import TaxonomyContext
from openbilanz.taxonomy.entry_point import TaxonomyEntryPoint
from openbilanz.taxonomy.gcd_company_data_mapper import (
    GcdCompanyDataMapper,
)
from openbilanz.taxonomy.gcd_report_profile import GcdReportProfile
from openbilanz.taxonomy.resolver import TaxonomyResolver
from openbilanz.taxonomy.taxonomy import TaxonomyVersion
from openbilanz.taxonomy.unit import TaxonomyUnit

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TAXONOMY_ROOT = (
    PROJECT_ROOT
    / "data"
    / "taxonomy"
)

OUTPUT_XBRL_FILE = (
    PROJECT_ROOT
    / "eric_69_generated.xbrl"
)

ENTITY_SCHEME = (
    "http://www.rzf-nrw.de/Steuernummer"
)


def validate_configuration(config) -> None:
    """Prüft die für den lokalen ERiC-Lauf benötigte Konfiguration."""

    if config.eric_lib_dir is None:
        raise RuntimeError(
            "In data/config.toml ist kein "
            "ERiC-lib-Verzeichnis konfiguriert."
        )

    eric_lib_dir = Path(
        config.eric_lib_dir
    ).expanduser()

    if not eric_lib_dir.is_dir():
        raise RuntimeError(
            "Das konfigurierte ERiC-lib-Verzeichnis "
            f"existiert nicht: {eric_lib_dir}"
        )

    manufacturer_id = (
        config.eric_manufacturer_id
    )

    if (
        manufacturer_id is None
        or not manufacturer_id.strip()
    ):
        raise RuntimeError(
            "In data/config.toml ist keine "
            "ERiC-Hersteller-ID konfiguriert."
        )

    taxonomy_69_root = (
        TAXONOMY_ROOT
        / "6.9"
    )

    if not taxonomy_69_root.is_dir():
        raise RuntimeError(
            "Die Taxonomie 6.9 ist lokal nicht installiert: "
            f"{taxonomy_69_root}"
        )


def select_company(
    companies: tuple[Company, ...],
) -> Company:
    """Wählt den Testmandanten aus."""

    if not companies:
        raise RuntimeError(
            "In der SimpleOB-Datenbank ist kein "
            "Unternehmen vorhanden."
        )

    if len(companies) == 1:
        company = companies[0]

        print(
            "Mandant automatisch ausgewählt: "
            f"{company.name}"
        )

        return company

    print()
    print("Vorhandene Mandanten:")

    for index, company in enumerate(
        companies,
        start=1,
    ):
        print(
            f"  {index}: {company.name}"
        )

    while True:
        value = input(
            "Mandant auswählen: "
        ).strip()

        try:
            index = int(value)
        except ValueError:
            print(
                "Bitte eine Nummer eingeben."
            )
            continue

        if 1 <= index <= len(companies):
            return companies[
                index - 1
            ]

        print(
            "Die Auswahl ist ungültig."
        )


def select_fiscal_year(
    fiscal_years: tuple[
        ManagedFiscalYear,
        ...,
    ],
) -> FiscalYear:
    """Wählt ein abgeschlossenes Geschäftsjahr aus."""

    closed_fiscal_years = tuple(
        managed
        for managed in fiscal_years
        if managed.status
        is FiscalYearStatus.CLOSED
    )

    if not closed_fiscal_years:
        raise RuntimeError(
            "Für den ausgewählten Mandanten ist "
            "kein abgeschlossenes Geschäftsjahr vorhanden."
        )

    if len(closed_fiscal_years) == 1:
        fiscal_year = (
            closed_fiscal_years[
                0
            ].fiscal_year
        )

        print(
            "Geschäftsjahr automatisch ausgewählt: "
            f"{fiscal_year.display_name}"
        )

        return fiscal_year

    print()
    print(
        "Abgeschlossene Geschäftsjahre:"
    )

    for index, managed in enumerate(
        closed_fiscal_years,
        start=1,
    ):
        print(
            f"  {index}: "
            f"{managed.fiscal_year.display_name}"
        )

    while True:
        value = input(
            "Geschäftsjahr auswählen: "
        ).strip()

        try:
            index = int(value)
        except ValueError:
            print(
                "Bitte eine Nummer eingeben."
            )
            continue

        if (
            1
            <= index
            <= len(closed_fiscal_years)
        ):
            return closed_fiscal_years[
                index - 1
            ].fiscal_year

        print(
            "Die Auswahl ist ungültig."
        )


def create_mandant_financial_statement_context(
    *,
    company: Company,
    chart_of_accounts_repository: (
        ChartOfAccountsRepository
    ),
):
    """Erzeugt den produktiven Abschlusskontext des Mandanten."""

    standard_context = (
        create_standard_financial_statement_context()
    )

    position_provider = (
        HgbFinancialStatementPositionProvider(
            (
                standard_context.assets,
                standard_context.liabilities,
                standard_context.income_statement,
            )
        )
    )

    loaded_chart_of_accounts = (
        chart_of_accounts_repository
        .load_for_company(
            company_id=company.company_id,
            position_provider=position_provider,
        )
    )

    if loaded_chart_of_accounts is None:
        raise RuntimeError(
            "Der Kontenrahmen des Unternehmens "
            "konnte nicht geladen werden."
        )

    (
        chart_of_accounts,
        accounts,
    ) = loaded_chart_of_accounts

    return create_financial_statement_context(
        assets=standard_context.assets,
        liabilities=standard_context.liabilities,
        income_statement=(
            standard_context.income_statement
        ),
        chart_of_accounts=chart_of_accounts,
        accounts=accounts,
    )


def create_pre_closing_ledger(
    *,
    company: Company,
    fiscal_year: FiscalYear,
    booking_repository: BookingRepository,
) -> Ledger:
    """Erzeugt das Hauptbuch ohne Abschlussbuchungen."""

    bookings = (
        booking_repository.list_for_fiscal_year(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
        )
    )

    if not bookings:
        raise RuntimeError(
            "Für das ausgewählte Geschäftsjahr "
            "sind keine Buchungen vorhanden."
        )

    ledger = Ledger()
    posting_service = PostingService()

    booking_count = 0

    for booking in bookings:
        if (
            booking.booking_type
            is BookingType.CLOSING
        ):
            continue

        posting_service.post_booking(
            booking=booking,
            ledger=ledger,
        )

        booking_count += 1

    print(
        "Pre-Closing-Ledger erzeugt."
    )
    print(
        "Berücksichtigte Buchungen: "
        f"{booking_count}"
    )

    return ledger


def create_income_statement(
    *,
    ledger: Ledger,
    financial_statement_context,
) -> IncomeStatement:
    """Erzeugt die GuV mit derselben Fachlogik wie die Oberfläche."""

    income_statement_account_types = (
        AccountType.REVENUE,
        AccountType.EXPENSE,
    )

    balances = tuple(
        balance
        for balance in ledger.balances()
        if (
            financial_statement_context
            .account_types
            .get(
                balance.account_number
            )
            in income_statement_account_types
        )
        and (
            balance.debit_balance > ZERO
            or balance.credit_balance > ZERO
        )
    )

    amounts = (
        financial_statement_context
        .statement_builder
        .build(
            balances=balances,
            root_positions=(
                financial_statement_context
                .income_statement,
            ),
        )
    )

    return IncomeStatement(
        income_statement=(
            financial_statement_context
            .income_statement
        ),
        amounts=amounts,
    )

def create_balance_sheet(
    *,
    ledger: Ledger,
    financial_statement_context,
    net_income,
) -> BalanceSheet:
    """Erzeugt die Bilanz mit derselben Fachlogik wie die Oberfläche."""

    balance_sheet_account_types = (
        AccountType.ASSET,
        AccountType.LIABILITY,
        AccountType.EQUITY,
    )

    balances = tuple(
        balance
        for balance in ledger.balances()
        if (
            financial_statement_context
            .account_types
            .get(
                balance.account_number
            )
            in balance_sheet_account_types
        )
        and (
            balance.debit_balance > ZERO
            or balance.credit_balance > ZERO
        )
    )

    try:
        equity = next(
            position
            for position
            in financial_statement_context.liabilities.children
            if position.code == "HGB.266.PASSIVA.A"
        )
    except StopIteration as exc:
        raise RuntimeError(
            "Die HGB-Eigenkapitalposition "
            "HGB.266.PASSIVA.A wurde nicht gefunden."
        ) from exc

    try:
        result_position = next(
            position
            for position in equity.children
            if position.code == "HGB.266.PASSIVA.A.V"
        )
    except StopIteration as exc:
        raise RuntimeError(
            "Die HGB-Ergebnisposition "
            "HGB.266.PASSIVA.A.V wurde nicht gefunden."
        ) from exc

    amounts = (
        financial_statement_context
        .statement_builder
        .build(
            balances=balances,
            root_positions=(
                financial_statement_context.assets,
                financial_statement_context.liabilities,
            ),
            closing_result=ClosingResult(
                net_income=net_income,
            ),
            result_position=result_position,
        )
    )

    return BalanceSheet(
        assets=financial_statement_context.assets,
        liabilities=(
            financial_statement_context.liabilities
        ),
        amounts=amounts,
    )

def print_balance_sheet_diagnostics(
    *,
    balance_sheet: BalanceSheet,
    financial_statement_context,
) -> None:
    """Gibt die tatsächlich werthaltigen GAAP-CI-Bilanzwerte aus."""

    values = (
        GaapCi69BalanceSheetValueBuilder.build(
            balance_sheet=balance_sheet,
            income_statement=(
                financial_statement_context
                .income_statement
            ),
        )
    )

    print()
    print("SimpleOB-Bilanz:")
    print(
        "  Aktiva: "
        f"{balance_sheet.amount_for(balance_sheet.assets)}"
    )
    print(
        "  Passiva: "
        f"{balance_sheet.amount_for(balance_sheet.liabilities)}"
    )
    print(
        "  Ausgeglichen: "
        f"{balance_sheet.is_balanced()}"
    )

    print()
    print(
        "Tatsächlich werthaltige "
        "GAAP-CI-Bilanzwerte:"
    )

    for path, value in sorted(
        values.items(),
        key=lambda item: item[0],
    ):
        print(
            f"  {'.'.join(path)} = {value}"
        )

    print(
        "Anzahl werthaltiger "
        "GAAP-CI-Bilanzwerte: "
        f"{len(values)}"
    )


def load_taxonomy_models():
    """Lädt die echten lokalen Taxonomie-6.9-Modelle."""

    resolver = TaxonomyResolver(
        root=TAXONOMY_ROOT
    )

    gcd_entry_point_path = (
        resolver.gcd_entry_point(
            TaxonomyVersion.V6_9
        )
    )

    gaap_ci_entry_point_path = (
        resolver.gaap_ci_fiscal_entry_point(
            TaxonomyVersion.V6_9
        )
    )

    gcd_entry_point = (
        TaxonomyEntryPoint.from_file(
            gcd_entry_point_path
        )
    )

    gaap_ci_entry_point = (
        TaxonomyEntryPoint.from_file(
            gaap_ci_entry_point_path
        )
    )

    adapter = ArelleAdapter()

    try:
        gcd_model = adapter.model(
            gcd_entry_point_path
        )

        gaap_ci_model = adapter.model(
            gaap_ci_entry_point_path
        )

        concepts = TaxonomyConceptSet(
            concepts=(
                gcd_model.concepts.concepts
                + gaap_ci_model.concepts.concepts
            )
        )

        return (
            adapter,
            concepts,
            gcd_entry_point,
            gaap_ci_entry_point,
        )

    except Exception:
        adapter.close()
        raise


def build_new_xbrl(
    *,
    master_data,
    fiscal_year: FiscalYear,
    income_statement: IncomeStatement,
    balance_sheet: BalanceSheet,
    account_details,
    net_income,
) -> str:
    """Erzeugt die neue Taxonomie-6.9-XBRL-Instanz."""

    company_mapping = (
        GcdCompanyDataMapper().map(
            master_data
        )
    )

    company_data = (
        company_mapping.company_data
    )

    identifiers = (
        company_mapping.identifiers
    )

    gaap_ci_values = (
        GaapCi69ValueCalculator.calculate(
            income_statement=income_statement,
            net_income=net_income,
        )
    )

    print()
    print(
        "ERiC-relevante GuV-Werte:"
    )
    print(
        "  Jahresergebnis: "
        f"{gaap_ci_values.net_income}"
    )
    print(
        "  Ergebnis nach Steuern: "
        f"{gaap_ci_values.earnings_after_taxes}"
    )
    print(
        "  Betriebsergebnis: "
        f"{gaap_ci_values.operating_total_cost}"
    )
    print(
        "  Rohergebnis: "
        f"{gaap_ci_values.gross_trading_profit}"
    )

    profile = create_profile_6_9()

    report_profile = (
        GcdReportProfile.standard()
    )

    values = Taxonomy69ValueBuilder().build(
        company_data=company_data,
        identifiers=identifiers,
        report_profile=report_profile,
        fiscal_year=fiscal_year,
        gaap_ci_values=gaap_ci_values,
    )

    balance_sheet_values = (
        GaapCi69BalanceSheetValueBuilder.build(
            balance_sheet=balance_sheet,
            income_statement=(
                income_statement.income_statement
            ),
        )
    )

    values.update(
        balance_sheet_values
    )
    account_detail_values = (
        GaapCi69AccountDetailValueBuilder.build(
            account_details=account_details,
            tax_liability_accounts=("1776",),
            general_rate_sales_accounts=("8400",),
        )
    )

    values.update(
        account_detail_values
    )

    print()
    print(
        "Werthaltige GAAP-CI-Unterpositionen "
        "aus Kontensalden:"
    )

    for path, value in sorted(
        account_detail_values.items(),
        key=lambda item: item[0],
    ):
        print(
            f"  {'.'.join(path)} = {value}"
        )

    print()
    print(
        "Bilanzwerte an FactPlan übergeben: "
        f"{len(balance_sheet_values)}"
    )

    entity_identifier = (
        identifiers.tax_number_13
    )

    instant_context = TaxonomyContext(
        entity_identifier=entity_identifier,
        entity_scheme=ENTITY_SCHEME,
        period_type=(
            TaxonomyPeriodType.INSTANT
        ),
        start_date=None,
        end_date=fiscal_year.end_date,
    )

    duration_context = TaxonomyContext(
        entity_identifier=entity_identifier,
        entity_scheme=ENTITY_SCHEME,
        period_type=(
            TaxonomyPeriodType.DURATION
        ),
        start_date=fiscal_year.start_date,
        end_date=fiscal_year.end_date,
    )

    contexts_by_period_type = {
        TaxonomyPeriodType.INSTANT:
            instant_context,
        TaxonomyPeriodType.DURATION:
            duration_context,
    }

    (
        adapter,
        concepts,
        gcd_entry_point,
        gaap_ci_entry_point,
    ) = load_taxonomy_models()

    try:
        resolved_fact_plan = (
            FactPlanResolver().resolve(
                fact_plan=profile.fact_plan,
                concepts=concepts,
                contexts=(
                    contexts_by_period_type
                ),
                values=values,
            )
        )

        year = fiscal_year.end_date.year

        contexts = {
            f"ctx-instant-{year}":
                instant_context,
            f"ctx-duration-{year}":
                duration_context,
        }

        units = {
            "EUR": TaxonomyUnit.eur(),
            "PURE": TaxonomyUnit.pure(),
        }

        return (
            Taxonomy69XbrlDocumentBuilder()
            .build_xml(
                resolved_fact_plan=(
                    resolved_fact_plan
                ),
                contexts=contexts,
                units=units,
                entry_points=(
                    gcd_entry_point,
                    gaap_ci_entry_point,
                ),
            )
        )

    finally:
        adapter.close()

def main() -> None:
    """Führt den vollständigen lokalen ERiC-Praxistest aus."""

    config = load_config()

    validate_configuration(
        config
    )

    database = Database(
        config
    )

    database.create_database()

    session = database.create_session()

    try:
        company_repository = (
            CompanyRepository(
                session
            )
        )

        booking_repository = (
            BookingRepository(
                session
            )
        )

        chart_of_accounts_repository = (
            ChartOfAccountsRepository(
                session
            )
        )

        company = select_company(
            company_repository
            .list_companies()
        )

        print()
        print(
            "Ausgewählter Mandant: "
            f"{company.name}"
        )

        fiscal_year = (
            select_fiscal_year(
                company_repository
                .get_managed_fiscal_years(
                    company.company_id
                )
            )
        )

        print(
            "Ausgewähltes Geschäftsjahr: "
            f"{fiscal_year.display_name}"
        )

        master_data = (
            company_repository
            .get_master_data(
                company.company_id
            )
        )

        if master_data is None:
            raise RuntimeError(
                "Die Unternehmensstammdaten "
                "konnten nicht geladen werden."
            )

        print(
            "Mandantenstammdaten "
            "erfolgreich geladen."
        )

        financial_statement_context = (
            create_mandant_financial_statement_context(
                company=company,
                chart_of_accounts_repository=(
                    chart_of_accounts_repository
                ),
            )
        )

        print(
            "Mandantenspezifischer Kontenrahmen "
            "erfolgreich geladen."
        )

        pre_closing_ledger = (
            create_pre_closing_ledger(
                company=company,
                fiscal_year=fiscal_year,
                booking_repository=(
                    booking_repository
                ),
            )
        )
        account_detail_service = (
            EBilanzAccountDetailService(
                account_mapper=(
                    financial_statement_context
                    .account_mapper
                ),
                accounts=(
                    financial_statement_context
                    .accounts
                ),
            )
        )

        account_details = (
            account_detail_service.build(
                ledger=pre_closing_ledger,
            )
        )

        print(
            "E-Bilanz-Kontensalden erzeugt: "
            f"{len(account_details)}"
        )

        income_statement = (
            create_income_statement(
                ledger=pre_closing_ledger,
                financial_statement_context=(
                    financial_statement_context
                ),
            )
        )

        closing_service = (
            ClosingService()
        )

        net_income = (
            closing_service
            .calculate_net_income(
                income_statement=(
                    income_statement
                )
            )
        )

        print(
            "GuV erfolgreich aus "
            "SimpleOB-Buchungsdaten erzeugt."
        )
        print(
            "Jahresergebnis laut SimpleOB: "
            f"{net_income}"
        )

        balance_sheet = (
            create_balance_sheet(
                ledger=pre_closing_ledger,
                financial_statement_context=(
                    financial_statement_context
                ),
                net_income=net_income,
            )
        )

        print_balance_sheet_diagnostics(
            balance_sheet=balance_sheet,
            financial_statement_context=(
                financial_statement_context
            ),
        )

        xbrl_xml = build_new_xbrl(
            master_data=master_data,
            fiscal_year=fiscal_year,
            income_statement=(
                income_statement
            ),
            balance_sheet=balance_sheet,
            account_details=account_details,
            net_income=net_income,
        )

        OUTPUT_XBRL_FILE.write_text(
            xbrl_xml,
            encoding="utf-8",
        )

        print()
        print(
            "Neue Taxonomie-6.9-XBRL-Instanz "
            "erfolgreich erzeugt."
        )
        print(
            "XBRL-Datei: "
            f"{OUTPUT_XBRL_FILE}"
        )
        print(
            "XBRL-Länge: "
            f"{len(xbrl_xml)}"
        )

        payload_service = (
            ElsterBilanzPayloadService()
        )

        data_part_xml = (
            payload_service.build(
                xbrl_xml=xbrl_xml,
                master_data=master_data,
                balance_sheet_date=(
                    fiscal_year.end_date
                ),
            )
        )

        print()
        print(
            "SimpleOB-DatenTeil "
            "erfolgreich erzeugt."
        )
        print(
            "Bilanzstichtag: "
            f"{fiscal_year.end_date}"
        )
        print(
            "DatenTeil-Länge: "
            f"{len(data_part_xml)}"
        )

        eric_lib_dir = Path(
            config.eric_lib_dir
        ).expanduser()

        create_th_adapter = (
            EricCreateThAdapter(
                lib_dir=eric_lib_dir
            )
        )

        elster_xml = (
            create_th_adapter.create(
                data_part_xml=(
                    data_part_xml
                ),
                manufacturer_id=(
                    config
                    .eric_manufacturer_id
                ),
                version_client=(
                    get_application_version()
                ),
            )
        )

        print(
            "EricCreateTH erfolgreich."
        )
        print(
            "ElsterXML-Länge: "
            f"{len(elster_xml)}"
        )

        validate_adapter = (
            EricValidateAdapter(
                lib_dir=eric_lib_dir
            )
        )

        try:
            result = (
                validate_adapter.validate(
                    elster_xml=elster_xml,
                    datenart_version=(
                        "Bilanz_6.9"
                    ),
                )
            )

        except EricValidateError as exc:
            print()
            print(
                "ERiC-Validierung "
                "NICHT erfolgreich."
            )
            print(
                "Fehlercode: "
                f"{exc.error_code}"
            )
            print(
                "Fehlertext: "
                f"{exc.error_text}"
            )
            print(
                "Rückgabe-XML vorhanden: "
                f"{bool(exc.response_xml)}"
            )

            if exc.response_xml:
                print(
                    "--- ERiC-Rückgabe ---"
                )
                print(
                    exc.response_xml
                )

            return

        print()
        print(
            "ERiC-Validierung erfolgreich."
        )

        if result.response_xml:
            print(
                "--- ERiC-Rückgabe ---"
            )
            print(
                result.response_xml
            )

    finally:
        session.close()


if __name__ == "__main__":
    main()

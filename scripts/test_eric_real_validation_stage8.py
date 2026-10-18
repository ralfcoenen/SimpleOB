#!/usr/bin/env python3
"""Manueller Stage-8-Praxistest des SimpleOB-ERiC-Pfads für Taxonomie 6.9.

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

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from simpleob.accounting.balance_sheet import BalanceSheet
from simpleob.accounting.financial_statement_context import (
    create_financial_statement_context,
    create_standard_financial_statement_context,
)
from simpleob.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from simpleob.accounting.income_statement import IncomeStatement
from simpleob.accounting.ledger import Ledger
from simpleob.core.config import load_config
from simpleob.core.version import get_application_version
from simpleob.database.booking_repository import BookingRepository
from simpleob.database.chart_of_accounts_repository import (
    ChartOfAccountsRepository,
)
from simpleob.database.company_repository import CompanyRepository
from simpleob.database.database import Database
from simpleob.database.fixed_asset_depreciation_repository import (
    FixedAssetDepreciationRepository,
)
from simpleob.database.fixed_asset_movement_repository import (
    FixedAssetMovementRepository,
)
from simpleob.database.fixed_asset_repository import FixedAssetRepository
from simpleob.database.shareholder_repository import (
    ShareholderRepository,
)
from simpleob.domain.account_type import AccountType
from simpleob.domain.booking_type import BookingType
from simpleob.domain.company import Company
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.fiscal_year_status import FiscalYearStatus
from simpleob.domain.managed_fiscal_year import ManagedFiscalYear
from simpleob.domain.money import ZERO
from simpleob.eric.bilanz_generation.fact_plan_resolver import (
    FactPlanResolver,
)
from simpleob.eric.bilanz_generation.gaap_ci_6_9_account_detail_values import (
    GaapCi69AccountDetailValueBuilder,
)
from simpleob.eric.bilanz_generation.gaap_ci_6_9_balance_sheet_values import (
    GaapCi69BalanceSheetValueBuilder,
)
from simpleob.eric.bilanz_generation.gaap_ci_6_9_income_statement_values import (
    GaapCi69IncomeStatementValueBuilder,
)
from simpleob.eric.bilanz_generation.gaap_ci_6_9_values import (
    GaapCi69ValueCalculator,
)
from simpleob.eric.bilanz_generation.taxonomy_6_9 import (
    create_profile_6_9,
)
from simpleob.eric.bilanz_generation.taxonomy_6_9_values import (
    Taxonomy69ValueBuilder,
)
from simpleob.eric.bilanz_generation.taxonomy_6_9_xbrl_document_builder import (
    Taxonomy69XbrlDocumentBuilder,
)
from simpleob.eric.elster_bilanz_payload_service import (
    ElsterBilanzPayloadService,
)
from simpleob.eric.eric_create_th_adapter import (
    EricCreateThAdapter,
)
from simpleob.eric.eric_validate_adapter import (
    EricValidateAdapter,
    EricValidateError,
)
from simpleob.services.closing_result import ClosingResult
from simpleob.services.closing_service import ClosingService
from simpleob.services.e_bilanz_account_detail_service import (
    EBilanzAccountDetailService,
)
from simpleob.services.e_bilanz_service import EBilanzService
from simpleob.services.fixed_asset_schedule_service import (
    FixedAssetScheduleService,
)
from simpleob.services.posting_service import PostingService
from simpleob.taxonomy.account_balance_builder import (
    AccountBalanceBuilder,
)
from simpleob.taxonomy.arelle_adapter import ArelleAdapter
from simpleob.taxonomy.concept import TaxonomyPeriodType
from simpleob.taxonomy.concept_set import TaxonomyConceptSet
from simpleob.taxonomy.context import TaxonomyContext
from simpleob.taxonomy.entry_point import TaxonomyEntryPoint
from simpleob.taxonomy.fact import TaxonomyFact
from simpleob.taxonomy.fiscal_requirement_reader import (
    FiscalRequirement,
    FiscalRequirementReader,
)
from simpleob.taxonomy.fixed_asset_schedule_builder import (
    FixedAssetScheduleBuilder,
)
from simpleob.taxonomy.gaap_ci_mandatory_fact_completer import (
    GaapCiMandatoryFactCompleter,
)
from simpleob.taxonomy.gcd_company_data_mapper import (
    GcdCompanyDataMapper,
)
from simpleob.taxonomy.gcd_fact_builder import GcdFactBuilder
from simpleob.taxonomy.gcd_report_profile import GcdReportProfile
from simpleob.taxonomy.gcd_shareholder import (
    GcdShareDivideKey,
    GcdShareholder,
    GcdShareholderLegalStatus,
)
from simpleob.taxonomy.hgb_gaap_ci_mapping import (
    create_hgb_gaap_ci_mapping,
)
from simpleob.taxonomy.mapper import TaxonomyMapper
from simpleob.taxonomy.nil_fact import TaxonomyNilFact
from simpleob.taxonomy.resolver import TaxonomyResolver
from simpleob.taxonomy.taxonomy import TaxonomyVersion
from simpleob.taxonomy.unit import TaxonomyUnit

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

BALANCE_SHEET_ROLE = (
    "http://www.xbrl.de/taxonomies/de-gaap-ci/role/balanceSheet"
)

INCOME_STATEMENT_ROLE = (
    "http://www.xbrl.de/taxonomies/de-gaap-ci/role/incomeStatement"
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


def find_previous_fiscal_year(
    *,
    fiscal_year: FiscalYear,
    fiscal_years: tuple[
        ManagedFiscalYear,
        ...,
    ],
) -> FiscalYear | None:
    """Ermittelt das chronologisch vorherige Geschäftsjahr."""

    previous_candidates = tuple(
        managed.fiscal_year
        for managed in fiscal_years
        if managed.fiscal_year.end_date < fiscal_year.start_date
    )

    if not previous_candidates:
        return None

    return max(
        previous_candidates,
        key=lambda candidate: candidate.end_date,
    )


def create_gcd_shareholders(
    shareholders,
) -> tuple[GcdShareholder, ...]:
    """Überführt gespeicherte Gesellschafter in das bestehende GCD-Modell."""

    result: list[GcdShareholder] = []

    for shareholder in shareholders:
        try:
            legal_status = GcdShareholderLegalStatus(
                shareholder.legal_status
            )
        except ValueError as exc:
            raise ValueError(
                "Unbekannte GCD-Rechtsstellung des Gesellschafters "
                f"{shareholder.shareholder_number}: "
                f"{shareholder.legal_status}"
            ) from exc

        result.append(
            GcdShareholder(
                name=shareholder.name,
                first_name=(
                    shareholder.first_name
                    if shareholder.first_name
                    else None
                ),
                shareholder_id=shareholder.shareholder_number,
                tax_number=(
                    shareholder.tax_number
                    if shareholder.tax_number
                    else None
                ),
                tax_id=(
                    shareholder.tax_id
                    if shareholder.tax_id
                    else None
                ),
                wid=(
                    shareholder.wid
                    if shareholder.wid
                    else None
                ),
                legal_status=legal_status,
                share_divide_key=GcdShareDivideKey(
                    numerator=shareholder.share_numerator,
                    denominator=shareholder.share_denominator,
                ),
            )
        )

    return tuple(result)


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


def collect_existing_numeric_or_nil_facts(
    resolved_fact_plan,
):
    """Sammelt vorhandene numerische VALUE- und NIL-Facts rekursiv."""

    facts: list[TaxonomyFact | TaxonomyNilFact] = []

    def visit(node) -> None:
        if isinstance(
            node.fact,
            (TaxonomyFact, TaxonomyNilFact),
        ):
            facts.append(node.fact)

        for child in node.children:
            visit(child)

    for node in resolved_fact_plan.nodes:
        visit(node)

    return tuple(facts)


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
            gcd_model,
            gaap_ci_model,
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
    previous_fiscal_year: FiscalYear | None,
    shareholders: tuple[GcdShareholder, ...],
    income_statement: IncomeStatement,
    balance_sheet: BalanceSheet,
    account_details,
    fixed_asset_schedule,
    financial_statement_context,
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

    bvv_report_element = (
        "genInfo.report.id.reportElement."
        "reportElements.BVV"
    )

    report_profile = replace(
        report_profile,
        report_elements=(
            *report_profile.report_elements,
            bvv_report_element,
        ),
    )

    if account_details:
        report_profile = replace(
            report_profile,
            report_elements=(
                *report_profile.report_elements,
                (
                    "genInfo.report.id.reportElement."
                    "reportElements.KS"
                ),
            ),
        )

    balance_sheet_values = (
        GaapCi69BalanceSheetValueBuilder.build(
            balance_sheet=balance_sheet,
            income_statement=(
                income_statement.income_statement
            ),
        )
    )

    income_statement_values = (
        GaapCi69IncomeStatementValueBuilder.build(
            income_statement=income_statement,
            assets=balance_sheet.assets,
            liabilities=balance_sheet.liabilities,
            fixed_asset_schedule=fixed_asset_schedule,
        )
    )

    account_detail_values = (
        GaapCi69AccountDetailValueBuilder.build(
            account_details=account_details,
            tax_liability_accounts=("1776",),
            general_rate_sales_accounts=("8400",),
            cash_accounts=("1000",),
            bank_accounts=("1200",),
            input_tax_receivable_accounts=("1576",),
        )
    )

    bvv_values = {
        ("BVV.profitLoss",):
            Decimal("1073.76"),
        ("BVV.profitLoss.assetsCurrentYear",):
            Decimal("11073.76"),
        ("BVV.profitLoss.assetsPreviousYear",):
            Decimal("0.00"),
        ("BVV.profitLoss.assetsPreviousYear.assets",):
            Decimal("0.00"),
        (
            "BVV.profitLoss.assetsPreviousYear."
            "capAdjustments",
        ):
            Decimal("0.00"),
        ("BVV.profitLoss.withdrawalDistrib",):
            Decimal("0.00"),
        ("BVV.profitLoss.contribution",):
            Decimal("10000.00"),
    }

    print()
    print(
        "Kontrollierte BVV-Testwerte:"
    )

    for path, value in sorted(
        bvv_values.items(),
        key=lambda item: item[0],
    ):
        print(
            f"  {'.'.join(path)} = {value}"
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

    print()
    print(
        "Werthaltige GAAP-CI-GuV-Werte "
        "aus HGB-GuV:"
    )

    for path, value in sorted(
        income_statement_values.items(),
        key=lambda item: item[0],
    ):
        print(
            f"  {'.'.join(path)} = {value}"
        )

    print()
    print(
        "GuV-Werte an FactPlan übergeben: "
        f"{len(income_statement_values)}"
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
        gcd_model,
        gaap_ci_model,
        gcd_entry_point,
        gaap_ci_entry_point,
    ) = load_taxonomy_models()

    try:
        gcd_fact_builder = GcdFactBuilder()

        shareholder_tuples = tuple(
            gcd_fact_builder.shareholder(
                shareholder=shareholder,
                taxonomy_model=gcd_model,
                context=duration_context,
            )
            for shareholder in shareholders
        )

        print(
            "GCD-Gesellschafter-Tuples erzeugt: "
            f"{len(shareholder_tuples)}"
        )

        taxonomy_mapper = TaxonomyMapper(
            create_hgb_gaap_ci_mapping(
                assets=(
                    financial_statement_context.assets
                ),
                liabilities=(
                    financial_statement_context.liabilities
                ),
                income_statement=(
                    financial_statement_context.income_statement
                ),
            ),
            gaap_ci_model,
        )

        account_balance_builder = (
            AccountBalanceBuilder(
                taxonomy_model=gaap_ci_model,
                taxonomy_mapper=taxonomy_mapper,
            )
        )

        account_balances = tuple(
            account_balance_builder.build(
                detail=detail,
                context=duration_context,
            )
            for detail in account_details
        )

        print(
            "KS-Kontennachweis-Tuples erzeugt: "
            f"{len(account_balances)}"
        )


        include_fixed_asset_schedule = True

        fixed_asset_schedule_xbrl = None

        if include_fixed_asset_schedule:
            fixed_asset_schedule_xbrl = (
                FixedAssetScheduleBuilder(
                    taxonomy_model=gaap_ci_model,
                    taxonomy_mapper=taxonomy_mapper,
                ).build(
                    positions=fixed_asset_schedule,
                    entity_identifier=entity_identifier,
                    entity_scheme=ENTITY_SCHEME,
                    fiscal_year_start=fiscal_year.start_date,
                    fiscal_year_end=fiscal_year.end_date,
                )
            )

            print(
                "BAL-Anlagenspiegel-Positionen aus SimpleOB: "
                f"{len(fixed_asset_schedule)}"
            )
            print(
                "BAL-Anlagenspiegel-Facts erzeugt: "
                f"{len(fixed_asset_schedule_xbrl.facts)}"
            )
            print(
                "BAL-Anlagenspiegel-NIL-Facts erzeugt: "
                f"{len(fixed_asset_schedule_xbrl.nil_facts)}"
            )

            if fixed_asset_schedule_xbrl.facts:
                report_profile = replace(
                    report_profile,
                    report_elements=(
                        *report_profile.report_elements,
                        (
                            "genInfo.report.id.reportElement."
                            "reportElements.BAL"
                        ),
                    ),
                )
        else:
            print(
                "BAL-Anlagenspiegel für HAOE-Test "
                "absichtlich nicht in XBRL übernommen."
            )

        values = Taxonomy69ValueBuilder().build(
            company_data=company_data,
            identifiers=identifiers,
            report_profile=report_profile,
            fiscal_year=fiscal_year,
            previous_fiscal_year=previous_fiscal_year,
            gaap_ci_values=gaap_ci_values,
        )
        values.update(
            balance_sheet_values
        )

        values.update(
            income_statement_values
        )

        values.update(
            account_detail_values
        )

        values.update(
            bvv_values
        )

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

        existing_numeric_or_nil_facts = (
            collect_existing_numeric_or_nil_facts(
                resolved_fact_plan
            )
        )

        requirements = FiscalRequirementReader(
            gaap_ci_entry_point
        ).requirements()

        mandatory_nil_facts = (
            GaapCiMandatoryFactCompleter(
                taxonomy_model=gaap_ci_model
            ).build_missing_nil_facts(
                requirements=requirements,
                existing_facts=existing_numeric_or_nil_facts,
                instant_context=instant_context,
                duration_context=duration_context,
                unit=TaxonomyUnit.eur(),
                active_report_element_roles=(
                    BALANCE_SHEET_ROLE,
                    INCOME_STATEMENT_ROLE,
                ),
                excluded_concept_prefixes=(
                    "is.netIncome.regular.operatingCOGS",
                ),
            )
        )

        requirement_by_concept = {
            requirement.concept_name: requirement
            for requirement in requirements
        }

        added_required = sum(
            1
            for fact in mandatory_nil_facts
            if requirement_by_concept[
                fact.concept.name
            ].requirement is FiscalRequirement.REQUIRED
        )
        added_sum_required = sum(
            1
            for fact in mandatory_nil_facts
            if requirement_by_concept[
                fact.concept.name
            ].requirement is FiscalRequirement.SUM_REQUIRED
        )

        kst_mandatory_count = sum(
            1
            for requirement in requirements
            if requirement.legal_form_kst
            and requirement.requirement in {
                FiscalRequirement.REQUIRED,
                FiscalRequirement.SUM_REQUIRED,
            }
        )

        print()
        print(
            "KSt-Pflichtfelder Taxonomie 6.9: "
            f"{kst_mandatory_count}"
        )
        print(
            "Bereits vorhandene numerische/NIL-Facts: "
            f"{len(existing_numeric_or_nil_facts)}"
        )
        print(
            "Zusätzlich erzeugte B/GuV-KSt-Pflicht-NIL-Facts: "
            f"{len(mandatory_nil_facts)}"
        )
        print(
            "  davon Mussfelder: "
            f"{added_required}"
        )
        print(
            "  davon Summenmussfelder: "
            f"{added_sum_required}"
        )

        year = fiscal_year.end_date.year

        contexts = {
            f"ctx-instant-{year}": instant_context,
            f"ctx-duration-{year}": duration_context,
        }

        fixed_asset_nil_facts = ()
        fixed_asset_facts = ()

        if fixed_asset_schedule_xbrl is not None:
            contexts.update(
                fixed_asset_schedule_xbrl.contexts
            )
            fixed_asset_nil_facts = (
                fixed_asset_schedule_xbrl.nil_facts
            )
            fixed_asset_facts = (
                fixed_asset_schedule_xbrl.facts
            )

        units = {
            "EUR": TaxonomyUnit.eur(),
            "PURE": TaxonomyUnit.pure(),
        }

        return (
            Taxonomy69XbrlDocumentBuilder()
            .build_xml(
                resolved_fact_plan=resolved_fact_plan,
                contexts=contexts,
                units=units,
                entry_points=(
                    gcd_entry_point,
                    gaap_ci_entry_point,
                ),
                shareholders=shareholder_tuples,
                nil_facts=(
                    mandatory_nil_facts
                    + fixed_asset_nil_facts
                ),
                account_balances=account_balances,
                facts=fixed_asset_facts,
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

        shareholder_repository = (
            ShareholderRepository(
                session
            )
        )

        fixed_asset_repository = FixedAssetRepository(session)
        fixed_asset_movement_repository = (
            FixedAssetMovementRepository(session)
        )
        fixed_asset_depreciation_repository = (
            FixedAssetDepreciationRepository(session)
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

        managed_fiscal_years = (
            company_repository
            .get_managed_fiscal_years(
                company.company_id
            )
        )

        fiscal_year = (
            select_fiscal_year(
                managed_fiscal_years
            )
        )

        previous_fiscal_year = (
            find_previous_fiscal_year(
                fiscal_year=fiscal_year,
                fiscal_years=managed_fiscal_years,
            )
        )

        print(
            "Ausgewähltes Geschäftsjahr: "
            f"{fiscal_year.display_name}"
        )

        if previous_fiscal_year is None:
            print(
                "Vorheriges Geschäftsjahr: "
                "nicht vorhanden"
            )
        else:
            print(
                "Vorheriges Geschäftsjahr: "
                f"{previous_fiscal_year.display_name}"
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

        vat_accounts = (
            chart_of_accounts_repository
            .load_vat_accounts(
                company.company_id
            )
        )

        account_roles = (
            chart_of_accounts_repository
            .load_account_roles(
                company.company_id
            )
        )

        if (
            vat_accounts is None
            or account_roles is None
        ):
            raise RuntimeError(
                "Die mandantenspezifische "
                "Kontenkonfiguration ist unvollständig."
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

        print()
        print("E-Bilanz-Kontensalden im Detail:")

        for detail in account_details:
            print(
                "  "
                f"Konto {detail.account_number}: "
                f"{detail.account_description} | "
                f"HGB={detail.position.code} | "
                f"Saldo={detail.balance}"
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

        stored_shareholders = (
            shareholder_repository.list_for_company(
                company.company_id
            )
        )

        print(
            "Gesellschafter aus SimpleOB geladen: "
            f"{len(stored_shareholders)}"
        )

        fixed_asset_schedule = (
            FixedAssetScheduleService(
                fixed_asset_repository=fixed_asset_repository,
                fixed_asset_movement_repository=(
                    fixed_asset_movement_repository
                ),
                fixed_asset_depreciation_repository=(
                    fixed_asset_depreciation_repository
                ),
            ).build(
                company_id=company.company_id,
                fiscal_year_start=fiscal_year.start_date,
                fiscal_year_end=fiscal_year.end_date,
            )
        )

        print(
            "Anlagenspiegel aus SimpleOB erzeugt: "
            f"{len(fixed_asset_schedule)} Position(en)"
        )

        company_mapping = (
            GcdCompanyDataMapper().map(
                master_data
            )
        )

        e_bilanz_adapter = ArelleAdapter()

        try:
            e_bilanz_service = EBilanzService(
                resolver=TaxonomyResolver(
                    root=TAXONOMY_ROOT
                ),
                adapter=e_bilanz_adapter,
                company_data_mapper=(
                    GcdCompanyDataMapper()
                ),
                assets=(
                    financial_statement_context.assets
                ),
                liabilities=(
                    financial_statement_context.liabilities
                ),
                income_statement=(
                    financial_statement_context
                    .income_statement
                ),
            )

            document = e_bilanz_service.build(
                master_data=master_data,
                fiscal_year=fiscal_year,
                previous_fiscal_year=(
                    previous_fiscal_year
                ),
                amounts={
                    **balance_sheet.amounts,
                    **income_statement.amounts,
                },
                income_statement=income_statement,
                balance_sheet=balance_sheet,
                vat_accounts=vat_accounts,
                account_roles=account_roles,
                entity_identifier=(
                    company_mapping
                    .identifiers
                    .tax_number_13
                ),
                entity_scheme=ENTITY_SCHEME,
                account_details=account_details,
                fixed_asset_schedule=(
                    fixed_asset_schedule
                ),
                shareholders=tuple(
                    stored_shareholders
                ),
            )

            xbrl_xml = document.xml

        finally:
            e_bilanz_adapter.close()
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

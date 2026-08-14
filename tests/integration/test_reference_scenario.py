"""Integrationstests für das persistente Referenzszenario."""
import pytest
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from openbilanz.accounting.balance_sheet import BalanceSheet
from openbilanz.accounting.financial_statement_builder import (
    FinancialStatementBuilder,
)
from openbilanz.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.accounting.ledger import Ledger
from openbilanz.accounting.mapper import AccountMapper
from openbilanz.accounting.trial_balance import TrialBalance
from openbilanz.database.booking_repository import BookingRepository
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.database.database import Base
from openbilanz.demo.reference_scenario import (
    REFERENCE_COMPANY_ID,
    create_reference_scenario,
    persist_reference_scenario,
)
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.fiscal_year_status import FiscalYearStatus
from openbilanz.domain.journal import Journal
from openbilanz.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from openbilanz.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from openbilanz.importers.csv_chart_of_accounts_importer import (
    CsvChartOfAccountsImporter,
)
from openbilanz.services.closing_accounts import ClosingAccounts
from openbilanz.services.closing_service import ClosingService
from openbilanz.services.fiscal_year_closing_workflow import (
    FiscalYearClosingWorkflow,
)
from openbilanz.services.posting_service import PostingService
from openbilanz.taxonomy.arelle_adapter import ArelleAdapter
from openbilanz.taxonomy.e_bilanz_builder import EBilanzBuilder
from openbilanz.taxonomy.entry_point import TaxonomyEntryPoint
from openbilanz.taxonomy.gcd_company_data import GcdCompanyData
from openbilanz.taxonomy.gcd_company_identifiers import (
    GcdCompanyIdentifiers,
)
from openbilanz.taxonomy.resolver import TaxonomyResolver
from openbilanz.taxonomy.taxonomy import TaxonomyVersion


STANDARD_CHART_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "openbilanz"
    / "resources"
    / "chart_of_accounts"
    / "openbilanz_standard.csv"
)



TAXONOMY_ROOT = Path(
    "/tmp/openbilanz-taxonomy"
)

TEST_ENTITY_SCHEME = (
    "http://www.bundesfinanzministerium.de"
)

GCD_NAMESPACE_6_10 = (
    "http://www.xbrl.de/taxonomies/"
    "de-gcd-2026-04-01"
)

GAAP_CI_NAMESPACE_6_10 = (
    "http://www.xbrl.de/taxonomies/"
    "de-gaap-ci-2026-04-01"
)

@dataclass(frozen=True)
class ReferenceAccounting:
    """Aufgebautes Referenzszenario vor dem Jahresabschluss."""

    scenario: object
    company_repository: CompanyRepository
    booking_repository: BookingRepository
    chart_of_accounts: object
    account_types: dict[str, AccountType]
    ledger: Ledger
    journal: Journal
    posting_service: PostingService
    statement_builder: FinancialStatementBuilder
    assets: object
    liabilities: object
    income_statement_root: object
    income_statement: IncomeStatement
    income_statement_amounts: dict


def _create_session():
    """Erzeugt eine leere SQLite-In-Memory-Testdatenbank."""

    engine = create_engine(
        "sqlite:///:memory:"
    )

    Base.metadata.create_all(
        engine
    )

    Session = sessionmaker(
        bind=engine
    )

    return Session()

def _build_reference_accounting(
    session,
) -> ReferenceAccounting:
    """Baut das persistierte Referenzszenario bis zur HGB-GuV auf."""

    company_repository = CompanyRepository(
        session
    )
    booking_repository = BookingRepository(
        session
    )

    scenario = create_reference_scenario()

    persist_reference_scenario(
        scenario=scenario,
        company_repository=company_repository,
        booking_repository=booking_repository,
    )

    assets, liabilities = (
        create_hgb_balance_sheet_structure()
    )

    income_statement_root = (
        create_hgb_income_statement_structure()
    )

    provider = HgbFinancialStatementPositionProvider(
        (
            assets,
            liabilities,
            income_statement_root,
        )
    )

    chart_of_accounts = CsvChartOfAccountsImporter(
        position_provider=provider,
    ).load(
        STANDARD_CHART_PATH
    )

    account_types = {
        account.account_number: account.account_type
        for account in chart_of_accounts.accounts
    }

    persisted_bookings = (
        booking_repository.list_for_fiscal_year(
            company_id=REFERENCE_COMPANY_ID,
            fiscal_year=scenario.fiscal_year,
        )
    )

    journal = Journal()
    ledger = Ledger()
    posting_service = PostingService()

    for booking in persisted_bookings:
        posting_service.post_booking(
            booking=booking,
            journal=journal,
            ledger=ledger,
        )

    mapper = AccountMapper(
        chart_of_accounts
    )

    statement_builder = FinancialStatementBuilder(
        mapper
    )

    income_statement_balances = tuple(
        balance
        for balance in ledger.balances()
        if account_types.get(balance.account_number)
        in (
            AccountType.REVENUE,
            AccountType.EXPENSE,
        )
    )

    income_statement_amounts = (
        statement_builder.build(
            balances=income_statement_balances,
            root_positions=(
                income_statement_root,
            ),
        )
    )

    income_statement = IncomeStatement(
        income_statement=income_statement_root,
        amounts=income_statement_amounts,
    )

    return ReferenceAccounting(
        scenario=scenario,
        company_repository=company_repository,
        booking_repository=booking_repository,
        chart_of_accounts=chart_of_accounts,
        account_types=account_types,
        ledger=ledger,
        journal=journal,
        posting_service=posting_service,
        statement_builder=statement_builder,
        assets=assets,
        liabilities=liabilities,
        income_statement_root=income_statement_root,
        income_statement=income_statement,
        income_statement_amounts=income_statement_amounts,
    )

def test_persists_complete_reference_scenario() -> None:
    """Das vollständige Referenzszenario wird persistent gespeichert."""

    with _create_session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )

        scenario = create_reference_scenario()

        persist_reference_scenario(
            scenario=scenario,
            company_repository=company_repository,
            booking_repository=booking_repository,
        )

        company = company_repository.get(
            REFERENCE_COMPANY_ID
        )

        assert company == scenario.company

        fiscal_years = (
            company_repository.get_fiscal_years(
                REFERENCE_COMPANY_ID
            )
        )

        assert fiscal_years == (
            scenario.fiscal_year,
        )

        bookings = (
            booking_repository.list_for_fiscal_year(
                company_id=REFERENCE_COMPANY_ID,
                fiscal_year=scenario.fiscal_year,
            )
        )

        assert len(bookings) == 20
        assert bookings == scenario.bookings


def test_reconstructs_reference_ledger_from_database() -> None:
    """Persistierte Buchungen ergeben die erwarteten Kontensalden."""

    with _create_session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )

        scenario = create_reference_scenario()

        persist_reference_scenario(
            scenario=scenario,
            company_repository=company_repository,
            booking_repository=booking_repository,
        )

        bookings = (
            booking_repository.list_for_fiscal_year(
                company_id=REFERENCE_COMPANY_ID,
                fiscal_year=scenario.fiscal_year,
            )
        )

        journal = Journal()
        ledger = Ledger()
        posting_service = PostingService()

        for booking in bookings:
            posting_service.post_booking(
                booking=booking,
                journal=journal,
                ledger=ledger,
            )

        trial_balance = TrialBalance(
            ledger
        )

        balances = {
            row.account_number: row
            for row in trial_balance
        }

        assert (
            balances["0400"].debit_balance
            == Decimal("3200.00")
        )
        assert (
            balances["0800"].credit_balance
            == Decimal("12500.00")
        )
        assert (
            balances["1200"].debit_balance
            == Decimal("13905.00")
        )
        assert (
            balances["1400"].debit_balance
            == Decimal("2900.00")
        )

        assert (
            balances["1576"].debit_balance
            == Decimal("1805.00")
        )
        assert (
            balances["1600"].credit_balance
            == Decimal("1190.00")
        )
        assert (
            balances["1776"].credit_balance
            == Decimal("3040.00")
        )

        assert (
            balances["3100"].debit_balance
            == Decimal("3000.00")
        )
        assert (
            balances["4210"].debit_balance
            == Decimal("3600.00")
        )
        assert (
            balances["4360"].debit_balance
            == Decimal("600.00")
        )
        assert (
            balances["4600"].debit_balance
            == Decimal("1000.00")
        )
        assert (
            balances["4800"].debit_balance
            == Decimal("500.00")
        )
        assert (
            balances["4830"].debit_balance
            == Decimal("800.00")
        )
        assert (
            balances["4920"].debit_balance
            == Decimal("600.00")
        )
        assert (
            balances["4930"].debit_balance
            == Decimal("400.00")
        )
        assert (
            balances["4945"].debit_balance
            == Decimal("800.00")
        )
        assert (
            balances["4970"].debit_balance
            == Decimal("120.00")
        )

        assert (
            balances["8400"].credit_balance
            == Decimal("16000.00")
        )
        assert (
            balances["8500"].credit_balance
            == Decimal("500.00")
        )

        assert len(journal) == 20

        assert trial_balance.is_turnover_balanced
        assert trial_balance.is_balance_balanced


def test_reference_scenario_has_expected_net_income() -> None:
    """Der Referenzfall erzielt den erwarteten Jahresüberschuss."""

    with _create_session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )

        scenario = create_reference_scenario()

        persist_reference_scenario(
            scenario=scenario,
            company_repository=company_repository,
            booking_repository=booking_repository,
        )

        bookings = (
            booking_repository.list_for_fiscal_year(
                company_id=REFERENCE_COMPANY_ID,
                fiscal_year=scenario.fiscal_year,
            )
        )

        ledger = Ledger()
        posting_service = PostingService()

        for booking in bookings:
            posting_service.post_booking(
                booking=booking,
                ledger=ledger,
            )

        trial_balance = TrialBalance(
            ledger
        )

        balances = {
            row.account_number: row
            for row in trial_balance
        }

        revenue = (
            balances["8400"].credit_balance
            + balances["8500"].credit_balance
        )

        expenses = (
            balances["3100"].debit_balance
            + balances["4210"].debit_balance
            + balances["4360"].debit_balance
            + balances["4600"].debit_balance
            + balances["4800"].debit_balance
            + balances["4830"].debit_balance
            + balances["4920"].debit_balance
            + balances["4930"].debit_balance
            + balances["4945"].debit_balance
            + balances["4970"].debit_balance
        )

        assert revenue == Decimal("16500.00")
        assert expenses == Decimal("11420.00")

        assert (
            revenue - expenses
            == Decimal("5080.00")
        )

def test_closes_reference_scenario_and_persists_year_end() -> None:
    """Der Referenzfall wird vollständig und persistent abgeschlossen."""

    with _create_session() as session:
        accounting = _build_reference_accounting(
            session
        )

        assert len(accounting.journal) == 20

        closing_service = ClosingService(
            closing_accounts=ClosingAccounts(
                income_summary_account="8990",
                profit_account="8020",
                loss_account="8021",
            )
        )

        workflow = FiscalYearClosingWorkflow(
            session=session,
            booking_repository=accounting.booking_repository,
            company_repository=accounting.company_repository,
            closing_service=closing_service,
        )

        closing_result = workflow.close(
            company_id=REFERENCE_COMPANY_ID,
            fiscal_year=accounting.scenario.fiscal_year,
            income_statement=accounting.income_statement,
            ledger=accounting.ledger,
            chart_of_accounts=accounting.chart_of_accounts,
            closing_date=accounting.scenario.fiscal_year.end_date,
        )

        assert (
            closing_result.net_income
            == Decimal("5080.00")
        )

        managed_fiscal_years = (
            accounting.company_repository.get_managed_fiscal_years(
                REFERENCE_COMPANY_ID
            )
        )

        assert len(managed_fiscal_years) == 1

        assert (
            managed_fiscal_years[0].status
            is FiscalYearStatus.CLOSED
        )

        all_bookings = (
            accounting.booking_repository.list_for_fiscal_year(
                company_id=REFERENCE_COMPANY_ID,
                fiscal_year=accounting.scenario.fiscal_year,
            )
        )

        descriptions = {
            booking.description
            for booking in all_bookings
        }

        assert len(all_bookings) == 33

        assert (
            "Abschluss des Erlöskontos 8400"
            in descriptions
        )
        assert (
            "Abschluss des Erlöskontos 8500"
            in descriptions
        )
        assert (
            "Abschluss des Aufwandskontos 3100"
            in descriptions
        )
        assert (
            "Abschluss des Aufwandskontos 4830"
            in descriptions
        )
        assert (
            "Abschluss des Aufwandskontos 4970"
            in descriptions
        )
        assert (
            "Abschluss des GuV-Kontos"
            in descriptions
        )

        closed_ledger = Ledger()
        closed_journal = Journal()

        for booking in all_bookings:
            accounting.posting_service.post_booking(
                booking=booking,
                journal=closed_journal,
                ledger=closed_ledger,
            )

        closed_trial_balance = TrialBalance(
            closed_ledger
        )

        closed_balances = {
            row.account_number: row
            for row in closed_trial_balance
        }

        for account_number in (
            "8400",
            "8500",
        ):
            assert (
                closed_balances[
                    account_number
                ].debit_balance
                == Decimal("0.00")
            )
            assert (
                closed_balances[
                    account_number
                ].credit_balance
                == Decimal("0.00")
            )

        for account_number in (
            "3100",
            "4210",
            "4360",
            "4600",
            "4800",
            "4830",
            "4920",
            "4930",
            "4945",
            "4970",
        ):
            assert (
                closed_balances[
                    account_number
                ].debit_balance
                == Decimal("0.00")
            )
            assert (
                closed_balances[
                    account_number
                ].credit_balance
                == Decimal("0.00")
            )

        assert (
            closed_balances["8990"].debit_balance
            == Decimal("0.00")
        )
        assert (
            closed_balances["8990"].credit_balance
            == Decimal("0.00")
        )

        assert (
            closed_balances["8020"].credit_balance
            == Decimal("5080.00")
        )

        assert closed_trial_balance.is_turnover_balanced
        assert closed_trial_balance.is_balance_balanced

        balance_sheet_balances = tuple(
            balance
            for balance in closed_ledger.balances()
            if (
                accounting.account_types.get(
                    balance.account_number
                )
                in (
                    AccountType.ASSET,
                    AccountType.LIABILITY,
                    AccountType.EQUITY,
                )
                and (
                    balance.debit_balance
                    > Decimal("0.00")
                    or balance.credit_balance
                    > Decimal("0.00")
                )
                and balance.account_number != "8990"
            )
        )

        balance_sheet_amounts = (
            accounting.statement_builder.build(
                balances=balance_sheet_balances,
                root_positions=(
                    accounting.assets,
                    accounting.liabilities,
                ),
            )
        )

        balance_sheet = BalanceSheet(
            assets=accounting.assets,
            liabilities=accounting.liabilities,
            amounts=balance_sheet_amounts,
        )

        positions = {
            position.code: position
            for root in (
                accounting.assets,
                accounting.liabilities,
            )
            for position in _walk_positions(root)
        }

        assert (
            balance_sheet.amount_for(
                positions[
                    "HGB.266.AKTIVA.A.II.3"
                ]
            )
            == Decimal("3200.00")
        )

        assert (
            balance_sheet.amount_for(
                positions[
                    "HGB.266.AKTIVA.B.IV"
                ]
            )
            == Decimal("13905.00")
        )

        assert (
            balance_sheet.amount_for(
                positions[
                    "HGB.266.AKTIVA.B.II.1"
                ]
            )
            == Decimal("2900.00")
        )

        assert (
            balance_sheet.amount_for(
                positions[
                    "HGB.266.AKTIVA.B.II.4"
                ]
            )
            == Decimal("1805.00")
        )

        assert (
            balance_sheet.amount_for(
                positions[
                    "HGB.266.PASSIVA.A.I"
                ]
            )
            == Decimal("12500.00")
        )

        assert (
            balance_sheet.amount_for(
                positions[
                    "HGB.266.PASSIVA.A.V"
                ]
            )
            == Decimal("5080.00")
        )

        assert (
            balance_sheet.amount_for(
                positions[
                    "HGB.266.PASSIVA.C.4"
                ]
            )
            == Decimal("1190.00")
        )

        assert (
            balance_sheet.amount_for(
                positions[
                    "HGB.266.PASSIVA.C.8"
                ]
            )
            == Decimal("3040.00")
        )

        assert (
            balance_sheet.amount_for(
                accounting.assets
            )
            == Decimal("21810.00")
        )

        assert (
            balance_sheet.amount_for(
                accounting.liabilities
            )
            == Decimal("21810.00")
        )

        assert balance_sheet.is_balanced()
        
def _walk_positions(position):
    """Liefert eine Abschlussposition einschließlich aller Kinder."""

    yield position

    for child in position.children:
        yield from _walk_positions(child)
        

@pytest.mark.integration
def test_reference_scenario_builds_valid_e_bilanz(
    tmp_path: Path,
) -> None:
    """Der persistente Referenzabschluss erzeugt eine valide E-Bilanz."""

    version_root = TAXONOMY_ROOT / "6.10"

    if not version_root.is_dir():
        pytest.skip(
            "Taxonomy 6.10 is not installed locally"
        )

    with _create_session() as session:
        accounting = _build_reference_accounting(
            session
        )

        # ---------------------------------------------------------
        # Jahresabschluss durchführen
        # ---------------------------------------------------------

        closing_service = ClosingService(
            closing_accounts=ClosingAccounts(
                income_summary_account="8990",
                profit_account="8020",
                loss_account="8021",
            )
        )

        workflow = FiscalYearClosingWorkflow(
            session=session,
            booking_repository=accounting.booking_repository,
            company_repository=accounting.company_repository,
            closing_service=closing_service,
        )

        closing_result = workflow.close(
            company_id=REFERENCE_COMPANY_ID,
            fiscal_year=accounting.scenario.fiscal_year,
            income_statement=accounting.income_statement,
            ledger=accounting.ledger,
            chart_of_accounts=accounting.chart_of_accounts,
            closing_date=accounting.scenario.fiscal_year.end_date,
        )

        assert (
            closing_result.net_income
            == Decimal("5080.00")
        )

        # ---------------------------------------------------------
        # Abgeschlossenes Ledger rekonstruieren
        # ---------------------------------------------------------

        all_bookings = (
            accounting.booking_repository.list_for_fiscal_year(
                company_id=REFERENCE_COMPANY_ID,
                fiscal_year=accounting.scenario.fiscal_year,
            )
        )

        assert len(all_bookings) == 33

        closed_ledger = Ledger()

        for booking in all_bookings:
            accounting.posting_service.post_booking(
                booking=booking,
                ledger=closed_ledger,
            )

        # ---------------------------------------------------------
        # HGB-Bilanz nach Jahresabschluss erzeugen
        # ---------------------------------------------------------

        balance_sheet_balances = tuple(
            balance
            for balance in closed_ledger.balances()
            if (
                accounting.account_types.get(
                    balance.account_number
                )
                in (
                    AccountType.ASSET,
                    AccountType.LIABILITY,
                    AccountType.EQUITY,
                )
                and (
                    balance.debit_balance
                    > Decimal("0.00")
                    or balance.credit_balance
                    > Decimal("0.00")
                )
                and balance.account_number != "8990"
            )
        )

        balance_sheet_amounts = (
            accounting.statement_builder.build(
                balances=balance_sheet_balances,
                root_positions=(
                    accounting.assets,
                    accounting.liabilities,
                ),
            )
        )

        # ---------------------------------------------------------
        # HGB-Abschlusswerte für die E-Bilanz zusammenführen
        #
        # Bilanz: nach Abschluss
        # GuV:    vor Abschluss
        # ---------------------------------------------------------

        e_bilanz_amounts = {
            **accounting.income_statement_amounts,
            **balance_sheet_amounts,
        }

        positions = {
            position.code: position
            for root in (
                accounting.assets,
                accounting.liabilities,
                accounting.income_statement_root,
            )
            for position in _walk_positions(root)
        }

        assert (
            e_bilanz_amounts[
                positions["HGB.266.PASSIVA.A.V"]
            ]
            == Decimal("5080.00")
        )


        assert (
            e_bilanz_amounts[
                positions["HGB.275.GKV.1"]
            ]
            == Decimal("16000.00")
        )

        assert (
            e_bilanz_amounts[
                positions["HGB.275.GKV.4"]
            ]
            == Decimal("500.00")
        )

        # ---------------------------------------------------------
        # GCD-Daten des Referenzunternehmens
        # ---------------------------------------------------------

        company_data = GcdCompanyData(
            company=accounting.scenario.company,
            tax_number="1234567890123",
            legal_form="UG (haftungsbeschränkt)",
            street="Musterstraße",
            house_number="12a",
            postal_code="12345",
            city="Musterstadt",
            country="DE",
            business="Softwareentwicklung",
        )

        identifiers = GcdCompanyIdentifiers(
            tax_number_13="1234567890123",
            tax_id="12345678901",
            tax_economic_id="DE123456789",
            bf4="1234",
        )

        # ---------------------------------------------------------
        # Taxonomie 6.10 laden
        # ---------------------------------------------------------

        resolver = TaxonomyResolver(
            root=TAXONOMY_ROOT
        )

        gcd_entry_point_path = resolver.gcd_entry_point(
            TaxonomyVersion.V6_10
        )

        gaap_entry_point_path = (
            resolver.gaap_ci_fiscal_entry_point(
                TaxonomyVersion.V6_10
            )
        )

        gcd_base_entry_point = (
            TaxonomyEntryPoint.from_file(
                gcd_entry_point_path
            )
        )

        gaap_base_entry_point = (
            TaxonomyEntryPoint.from_file(
                gaap_entry_point_path
            )
        )

        gcd_entry_point = TaxonomyEntryPoint(
            path=gcd_base_entry_point.path,
            namespace=gcd_base_entry_point.namespace,
            schema_imports=(
                gcd_base_entry_point.schema_imports
            ),
            linkbase_references=(
                gcd_base_entry_point.linkbase_references
            ),
            schema_ref=gcd_entry_point_path.as_uri(),
        )

        gaap_entry_point = TaxonomyEntryPoint(
            path=gaap_base_entry_point.path,
            namespace=gaap_base_entry_point.namespace,
            schema_imports=(
                gaap_base_entry_point.schema_imports
            ),
            linkbase_references=(
                gaap_base_entry_point.linkbase_references
            ),
            schema_ref=gaap_entry_point_path.as_uri(),
        )

        # ---------------------------------------------------------
        # Vollständige E-Bilanz erzeugen
        # ---------------------------------------------------------

        adapter = ArelleAdapter()

        try:
            gcd_model = adapter.model(
                gcd_entry_point_path
            )

            gaap_model = adapter.model(
                gaap_entry_point_path
            )

            builder = EBilanzBuilder(
                gcd_model=gcd_model,
                gaap_ci_model=gaap_model,
                gcd_entry_point=gcd_entry_point,
                gaap_ci_entry_point=gaap_entry_point,
                gcd_namespace=GCD_NAMESPACE_6_10,
                gaap_ci_namespace=GAAP_CI_NAMESPACE_6_10,
                assets=accounting.assets,
                liabilities=accounting.liabilities,
                income_statement=(
                    accounting.income_statement_root
                ),
            )

            document = builder.build(
                company_data=company_data,
                fiscal_year=accounting.scenario.fiscal_year,
                amounts=e_bilanz_amounts,
                entity_identifier="DE123456789",
                entity_scheme=TEST_ENTITY_SCHEME,
                identifiers=identifiers,
            )

            xml = document.xml

            # -----------------------------------------------------
            # Grundstruktur GCD + GAAP-CI
            # -----------------------------------------------------

            assert "de-gcd" in xml
            assert "de-gaap-ci" in xml

            assert (
                "genInfo.report.id."
                "reportElement.reportElements.B"
                in xml
            )

            assert (
                "genInfo.report.id."
                "reportElement.reportElements.GuV"
                in xml
            )

            # -----------------------------------------------------
            # Bilanz-Facts aus dem echten Referenzabschluss
            # -----------------------------------------------------

            assert (
                "bs.ass.fixAss.tan.otherEquipm"
                in xml
            )

            assert (
                "bs.ass.currAss.cashEquiv"
                in xml
            )

            assert (
                "bs.eqLiab.equity.subscribed"
                in xml
            )

            assert (
                "bs.eqLiab.equity.netIncome"
                in xml
            )

            assert (
                "bs.eqLiab.liab.trade"
                in xml
            )

            # -----------------------------------------------------
            # GuV-Facts aus den echten Geschäftsvorfällen
            # -----------------------------------------------------

            assert (
                "is.netIncome.regular.operatingTC."
                "grossTradingProfit.totalOutput.netSales"
                in xml
            )

            assert (
                "is.netIncome.regular.operatingTC."
                "grossTradingProfit.materialServices.services"
                in xml
            )

            assert (
                "is.netIncome.regular.operatingTC."
                "deprAmort.fixAss"
                in xml
            )

            assert (
                "is.netIncome.regular.operatingTC.otherCost"
                in xml
            )

            # -----------------------------------------------------
            # Werte müssen tatsächlich im erzeugten Dokument stehen
            # -----------------------------------------------------

            assert ">5080.00<" in xml
            assert ">16000.00<" in xml
            assert ">500.00<" in xml
            assert ">13905.00<" in xml
            assert ">12500.00<" in xml

            # -----------------------------------------------------
            # XBRL-Datei schreiben und mit Arelle validieren
            # -----------------------------------------------------

            instance_path = (
                tmp_path
                / "openbilanz-reference-scenario-610.xbrl"
            )

            instance_path.write_text(
                xml,
                encoding="utf-8",
            )

            result = adapter.validate(
                instance_path
            )

        finally:
            adapter.close()

    assert result.is_valid
    assert result.errors == ()


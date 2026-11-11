"""Erzeugt einen Testmandanten für die manuelle USt-Verrechnung.

Das Skript arbeitet ausschließlich in einer ausdrücklich angegebenen,
bereits vorhandenen lokalen SQLite-Testdatenbank. Es legt keine Tabellen an,
löscht keine Daten und bucht keine USt-Verrechnung.
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from sqlalchemy import inspect
from sqlalchemy.engine import URL, make_url

from simpleob.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from simpleob.core.config import default_config
from simpleob.database.booking_repository import BookingRepository
from simpleob.database.business_partner_repository import (
    BusinessPartnerRepository,
)
from simpleob.database.chart_of_accounts_repository import (
    ChartOfAccountsRepository,
)
from simpleob.database.company_repository import CompanyRepository
from simpleob.database.database import Database
from simpleob.database.open_item_payment_repository import (
    OpenItemPaymentRepository,
)
from simpleob.database.payable_invoice_repository import (
    PayableInvoiceRepository,
)
from simpleob.database.receivable_invoice_repository import (
    ReceivableInvoiceRepository,
)
from simpleob.domain.account import Account
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.business_partner import BusinessPartner
from simpleob.domain.company import Company
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.open_item_payment import PaymentDirection
from simpleob.domain.opening_balance import OpeningBalance
from simpleob.domain.opening_balance_item import OpeningBalanceItem
from simpleob.domain.vat_booking_item import VatBookingItem
from simpleob.hgb.balance_sheet_structure import create_hgb_balance_sheet_structure
from simpleob.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from simpleob.importers.chart_of_accounts_template_bundle_importer import (
    ChartOfAccountsTemplateBundleImporter,
)
from simpleob.importers.csv_chart_of_accounts_importer import (
    CsvChartOfAccountsImporter,
)
from simpleob.services.chart_of_accounts_initialization_service import (
    ChartOfAccountsInitializationService,
)
from simpleob.services.open_item_payment_service import OpenItemPaymentService
from simpleob.services.opening_balance_service import OpeningBalanceService
from simpleob.services.payable_invoice_posting_service import (
    PayableInvoicePostingService,
)
from simpleob.services.receivable_invoice_posting_service import (
    ReceivableInvoicePostingService,
)

COMPANY_NAME = "USt-Jahresabschluss-Test UG"
FISCAL_YEAR = FiscalYear(date(2026, 1, 1), date(2026, 12, 31))
FOLLOWING_FISCAL_YEAR = FiscalYear(date(2027, 1, 1), date(2027, 12, 31))
STANDARD_CHART = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "simpleob"
    / "resources"
    / "chart_of_accounts"
    / "openbilanz_standard.csv"
)


def _selected_database_url(value: str) -> tuple[URL, Path]:
    """Akzeptiert nur eine explizite, vorhandene lokale SQLite-Testdatei."""

    try:
        url = make_url(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Die Datenbank-URL ist ungültig.") from exc

    if url.drivername != "sqlite" or url.database in (None, "", ":memory:"):
        raise ValueError(
            "Nur eine lokale SQLite-Datei darf verwendet werden; "
            "PostgreSQL-, Netzwerk- und In-Memory-Datenbanken sind gesperrt."
        )
    if url.username or url.password or url.host or url.query:
        raise ValueError("Die Datenbank-URL darf keine Netzwerkparameter enthalten.")

    raw_path = Path(url.database).expanduser()
    if not raw_path.is_absolute():
        raise ValueError("Der Pfad zur Testdatenbank muss absolut sein.")
    database_path = raw_path.resolve()
    if "test" not in database_path.name.casefold():
        raise ValueError("Der Datenbankdateiname muss zur Sicherheit 'test' enthalten.")
    if not database_path.is_file() or database_path.stat().st_size == 0:
        raise ValueError(
            "Die ausgewählte SQLite-Testdatenbank muss bereits existieren "
            "und ein vorhandenes Schema enthalten."
        )
    return url, database_path


def _template_bundle():
    roots = (
        *create_hgb_balance_sheet_structure(),
        create_hgb_income_statement_structure(),
    )
    provider = HgbFinancialStatementPositionProvider(roots)
    importer = ChartOfAccountsTemplateBundleImporter(
        chart_importer=CsvChartOfAccountsImporter(position_provider=provider)
    )
    bundle = importer.load(STANDARD_CHART)
    importer.validate(bundle)

    required_accounts = {
        "3820",
        "3840",
        "1422",
        "3841",
        "1200",
        "1400",
        "1600",
        "1571",
        "1576",
        "1771",
        "1776",
        "4930",
        "8400",
        "8407",
        "0800",
        "0855",
        "9000",
    }
    missing = sorted(
        number for number in required_accounts if not bundle.chart.contains(number)
    )
    if missing:
        raise ValueError(
            "Der SimpleOB-Standardkontenrahmen enthält nicht alle benötigten "
            f"Konten: {', '.join(missing)}"
        )
    roles = bundle.account_roles
    if roles is None or not all(
        (
            roles.bank_accounts,
            roles.customer_receivables,
            roles.supplier_payables,
            roles.vat_advance_payments,
            roles.vat_current_year,
            roles.vat_prior_year_receivables,
            roles.vat_prior_year_payables,
        )
    ):
        raise ValueError("Die Standardkontenvorlage hat unvollständige Kontenrollen.")
    if bundle.vat_accounts is None or bundle.control_accounts is None:
        raise ValueError(
            "Die Standardkontenvorlage ist nicht vollständig konfiguriert."
        )
    return bundle


def _opening_bookings(bundle) -> tuple[Booking, ...]:
    opening_balance = OpeningBalance(
        items=(
            OpeningBalanceItem(Account(bundle.chart.get("1200")), Decimal("100000.00")),
            OpeningBalanceItem(Account(bundle.chart.get("0800")), Decimal("25000.00")),
            OpeningBalanceItem(Account(bundle.chart.get("0855")), Decimal("75000.00")),
        )
    )
    if not opening_balance.is_balanced:
        raise ValueError("Die Test-Eröffnungsbilanz ist nicht ausgeglichen.")
    return OpeningBalanceService(
        opening_balance_account_number=(bundle.control_accounts.opening_balance_account)
    ).create_bookings(
        opening_balance=opening_balance,
        booking_date=FISCAL_YEAR.start_date,
    )


def _post_vat_advance_payments(
    *,
    company_id,
    booking_repository: BookingRepository,
    account_roles,
) -> None:
    advance_account = _single_role_account(
        account_roles.vat_advance_payments, "USt-Vorauszahlungen"
    )
    bank_account = _single_role_account(account_roles.bank_accounts, "Bank")
    for index, booking_date in enumerate(
        (date(2026, 4, 10), date(2026, 7, 10), date(2026, 10, 10), date(2026, 12, 10)),
        start=1,
    ):
        booking_repository.add(
            company_id=company_id,
            fiscal_year=FISCAL_YEAR,
            booking=Booking(
                booking_date=booking_date,
                voucher_no=f"UVA-2026-{index:02d}",
                description=f"USt-Vorauszahlung 2026, Rate {index}",
                lines=(
                    BookingLine(advance_account, EntrySide.DEBIT, Decimal("1250.00")),
                    BookingLine(bank_account, EntrySide.CREDIT, Decimal("1250.00")),
                ),
            ),
        )


def _post_invoices_and_payments(
    *,
    company,
    session,
    partner_repository: BusinessPartnerRepository,
    booking_repository: BookingRepository,
    chart_repository: ChartOfAccountsRepository,
    bundle,
) -> None:
    customer = BusinessPartner(company.company_id, "Nordlicht Handel GmbH")
    supplier = BusinessPartner(
        company.company_id,
        "Kontorbedarf Berlin GmbH",
        is_customer=False,
        is_supplier=True,
    )
    partner_repository.add(customer)
    partner_repository.add(supplier)

    receivable_service = ReceivableInvoicePostingService(
        booking_repository=booking_repository,
        partner_repository=partner_repository,
        invoice_repository=ReceivableInvoiceRepository(session),
        chart_of_accounts_repository=chart_repository,
    )
    payable_service = PayableInvoicePostingService(
        booking_repository=booking_repository,
        partner_repository=partner_repository,
        invoice_repository=PayableInvoiceRepository(session),
        chart_of_accounts_repository=chart_repository,
    )
    payment_service = OpenItemPaymentService(
        booking_repository=booking_repository,
        payment_repository=OpenItemPaymentRepository(session),
        chart_of_accounts_repository=chart_repository,
    )
    vat_accounts = bundle.vat_accounts
    bank_account = _single_role_account(bundle.account_roles.bank_accounts, "Bank")

    sales = (
        (19, "8400", Decimal("11900.00"), date(2026, 1, 15)),
        (19, "8400", Decimal("11900.00"), date(2026, 3, 15)),
        (19, "8400", Decimal("11900.00"), date(2026, 5, 15)),
        (19, "8400", Decimal("11900.00"), date(2026, 7, 15)),
        (19, "8400", Decimal("11900.00"), date(2026, 9, 15)),
        (7, "8407", Decimal("3821.43"), date(2026, 4, 15)),
        (7, "8407", Decimal("3821.43"), date(2026, 10, 15)),
    )
    purchases = (
        (19, Decimal("5950.00"), date(2026, 2, 5)),
        (19, Decimal("5950.00"), date(2026, 4, 5)),
        (19, Decimal("5950.00"), date(2026, 6, 5)),
        (19, Decimal("5950.00"), date(2026, 8, 5)),
        (7, Decimal("1528.57"), date(2026, 3, 5)),
        (7, Decimal("1528.57"), date(2026, 9, 5)),
    )

    for index, (rate, sales_account, gross, invoice_date) in enumerate(sales, start=1):
        invoice_number = f"AR-2026-{rate:02d}-{index:02d}"
        open_item_id = uuid4()
        receivable_service.post_output_invoice_on_account(
            company_id=company.company_id,
            fiscal_year=FISCAL_YEAR,
            partner_id=customer.partner_id,
            invoice_number=invoice_number,
            booking_date=invoice_date,
            due_date=invoice_date + timedelta(days=30),
            items=(VatBookingItem(sales_account, gross, rate),),
            vat_accounts=vat_accounts,
            description=f"Dienstleistung und Warenlieferung {invoice_date:%m/%Y}",
            open_item_id=open_item_id,
        )
        payment_service.post_payment(
            company_id=company.company_id,
            fiscal_year=FISCAL_YEAR,
            partner_id=customer.partner_id,
            open_item_id=open_item_id,
            direction=PaymentDirection.CUSTOMER_RECEIPT,
            amount=gross,
            payment_date=invoice_date + timedelta(days=20),
            booking_date=invoice_date + timedelta(days=20),
            cash_bank_account_number=bank_account,
            voucher_no=f"EIN-2026-{index:02d}",
            description="Zahlungseingang",
        )

    for index, (rate, gross, invoice_date) in enumerate(purchases, start=1):
        invoice_number = f"ER-2026-{rate:02d}-{index:02d}"
        open_item_id = uuid4()
        payable_service.post_supplier_invoice_on_account(
            company_id=company.company_id,
            fiscal_year=FISCAL_YEAR,
            partner_id=supplier.partner_id,
            invoice_number=invoice_number,
            booking_date=invoice_date,
            due_date=invoice_date + timedelta(days=30),
            items=(VatBookingItem("4930", gross, rate),),
            vat_accounts=vat_accounts,
            description=f"Büro- und Betriebsmaterial {invoice_date:%m/%Y}",
            open_item_id=open_item_id,
        )
        payment_service.post_payment(
            company_id=company.company_id,
            fiscal_year=FISCAL_YEAR,
            partner_id=supplier.partner_id,
            open_item_id=open_item_id,
            direction=PaymentDirection.SUPPLIER_PAYMENT,
            amount=gross,
            payment_date=invoice_date + timedelta(days=20),
            booking_date=invoice_date + timedelta(days=20),
            cash_bank_account_number=bank_account,
            voucher_no=f"AUS-2026-{index:02d}",
            description="Überweisung Lieferant",
        )


def _single_role_account(accounts, label: str) -> str:
    if len(accounts) != 1:
        raise ValueError(f"Für {label} muss genau ein Konto konfiguriert sein.")
    return next(iter(accounts))


def _verify_vat_balances(
    *,
    booking_repository: BookingRepository,
    company_id,
    vat_accounts,
    account_roles,
) -> dict[str, Decimal]:
    balances: dict[str, Decimal] = {}
    for booking in booking_repository.list_for_fiscal_year(
        company_id=company_id,
        fiscal_year=FISCAL_YEAR,
    ):
        for line in booking.lines:
            amount = line.amount if line.side is EntrySide.DEBIT else -line.amount
            balances[line.account_number] = (
                balances.get(line.account_number, Decimal("0.00")) + amount
            )
    expected = {
        vat_accounts.output_tax_19: Decimal("-9500.00"),
        vat_accounts.output_tax_7: Decimal("-500.00"),
        vat_accounts.input_tax_19: Decimal("3800.00"),
        vat_accounts.input_tax_7: Decimal("200.00"),
        _single_role_account(
            account_roles.vat_advance_payments, "USt-Vorauszahlungen"
        ): Decimal("5000.00"),
        _single_role_account(
            account_roles.vat_current_year, "USt-Verrechnung"
        ): Decimal("0.00"),
    }
    mismatches = {
        account: (balances.get(account, Decimal("0.00")), amount)
        for account, amount in expected.items()
        if balances.get(account, Decimal("0.00")) != amount
    }
    if mismatches:
        detail = ", ".join(
            f"{account}: Ist {actual:.2f}, Soll {target:.2f}"
            for account, (actual, target) in sorted(mismatches.items())
        )
        raise RuntimeError(f"USt-Saldenprüfung fehlgeschlagen: {detail}")
    return balances


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Legt den USt-Jahresabschluss-Testmandanten in einer explizit "
            "ausgewählten lokalen SQLite-Testdatenbank an."
        )
    )
    parser.add_argument(
        "--database-url",
        required=True,
        help="Absolute URL zu einer vorhandenen lokalen SQLite-Testdatei.",
    )
    args = parser.parse_args()

    try:
        database_url, database_path = _selected_database_url(args.database_url)
        bundle = _template_bundle()
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.error(str(exc))

    config = default_config()
    config = config.__class__(
        data_dir=config.data_dir,
        database_file=database_path,
        taxonomy_dir=config.taxonomy_dir,
        config_file=config.config_file,
        eric_lib_dir=config.eric_lib_dir,
        eric_data_supplier=config.eric_data_supplier,
        eric_certificate_path=config.eric_certificate_path,
        database_url_override=database_url.render_as_string(hide_password=True),
    )
    database = Database(config)
    try:
        required_tables = {
            "mandanten",
            "wirtschaftsjahre",
            "konten",
            "kontenrahmen_konfiguration",
            "kontenrollen",
            "konten_taxonomie_zuordnungen",
            "buchungen",
            "buchungszeilen",
            "geschaeftspartner",
            "ausgangsrechnungen",
            "forderungs_ops",
            "eingangsrechnungen",
            "verbindlichkeits_ops",
            "zahlungen",
            "rechnungs_op_zahlungsereignisse",
        }
        existing_tables = set(inspect(database.engine).get_table_names())
        if not required_tables.issubset(existing_tables):
            raise RuntimeError(
                "Die ausgewählte Datenbank enthält kein vollständiges "
                "SimpleOB-Schema. Das Skript erzeugt oder migriert kein Schema."
            )

        with database.create_session() as session:
            company_repository = CompanyRepository(session)
            if any(
                existing.name.casefold() == COMPANY_NAME.casefold()
                for existing in company_repository.list_companies()
            ):
                raise RuntimeError(
                    f"Der Mandant {COMPANY_NAME!r} existiert bereits; "
                    "es wurden keine Daten geändert."
                )

            chart_repository = ChartOfAccountsRepository(session)
            company = Company(uuid4(), COMPANY_NAME)
            company_repository.add(company, commit=False)
            company_repository.add_fiscal_year(
                company.company_id,
                FISCAL_YEAR,
                commit=False,
            )
            company_repository.add_fiscal_year(
                company.company_id,
                FOLLOWING_FISCAL_YEAR,
                commit=False,
            )
            ChartOfAccountsInitializationService(
                repository=chart_repository,
                position_provider=HgbFinancialStatementPositionProvider(
                    (
                        *create_hgb_balance_sheet_structure(),
                        create_hgb_income_statement_structure(),
                    )
                ),
            ).initialize(
                company=company,
                standard_chart_of_accounts=bundle.chart,
                standard_account_taxonomy_concepts=bundle.taxonomy_mappings or {},
                control_accounts=bundle.control_accounts,
                vat_accounts=bundle.vat_accounts,
                account_roles=bundle.account_roles,
                taxonomy_version=bundle.taxonomy_version or "6.9",
            )

            booking_repository = BookingRepository(session)
            for opening_booking in _opening_bookings(bundle):
                booking_repository.add(
                    company_id=company.company_id,
                    fiscal_year=FISCAL_YEAR,
                    booking=opening_booking,
                    commit=False,
                )
            booking_repository.commit()

            _post_invoices_and_payments(
                company=company,
                session=session,
                partner_repository=BusinessPartnerRepository(session),
                booking_repository=booking_repository,
                chart_repository=chart_repository,
                bundle=bundle,
            )
            _post_vat_advance_payments(
                company_id=company.company_id,
                booking_repository=booking_repository,
                account_roles=bundle.account_roles,
            )
            balances = _verify_vat_balances(
                booking_repository=booking_repository,
                company_id=company.company_id,
                vat_accounts=bundle.vat_accounts,
                account_roles=bundle.account_roles,
            )
            output_due = -(
                balances[bundle.vat_accounts.output_tax_19]
                + balances[bundle.vat_accounts.output_tax_7]
            )
            net_payable = (
                output_due
                - balances[bundle.vat_accounts.input_tax_19]
                - balances[bundle.vat_accounts.input_tax_7]
                - balances[
                    _single_role_account(
                        bundle.account_roles.vat_advance_payments,
                        "USt-Vorauszahlungen",
                    )
                ]
            )
            if net_payable != Decimal("1000.00"):
                raise RuntimeError(
                    "Das vorbereitete Szenario ergibt nicht die erwartete "
                    f"USt-Nachzahlung von 1.000,00 EUR (Ist: {net_payable:.2f} EUR)."
                )

            print(f"Testmandant angelegt: {COMPANY_NAME}")
            print(f"Datenbank: {database_path}")
            print(f"Geschäftsjahr: {FISCAL_YEAR.display_name}")
            print("USt-Kontensalden vor Verrechnung (Soll positiv):")
            roles = bundle.account_roles
            vat_numbers = (
                bundle.vat_accounts.output_tax_19,
                bundle.vat_accounts.output_tax_7,
                bundle.vat_accounts.input_tax_19,
                bundle.vat_accounts.input_tax_7,
                _single_role_account(roles.vat_advance_payments, "USt-Vorauszahlungen"),
                _single_role_account(roles.vat_current_year, "USt-Verrechnung"),
            )
            for number in vat_numbers:
                print(f"  {number}: {balances.get(number, Decimal('0.00')):.2f} EUR")
            print(f"Erwartete USt-Nachzahlung: {net_payable:.2f} EUR.")
            print(
                "Keine USt-Verrechnung, kein Jahresabschluss und keine Übernahme gebucht."
            )
    finally:
        database.dispose()


if __name__ == "__main__":
    main()

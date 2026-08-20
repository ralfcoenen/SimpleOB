"""Reproduzierbarer Datenbestand für manuelle GUI-Tests."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from openbilanz.database.booking_repository import BookingRepository
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.database.database import create_session
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.company import Company
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.fiscal_year import FiscalYear

GUI_TEST_COMPANY_ID = UUID(
    "00000000-0000-0000-0000-000000000041"
)

GUI_TEST_FISCAL_YEAR = FiscalYear(
    start_date=date(2028, 1, 1),
    end_date=date(2028, 12, 31),
)

EXPECTED_NET_INCOME = Decimal("550.00")

EXPECTED_PRE_CLOSING_BALANCES = {
    "0400": ("DEBIT", Decimal("1600.00")),
    "0800": ("CREDIT", Decimal("12500.00")),
    "1200": ("DEBIT", Decimal("12687.00")),
    "1400": ("DEBIT", Decimal("2260.00")),
    "1571": ("DEBIT", Decimal("70.00")),
    "1576": ("DEBIT", Decimal("646.00")),
    "1600": ("CREDIT", Decimal("3510.00")),
    "1771": ("CREDIT", Decimal("133.00")),
    "1776": ("CREDIT", Decimal("570.00")),
    "3100": ("DEBIT", Decimal("1000.00")),
    "4210": ("DEBIT", Decimal("1200.00")),
    "4660": ("DEBIT", Decimal("300.00")),
    "4800": ("CREDIT", Decimal("100.00")),
    "4830": ("DEBIT", Decimal("400.00")),
    "4930": ("DEBIT", Decimal("1500.00")),
    "4970": ("DEBIT", Decimal("50.00")),
    "8400": ("CREDIT", Decimal("5000.00")),
    "8500": ("DEBIT", Decimal("100.00")),
}


@dataclass(frozen=True, slots=True)
class GuiTestScenario:
    """Vollständiger Datenbestand für manuelle GUI-Tests."""

    company: Company
    fiscal_year: FiscalYear
    bookings: tuple[Booking, ...]


def _booking(
    *,
    booking_id: str,
    booking_date: date,
    voucher_no: str,
    description: str,
    lines: tuple[BookingLine, ...],
) -> Booking:
    """Erzeugt eine deterministische Testbuchung."""

    return Booking(
        booking_id=UUID(booking_id),
        booking_date=booking_date,
        voucher_no=voucher_no,
        description=description,
        lines=lines,
    )


def _debit(
    account_number: str,
    amount: str,
) -> BookingLine:
    """Erzeugt eine Sollbuchungszeile."""

    return BookingLine(
        account_number=account_number,
        side=EntrySide.DEBIT,
        amount=Decimal(amount),
    )


def _credit(
    account_number: str,
    amount: str,
) -> BookingLine:
    """Erzeugt eine Habenbuchungszeile."""

    return BookingLine(
        account_number=account_number,
        side=EntrySide.CREDIT,
        amount=Decimal(amount),
    )


def create_gui_test_scenario() -> GuiTestScenario:
    """Erzeugt den vollständigen GUI-Testbestand."""

    company = Company(
        company_id=GUI_TEST_COMPANY_ID,
        name="OpenBilanz GUI-Test UG",
    )

    bookings = (
        # 1. Einzahlung des Stammkapitals
        _booking(
            booking_id="00000000-0000-0000-0002-000000000001",
            booking_date=date(2028, 1, 2),
            voucher_no="KB-001",
            description="Einzahlung Stammkapital",
            lines=(
                _debit("1200", "12500.00"),
                _credit("0800", "12500.00"),
            ),
        ),

        # 2. Ausgangsrechnung 19 %
        _booking(
            booking_id="00000000-0000-0000-0002-000000000002",
            booking_date=date(2028, 2, 1),
            voucher_no="AR-001",
            description="Ausgangsrechnung 19 %",
            lines=(
                _debit("1400", "2380.00"),
                _credit("8400", "2000.00"),
                _credit("1776", "380.00"),
            ),
        ),

        # 3. Ausgangsrechnung 7 %
        _booking(
            booking_id="00000000-0000-0000-0002-000000000003",
            booking_date=date(2028, 2, 10),
            voucher_no="AR-002",
            description="Ausgangsrechnung 7 %",
            lines=(
                _debit("1400", "1070.00"),
                _credit("8400", "1000.00"),
                _credit("1771", "70.00"),
            ),
        ),

        # 4. Kundengutschrift 7 %
        #
        # 8500 erhält bewusst einen Sollsaldo.
        # Damit wird beim Jahresabschluss ein Erlöskonto
        # mit Gegensaldo getestet.
        _booking(
            booking_id="00000000-0000-0000-0002-000000000004",
            booking_date=date(2028, 2, 15),
            voucher_no="KG-001",
            description="Kundengutschrift 7 %",
            lines=(
                _debit("8500", "100.00"),
                _debit("1771", "7.00"),
                _credit("1400", "107.00"),
            ),
        ),

        # 5. Eingangsrechnung 19 %
        _booking(
            booking_id="00000000-0000-0000-0002-000000000005",
            booking_date=date(2028, 3, 1),
            voucher_no="ER-001",
            description="Bürobedarf 19 %",
            lines=(
                _debit("4930", "1000.00"),
                _debit("1576", "190.00"),
                _credit("1600", "1190.00"),
            ),
        ),

        # 6. Eingangsrechnung 7 %
        _booking(
            booking_id="00000000-0000-0000-0002-000000000006",
            booking_date=date(2028, 3, 10),
            voucher_no="ER-002",
            description="Fremdleistung 7 %",
            lines=(
                _debit("3100", "500.00"),
                _debit("1571", "35.00"),
                _credit("1600", "535.00"),
            ),
        ),

        # 7. Lieferantengutschrift 19 %
        #
        # 4800 erhält bewusst einen Habensaldo.
        # Damit wird beim Jahresabschluss ein Aufwandskonto
        # mit Gegensaldo getestet.
        _booking(
            booking_id="00000000-0000-0000-0002-000000000007",
            booking_date=date(2028, 3, 15),
            voucher_no="LG-001",
            description="Lieferantengutschrift 19 %",
            lines=(
                _debit("1600", "119.00"),
                _credit("4800", "100.00"),
                _credit("1576", "19.00"),
            ),
        ),

        # 8. Büromiete ohne USt-Aufteilung
        _booking(
            booking_id="00000000-0000-0000-0002-000000000008",
            booking_date=date(2028, 4, 1),
            voucher_no="BA-001",
            description="Büromiete",
            lines=(
                _debit("4210", "1200.00"),
                _credit("1200", "1200.00"),
            ),
        ),

        # 9. Bankgebühren
        _booking(
            booking_id="00000000-0000-0000-0002-000000000009",
            booking_date=date(2028, 4, 5),
            voucher_no="BA-002",
            description="Bankgebühren",
            lines=(
                _debit("4970", "50.00"),
                _credit("1200", "50.00"),
            ),
        ),

        # 10. Zahlung der ersten Kundenrechnungen
        _booking(
            booking_id="00000000-0000-0000-0002-000000000010",
            booking_date=date(2028, 4, 15),
            voucher_no="ZE-001",
            description="Zahlung Kundenforderungen",
            lines=(
                _debit("1200", "3343.00"),
                _credit("1400", "3343.00"),
            ),
        ),

        # 11. Zahlung der ersten Lieferantenrechnungen
        _booking(
            booking_id="00000000-0000-0000-0002-000000000011",
            booking_date=date(2028, 4, 20),
            voucher_no="BA-003",
            description="Zahlung Lieferantenverbindlichkeiten",
            lines=(
                _debit("1600", "1606.00"),
                _credit("1200", "1606.00"),
            ),
        ),

        # 12. Anlagevermögen auf Rechnung
        _booking(
            booking_id="00000000-0000-0000-0002-000000000012",
            booking_date=date(2028, 5, 1),
            voucher_no="ER-003",
            description="Anschaffung Betriebs- und Geschäftsausstattung",
            lines=(
                _debit("0400", "2000.00"),
                _debit("1576", "380.00"),
                _credit("1600", "2380.00"),
            ),
        ),

        # 13. Abschreibung
        _booking(
            booking_id="00000000-0000-0000-0002-000000000013",
            booking_date=date(2028, 12, 1),
            voucher_no="AB-001",
            description="Abschreibung Betriebs- und Geschäftsausstattung",
            lines=(
                _debit("4830", "400.00"),
                _credit("0400", "400.00"),
            ),
        ),

        # 14. Reisekosten
        _booking(
            booking_id="00000000-0000-0000-0002-000000000014",
            booking_date=date(2028, 6, 1),
            voucher_no="BA-004",
            description="Reisekosten",
            lines=(
                _debit("4660", "300.00"),
                _credit("1200", "300.00"),
            ),
        ),

        # 15. Gemischte Ausgangsrechnung 19 % und 7 %
        _booking(
            booking_id="00000000-0000-0000-0002-000000000015",
            booking_date=date(2028, 7, 1),
            voucher_no="AR-003",
            description="Gemischte Ausgangsrechnung",
            lines=(
                _debit("1400", "2260.00"),
                _credit("8400", "2000.00"),
                _credit("1776", "190.00"),
                _credit("1771", "70.00"),
            ),
        ),

        # 16. Gemischte Eingangsrechnung 19 % und 7 %
        _booking(
            booking_id="00000000-0000-0000-0002-000000000016",
            booking_date=date(2028, 8, 1),
            voucher_no="ER-004",
            description="Gemischte Eingangsrechnung",
            lines=(
                _debit("4930", "500.00"),
                _debit("1576", "95.00"),
                _debit("3100", "500.00"),
                _debit("1571", "35.00"),
                _credit("1600", "1130.00"),
            ),
        ),
    )

    return GuiTestScenario(
        company=company,
        fiscal_year=GUI_TEST_FISCAL_YEAR,
        bookings=bookings,
    )


def persist_gui_test_scenario(
    *,
    scenario: GuiTestScenario,
    company_repository: CompanyRepository,
    booking_repository: BookingRepository,
) -> None:
    """Persistiert den GUI-Testmandanten."""

    if not isinstance(
        scenario,
        GuiTestScenario,
    ):
        raise TypeError(
            "scenario muss ein GuiTestScenario sein."
        )

    company_repository.add(
        scenario.company
    )

    company_repository.add_fiscal_year(
        scenario.company.company_id,
        scenario.fiscal_year,
    )

    for booking in scenario.bookings:
        booking_repository.add(
            company_id=scenario.company.company_id,
            fiscal_year=scenario.fiscal_year,
            booking=booking,
        )


def main() -> None:
    """Legt den GUI-Testmandanten in der Standarddatenbank an."""

    session = create_session()

    try:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )

        existing = company_repository.get(
            GUI_TEST_COMPANY_ID
        )

        if existing is not None:
            raise ValueError(
                "Der GUI-Testmandant ist bereits vorhanden."
            )

        scenario = create_gui_test_scenario()

        persist_gui_test_scenario(
            scenario=scenario,
            company_repository=company_repository,
            booking_repository=booking_repository,
        )

        print(
            "GUI-Testmandant wurde angelegt:"
        )
        print(
            f"  {scenario.company.name}"
        )
        print(
            "  Geschäftsjahr: "
            f"{scenario.fiscal_year.start_date:%d.%m.%Y}"
            " – "
            f"{scenario.fiscal_year.end_date:%d.%m.%Y}"
        )
        print(
            f"  Buchungen: {len(scenario.bookings)}"
        )
        print(
            "  Erwarteter Jahresüberschuss: "
            f"{EXPECTED_NET_INCOME:.2f} EUR"
        )

    finally:
        session.close()


if __name__ == "__main__":
    main()

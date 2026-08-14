"""Persistentes Referenzszenario für OpenBilanz-UG."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from openbilanz.database.booking_repository import BookingRepository
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.company import Company
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.fiscal_year import FiscalYear

REFERENCE_COMPANY_ID = UUID(
    "00000000-0000-0000-0000-000000000031"
)

REFERENCE_FISCAL_YEAR = FiscalYear(
    start_date=date(2027, 1, 1),
    end_date=date(2027, 12, 31),
)


@dataclass(frozen=True, slots=True)
class ReferenceScenario:
    """Reproduzierbares Buchhaltungsszenario einer kleinen Muster-UG."""

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
    """Erzeugt eine deterministische Referenzbuchung."""

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


def create_reference_scenario() -> ReferenceScenario:
    """Erzeugt das vollständige OpenBilanz-Referenzszenario."""

    company = Company(
        company_id=REFERENCE_COMPANY_ID,
        name="OpenBilanz Muster UG (haftungsbeschränkt)",
    )

    bookings = (
        # 1. Einzahlung des Stammkapitals
        _booking(
            booking_id="00000000-0000-0000-0001-000000000001",
            booking_date=date(2027, 1, 2),
            voucher_no="KB-001",
            description="Einzahlung Stammkapital",
            lines=(
                _debit("1200", "12500.00"),
                _credit("0800", "12500.00"),
            ),
        ),

        # 2. Betriebs- und Geschäftsausstattung auf Rechnung
        _booking(
            booking_id="00000000-0000-0000-0001-000000000002",
            booking_date=date(2027, 1, 10),
            voucher_no="ER-001",
            description="Anschaffung Betriebs- und Geschäftsausstattung",
            lines=(
                _debit("0400", "4000.00"),
                _debit("1576", "760.00"),
                _credit("1600", "4760.00"),
            ),
        ),

        # 3. Bezahlung der BGA-Rechnung
        _booking(
            booking_id="00000000-0000-0000-0001-000000000003",
            booking_date=date(2027, 1, 20),
            voucher_no="BA-001",
            description="Bezahlung Betriebs- und Geschäftsausstattung",
            lines=(
                _debit("1600", "4760.00"),
                _credit("1200", "4760.00"),
            ),
        ),

        # 4. Erste Ausgangsrechnung
        _booking(
            booking_id="00000000-0000-0000-0001-000000000004",
            booking_date=date(2027, 2, 5),
            voucher_no="AR-001",
            description="Dienstleistungsrechnung Kunde A",
            lines=(
                _debit("1400", "11900.00"),
                _credit("8400", "10000.00"),
                _credit("1776", "1900.00"),
            ),
        ),

        # 5. Teilzahlung Kunde A
        _booking(
            booking_id="00000000-0000-0000-0001-000000000005",
            booking_date=date(2027, 2, 20),
            voucher_no="ZE-001",
            description="Teilzahlung Kunde A",
            lines=(
                _debit("1200", "9000.00"),
                _credit("1400", "9000.00"),
            ),
        ),

        # 6. Zweite Ausgangsrechnung
        _booking(
            booking_id="00000000-0000-0000-0001-000000000006",
            booking_date=date(2027, 3, 10),
            voucher_no="AR-002",
            description="Dienstleistungsrechnung Kunde B",
            lines=(
                _debit("1400", "7140.00"),
                _credit("8400", "6000.00"),
                _credit("1776", "1140.00"),
            ),
        ),

        # 7. Vollständige Zahlung Kunde B
        _booking(
            booking_id="00000000-0000-0000-0001-000000000007",
            booking_date=date(2027, 3, 25),
            voucher_no="ZE-002",
            description="Zahlung Kunde B",
            lines=(
                _debit("1200", "7140.00"),
                _credit("1400", "7140.00"),
            ),
        ),

        # 8. Fremdleistung auf Rechnung
        _booking(
            booking_id="00000000-0000-0000-0001-000000000008",
            booking_date=date(2027, 4, 5),
            voucher_no="ER-002",
            description="Externe Entwicklungsleistung",
            lines=(
                _debit("3100", "2000.00"),
                _debit("1576", "380.00"),
                _credit("1600", "2380.00"),
            ),
        ),

        # 9. Zahlung Fremdleistung
        _booking(
            booking_id="00000000-0000-0000-0001-000000000009",
            booking_date=date(2027, 4, 20),
            voucher_no="BA-002",
            description="Bezahlung externe Entwicklungsleistung",
            lines=(
                _debit("1600", "2380.00"),
                _credit("1200", "2380.00"),
            ),
        ),

        # 10. Jahresmiete
        _booking(
            booking_id="00000000-0000-0000-0001-000000000010",
            booking_date=date(2027, 5, 2),
            voucher_no="BA-003",
            description="Büromiete",
            lines=(
                _debit("4210", "3600.00"),
                _credit("1200", "3600.00"),
            ),
        ),

        # 11. Versicherung
        _booking(
            booking_id="00000000-0000-0000-0001-000000000011",
            booking_date=date(2027, 5, 15),
            voucher_no="BA-004",
            description="Betriebliche Versicherung",
            lines=(
                _debit("4360", "600.00"),
                _credit("1200", "600.00"),
            ),
        ),

        # 12. Telefon und Internet
        _booking(
            booking_id="00000000-0000-0000-0001-000000000012",
            booking_date=date(2027, 6, 5),
            voucher_no="ER-003",
            description="Telefon und Internet",
            lines=(
                _debit("4920", "600.00"),
                _debit("1576", "114.00"),
                _credit("1200", "714.00"),
            ),
        ),

        # 13. Bürobedarf
        _booking(
            booking_id="00000000-0000-0000-0001-000000000013",
            booking_date=date(2027, 6, 20),
            voucher_no="ER-004",
            description="Bürobedarf",
            lines=(
                _debit("4930", "400.00"),
                _debit("1576", "76.00"),
                _credit("1200", "476.00"),
            ),
        ),

        # 14. Fortbildung
        _booking(
            booking_id="00000000-0000-0000-0001-000000000014",
            booking_date=date(2027, 7, 10),
            voucher_no="BA-005",
            description="Fachliche Fortbildung",
            lines=(
                _debit("4945", "800.00"),
                _credit("1200", "800.00"),
            ),
        ),

        # 15. Bankgebühren
        _booking(
            booking_id="00000000-0000-0000-0001-000000000015",
            booking_date=date(2027, 8, 1),
            voucher_no="BA-006",
            description="Bankgebühren",
            lines=(
                _debit("4970", "120.00"),
                _credit("1200", "120.00"),
            ),
        ),

        # 16. Werbung
        _booking(
            booking_id="00000000-0000-0000-0001-000000000016",
            booking_date=date(2027, 9, 5),
            voucher_no="ER-005",
            description="Online-Werbung",
            lines=(
                _debit("4600", "1000.00"),
                _debit("1576", "190.00"),
                _credit("1200", "1190.00"),
            ),
        ),

        # 17. Reparatur und Instandhaltung
        _booking(
            booking_id="00000000-0000-0000-0001-000000000017",
            booking_date=date(2027, 10, 10),
            voucher_no="ER-006",
            description="Reparatur Büroausstattung",
            lines=(
                _debit("4800", "500.00"),
                _debit("1576", "95.00"),
                _credit("1200", "595.00"),
            ),
        ),

        # 18. Sonstiger betrieblicher Ertrag
        _booking(
            booking_id="00000000-0000-0000-0001-000000000018",
            booking_date=date(2027, 11, 5),
            voucher_no="ZE-003",
            description="Sonstiger betrieblicher Ertrag",
            lines=(
                _debit("1200", "500.00"),
                _credit("8500", "500.00"),
            ),
        ),

        # 19. Jahresabschreibung BGA
        _booking(
            booking_id="00000000-0000-0000-0001-000000000019",
            booking_date=date(2027, 12, 20),
            voucher_no="AB-001",
            description="Jahresabschreibung Betriebs- und Geschäftsausstattung",
            lines=(
                _debit("4830", "800.00"),
                _credit("0400", "800.00"),
            ),
        ),

        # 20. Offene Fremdleistungsrechnung zum Jahresende
        _booking(
            booking_id="00000000-0000-0000-0001-000000000020",
            booking_date=date(2027, 12, 28),
            voucher_no="ER-007",
            description="Offene Fremdleistungsrechnung",
            lines=(
                _debit("3100", "1000.00"),
                _debit("1576", "190.00"),
                _credit("1600", "1190.00"),
            ),
        ),
    )

    return ReferenceScenario(
        company=company,
        fiscal_year=REFERENCE_FISCAL_YEAR,
        bookings=bookings,
    )


def persist_reference_scenario(
    *,
    scenario: ReferenceScenario,
    company_repository: CompanyRepository,
    booking_repository: BookingRepository,
) -> None:
    """Persistiert das Referenzunternehmen einschließlich aller Buchungen."""

    if not isinstance(scenario, ReferenceScenario):
        raise TypeError(
            "scenario muss ein ReferenceScenario sein."
        )

    if not isinstance(company_repository, CompanyRepository):
        raise TypeError(
            "company_repository muss ein CompanyRepository sein."
        )

    if not isinstance(booking_repository, BookingRepository):
        raise TypeError(
            "booking_repository muss ein BookingRepository sein."
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
    
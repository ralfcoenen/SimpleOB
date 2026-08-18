"""Erzeugt eine reproduzierbare OpenBilanz-Entwicklungsdatenbank."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from openbilanz.core.config import load_config
from openbilanz.database.models import (
    Buchung,
    Buchungszeile,
    Mandant,
    Wirtschaftsjahr,
)

FISCAL_YEAR_START = date(2026, 1, 1)
FISCAL_YEAR_END = date(2026, 12, 31)


def _line(
    *,
    position: int,
    account_number: str,
    side: str,
    amount: str,
) -> Buchungszeile:
    return Buchungszeile(
        position=position,
        account_number=account_number,
        side=side,
        amount=Decimal(amount),
    )


def _booking(
    *,
    fiscal_year_id: int,
    booking_date: date,
    description: str,
    debit_account: str,
    credit_account: str,
    amount: str,
) -> Buchung:
    booking = Buchung(
        booking_id=str(uuid4()),
        wirtschaftsjahr_id=fiscal_year_id,
        booking_date=booking_date,
        voucher_no=None,
        description=description,
        booking_type="REGULAR",
    )

    booking.zeilen = [
        _line(
            position=0,
            account_number=debit_account,
            side="DEBIT",
            amount=amount,
        ),
        _line(
            position=1,
            account_number=credit_account,
            side="CREDIT",
            amount=amount,
        ),
    ]

    return booking


def _recreate_database(
    database_file: Path,
) -> None:
    """Löscht die Datenbank und erzeugt das aktuelle Schema per Alembic."""

    if database_file.exists():
        database_file.unlink()

    database_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "upgrade",
            "head",
        ],
        check=True,
    )


def _seed_database(
    database_file: Path,
) -> None:
    """Erzeugt Mandant, Geschäftsjahr und Testbuchungen."""

    engine = create_engine(
        f"sqlite:///{database_file}",
        echo=False,
    )

    try:
        with Session(engine) as session:
            company = Mandant(
                company_id=str(uuid4()),
                name="OpenBilanz Test-UG",
                rechtsform="UG (haftungsbeschränkt)",
            )

            session.add(company)
            session.flush()

            fiscal_year = Wirtschaftsjahr(
                mandant_id=company.id,
                start_date=FISCAL_YEAR_START,
                end_date=FISCAL_YEAR_END,
                status="OPEN",
            )

            session.add(fiscal_year)
            session.flush()

            bookings = (
                # Einzahlung Stammkapital
                _booking(
                    fiscal_year_id=fiscal_year.id,
                    booking_date=date(2026, 1, 2),
                    description="Einzahlung Stammkapital",
                    debit_account="1200",
                    credit_account="0800",
                    amount="25000.00",
                ),

                # Anlagevermögen gegen Bank
                _booking(
                    fiscal_year_id=fiscal_year.id,
                    booking_date=date(2026, 2, 1),
                    description="Anschaffung Anlagevermögen",
                    debit_account="0400",
                    credit_account="1200",
                    amount="10000.00",
                ),

                # Aufwand
                _booking(
                    fiscal_year_id=fiscal_year.id,
                    booking_date=date(2026, 3, 10),
                    description="Bürobedarf",
                    debit_account="4930",
                    credit_account="1200",
                    amount="1500.00",
                ),

                # Erlös
                _booking(
                    fiscal_year_id=fiscal_year.id,
                    booking_date=date(2026, 4, 15),
                    description="Umsatzerlös",
                    debit_account="1200",
                    credit_account="8400",
                    amount="2000.00",
                ),

                # weiterer Aufwand, damit GuV = 0
                _booking(
                    fiscal_year_id=fiscal_year.id,
                    booking_date=date(2026, 5, 10),
                    description="Weiterer betrieblicher Aufwand",
                    debit_account="4930",
                    credit_account="1200",
                    amount="500.00",
                ),
            )

            session.add_all(bookings)
            session.commit()

    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Erzeugt die konfigurierte OpenBilanz-Datenbank "
            "als reproduzierbaren Entwicklungs-Testfall."
        )
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Bestätigt das Löschen der bestehenden Datenbank.",
    )

    args = parser.parse_args()

    config = load_config()
    database_file = config.database_file

    if database_file.exists() and not args.force:
        raise SystemExit(
            "\nDie Datenbank existiert bereits:\n"
            f"  {database_file}\n\n"
            "Zum vollständigen Neuaufbau ausdrücklich aufrufen mit:\n"
            "  python scripts/create_demo_database.py --force\n"
        )

    print(
        f"Erzeuge Entwicklungsdatenbank: {database_file}"
    )

    _recreate_database(
        database_file
    )

    _seed_database(
        database_file
    )

    print()
    print("Testdatenbank wurde erzeugt.")
    print()
    print("Mandant:")
    print("  OpenBilanz Test-UG")
    print()
    print("Geschäftsjahr:")
    print("  01.01.2026 - 31.12.2026")
    print("  Status: OPEN")
    print()
    print("Sollzustand:")
    print("  Bank 1200:          15.000,00 EUR")
    print("  Anlagekonto 0400:   10.000,00 EUR")
    print("  Stammkapital 0800:  25.000,00 EUR")
    print("  GuV-Ergebnis:            0,00 EUR")
    print("  Bilanzsumme:        25.000,00 EUR")
    print()


if __name__ == "__main__":
    main()
    
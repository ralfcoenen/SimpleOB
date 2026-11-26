from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from simpleob.domain.bank_booking_proposal import (
    BankBookingProposal,
    CounterBookingLineProposal,
    build_booking_proposals,
)
from simpleob.domain.bank_transaction import TransactionImportStatus
from simpleob.domain.entry_side import EntrySide
from simpleob.importers.bank_csv_errors import BankCsvImportError
from simpleob.importers.qonto_csv_importer import QontoCsvImporter

HEADER = (
    "Transaction ID;Status;Settlement date (local);Counterparty name;Reference;"
    "Total amount (incl. VAT);Currency"
)


def _write_csv(tmp_path: Path, body: str, header: str = HEADER) -> Path:
    path = tmp_path / "qonto-synthetic.csv"
    path.write_text(f"{header}\n{body}", encoding="utf-8")
    return path


def test_loads_by_column_names_and_normalizes_signed_amounts(tmp_path: Path) -> None:
    reordered_header = (
        "Currency;Reference;Total amount (incl. VAT);Transaction ID;Status;"
        "Counterparty name;Settlement date (local)"
    )
    path = _write_csv(
        tmp_path,
        "EUR;Büromaterial;-119,00;TEST-001;completed;Bürobedarf GmbH;16.11.2026\n"
        "EUR;Rechnung 2026-041;1190,00;TEST-002;completed;Muster GmbH;17.11.2026",
        reordered_header,
    )

    transactions = QontoCsvImporter().load(path)

    assert [item.external_transaction_id for item in transactions] == ["TEST-001", "TEST-002"]
    assert [item.amount for item in transactions] == [Decimal("-119.00"), Decimal("1190.00")]
    assert transactions[0].booking_date == date(2026, 11, 16)
    assert transactions[0].counterparty == "Bürobedarf GmbH"
    assert transactions[0].reference == "Büromaterial"
    assert transactions[0].source_record.value("Total amount (incl. VAT)") == "-119,00"


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (";completed;16.11.2026;Partner;Referenz;1,00;EUR", "Transaction ID"),
        ("ID-1;completed;;Partner;Referenz;1,00;EUR", "Settlement date"),
        ("ID-1;completed;31.02.2026;Partner;Referenz;1,00;EUR", "gültiges Datum"),
        ("ID-1;completed;16.11.2026;Partner;Referenz;1.00;EUR", "Dezimalkomma"),
        ("ID-1;completed;16.11.2026;Partner;Referenz;1,00;EU", "Currency"),
    ],
)
def test_reports_invalid_required_fields_with_line_number(
    tmp_path: Path,
    body: str,
    message: str,
) -> None:
    with pytest.raises(BankCsvImportError) as error:
        QontoCsvImporter().load(_write_csv(tmp_path, body))

    assert "Zeile 2" in str(error.value)
    assert message in str(error.value)


def test_rejects_duplicate_transaction_ids_in_one_file(tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path,
        "DUP;completed;16.11.2026;Partner;A;1,00;EUR\n"
        "DUP;completed;17.11.2026;Partner;B;2,00;EUR",
    )

    with pytest.raises(BankCsvImportError, match=r"Zeile 3: Doppelte Transaction ID"):
        QontoCsvImporter().load(path)


def test_unsettled_transaction_is_not_offered_as_bookable(tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path,
        "PENDING;pending;16.11.2026;Partner;Referenz;1,00;EUR",
    )
    transaction = QontoCsvImporter().load(path)[0]

    assert transaction.import_validation_status is TransactionImportStatus.NOT_SETTLED
    assert build_booking_proposals((transaction,)) == ()


def test_proposal_accepts_multiple_counter_lines_and_maps_positive_direction(
    tmp_path: Path,
) -> None:
    transaction = QontoCsvImporter().load(
        _write_csv(tmp_path, "IN;completed;16.11.2026;Partner;Referenz;119,00;EUR")
    )[0]
    proposal = build_booking_proposals((transaction,))[0]
    proposal.bank_account_number = "1200"
    proposal.counter_lines = (
        CounterBookingLineProposal("4930", Decimal("100.00")),
        CounterBookingLineProposal("1576", Decimal("19.00")),
    )

    assert proposal.is_valid
    booking = proposal.to_booking()
    assert booking.debit_lines[0].account_number == "1200"
    assert all(line.side is EntrySide.CREDIT for line in booking.credit_lines)
    assert len(booking.credit_lines) == 2
    assert booking.debit_total == booking.credit_total == Decimal("119.00")


def test_negative_proposal_maps_counter_lines_to_debit(tmp_path: Path) -> None:
    transaction = QontoCsvImporter().load(
        _write_csv(tmp_path, "OUT;completed;16.11.2026;Partner;Referenz;-119,00;EUR")
    )[0]
    proposal = build_booking_proposals((transaction,))[0]
    proposal.bank_account_number = "1200"
    proposal.counter_lines = (CounterBookingLineProposal("4930", Decimal("119.00")),)

    booking = proposal.to_booking()

    assert booking.debit_lines[0].account_number == "4930"
    assert booking.credit_lines[0].account_number == "1200"


def test_proposal_reports_missing_accounts_and_unbalanced_counter_lines(
    tmp_path: Path,
) -> None:
    transaction = QontoCsvImporter().load(
        _write_csv(tmp_path, "IN;completed;16.11.2026;Partner;Referenz;119,00;EUR")
    )[0]
    proposal = build_booking_proposals((transaction,))[0]
    proposal.counter_lines = (CounterBookingLineProposal("4930", Decimal("118.00")),)

    assert not proposal.is_valid
    assert any("Bank-Sachkonto" in error for error in proposal.validation_errors)
    assert any("stimmt nicht" in error for error in proposal.validation_errors)
    with pytest.raises(ValueError, match="Buchungsvorschlag ist ungültig"):
        proposal.to_booking()


def test_proposal_can_be_created_with_one_default_counter_line(tmp_path: Path) -> None:
    transaction = QontoCsvImporter().load(
        _write_csv(tmp_path, "IN;completed;16.11.2026;Partner;Referenz;119,00;EUR")
    )[0]

    proposal = build_booking_proposals((transaction,))[0]

    assert len(proposal.counter_lines) == 1
    assert proposal.counter_lines[0].amount == Decimal("119.00")
    assert isinstance(proposal, BankBookingProposal)

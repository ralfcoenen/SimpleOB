"""Profilparser: Kompatibilität, Betragsinterpretation und strenge Fehlerbehandlung."""

from dataclasses import replace
from decimal import Decimal
from io import StringIO

import pytest

from simpleob.domain.bank_transaction import BankImportSource, TransactionImportStatus
from simpleob.domain.csv_import_profile import (
    CsvAmount,
    CsvColumn,
    CsvStatus,
    qonto_compatibility_profile,
)
from simpleob.importers.bank_csv_errors import BankCsvImportError
from simpleob.importers.profile_csv_importer import ProfileCsvImporter
from simpleob.importers.qonto_csv_importer import QontoCsvImporter
from tests.importers.test_qonto_csv_importer import HEADER


def test_compatibility_profile_matches_existing_parser():
    text = (
        HEADER
        + ";Operation date (local)\n"
        + (
            " ID-1 ;COMPLETED;16.11.2026; Partner ; Zweck ;-119,00;eur;15.11.2026\n"
            "ID-2;pending;17.11.2026;;;1190,00;EUR;\n"
        )
    )
    profile = qonto_compatibility_profile()
    assert ProfileCsvImporter(profile).load_file(
        StringIO(text)
    ) == QontoCsvImporter().load_file(StringIO(text))
    # Die optionale Datumsspalte darf wie bisher vollständig fehlen.
    text = HEADER + "\nID-3;completed;16.11.2026;P;R;1,00;EUR"
    assert ProfileCsvImporter(profile).load_file(
        StringIO(text)
    ) == QontoCsvImporter().load_file(StringIO(text))


def _profile(**changes):
    base = qonto_compatibility_profile()
    return replace(base, import_source=BankImportSource("custom.bank"), **changes)


def _read(profile, amount="1,00", status="completed", extra_header="", extra=""):
    return ProfileCsvImporter(profile).load_file(
        StringIO(
            HEADER
            + extra_header
            + "\n"
            + f"ID;{status};16.11.2026;P;R;{amount};EUR{extra}"
        )
    )


def test_signed_direction_grouping_and_original_values():
    p = _profile(
        thousands_separator=".",
        amount=CsvAmount(
            "signed", CsvColumn("Total amount (incl. VAT)"), positive_means="outflow"
        ),
    )
    transaction = _read(p, "1.234,56")[0]
    assert transaction.amount == Decimal("-1234.56")
    assert transaction.source_record.value("Total amount (incl. VAT)") == "1.234,56"
    assert transaction.import_source.value == "custom.bank"


@pytest.mark.parametrize(
    ("incoming", "outgoing", "expected"),
    [("10,00", "", "10"), ("0,00", "12,34", "-12.34")],
)
def test_separate_amount_columns(incoming, outgoing, expected):
    p = _profile(
        amount=CsvAmount(
            "separate", inflow_column=CsvColumn("In"), outflow_column=CsvColumn("Out")
        )
    )
    result = _read(p, extra_header=";In;Out", extra=f";{incoming};{outgoing}")
    assert result[0].amount == Decimal(expected)


@pytest.mark.parametrize(
    ("incoming", "outgoing"),
    [("1,00", "2,00"), ("", ""), ("-1,00", ""), ("0,00", "0,00")],
)
def test_ambiguous_separate_amounts_fail(incoming, outgoing):
    p = _profile(
        amount=CsvAmount(
            "separate", inflow_column=CsvColumn("In"), outflow_column=CsvColumn("Out")
        )
    )
    with pytest.raises(BankCsvImportError, match="Zeile 2"):
        _read(p, extra_header=";In;Out", extra=f";{incoming};{outgoing}")


@pytest.mark.parametrize(
    "amount",
    [
        "1.23,45",
        "01,00",
        "NaN",
        "1,001",
        "1",
        "0,00",
        "1e2",
        "1,00 EUR",
        "999999999999999999999999999999,00",
    ],
)
def test_invalid_amounts_fail_with_line_number(amount):
    with pytest.raises(BankCsvImportError, match="Zeile 2"):
        _read(_profile(thousands_separator="."), amount)


def test_status_requires_explicit_configuration():
    p = _profile(status=CsvStatus(CsvColumn("Status"), (("booked", "ready"),)))
    with pytest.raises(BankCsvImportError, match="Unbekannter Status"):
        _read(p)
    assert (
        _read(p, status="BOOKED")[0].import_validation_status
        is TransactionImportStatus.READY
    )
    assert (
        _read(_profile(), status="unknown")[0].import_validation_status
        is TransactionImportStatus.NOT_SETTLED
    )
    with pytest.raises(ValueError, match="ausdrücklich"):
        CsvStatus()
    assert (
        _read(_profile(status=CsvStatus(assume_settled=True)))[
            0
        ].import_validation_status
        is TransactionImportStatus.READY
    )


@pytest.mark.parametrize(
    "text",
    [
        "ID;ID\na;b",
        HEADER + "\nID;completed;16.11.2026;P;R;1,00;EUR;extra",
        HEADER
        + "\nID;completed;16.11.2026;P;R;1,00;EUR\nID;completed;16.11.2026;P;R;2,00;EUR",
        HEADER
        + "\nID;completed;16.11.2026;P;R;1,00;EUR\nBAD;completed;31.02.2026;P;R;2,00;EUR",
        HEADER + '\n"unterminated',
    ],
)
def test_structure_and_row_errors_never_return_partial_results(text):
    with pytest.raises(BankCsvImportError, match="Zeile"):
        ProfileCsvImporter(_profile()).load_file(StringIO(text))


def test_encoding_and_file_loading(tmp_path):
    p = _profile(encoding="cp1252")
    path = tmp_path / "bank.csv"
    path.write_bytes(
        (HEADER + "\nID;completed;16.11.2026;Müller;R;1,00;EUR").encode("cp1252")
    )
    assert ProfileCsvImporter(p).load(path)[0].counterparty == "Müller"
    with pytest.raises(BankCsvImportError, match="Zeichencodierung"):
        ProfileCsvImporter(qonto_compatibility_profile()).load(path)

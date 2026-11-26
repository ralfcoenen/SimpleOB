"""Parser für das ausdrücklich synthetische Qonto-CSV-Testformat.

Das Format verwendet UTF-8, Semikolon, Datum TT.MM.JJJJ und Dezimalkomma
ohne Tausendertrennzeichen. Es ist keine bestätigte Qonto-Exportdefinition.
"""

import csv
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from simpleob.domain.bank_transaction import (
    BankImportSource,
    BankTransaction,
    BankTransactionCsvRecord,
    TransactionImportStatus,
)
from simpleob.importers.bank_csv_errors import BankCsvImportError

_REQUIRED_COLUMNS = (
    "Transaction ID",
    "Status",
    "Settlement date (local)",
    "Counterparty name",
    "Reference",
    "Total amount (incl. VAT)",
    "Currency",
)
_AMOUNT_PATTERN = re.compile(r"[+-]?(?:0|[1-9][0-9]*),[0-9]{2}\Z")


class QontoCsvImporter:
    """Liest Transaktionen anhand der Spaltennamen des Testformats ein."""

    def load(self, path: Path) -> tuple[BankTransaction, ...]:
        """Liest eine UTF-8-CSV-Datei; ungültige Daten liefern Zeilenfehler."""
        if not isinstance(path, Path):
            raise TypeError("path muss ein Path sein.")
        try:
            with path.open("r", encoding="utf-8", newline="") as csv_file:
                return self.load_file(csv_file)
        except UnicodeDecodeError as exc:
            raise BankCsvImportError(("Die CSV-Datei ist nicht gültiges UTF-8.",)) from exc
        except OSError as exc:
            raise BankCsvImportError((f"CSV-Datei konnte nicht gelesen werden: {exc}",)) from exc

    def load_file(self, csv_file) -> tuple[BankTransaction, ...]:
        """Liest einen Textstream; primär für Tests und aufrufende Importadapter."""
        reader = csv.DictReader(csv_file, delimiter=";", strict=True)
        headers = reader.fieldnames
        if headers is None:
            raise BankCsvImportError(("Die CSV-Datei enthält keine Kopfzeile.",))
        if len(headers) != len(set(headers)):
            raise BankCsvImportError(("Die CSV-Kopfzeile enthält doppelte Spaltennamen.",))
        missing = tuple(column for column in _REQUIRED_COLUMNS if column not in headers)
        if missing:
            raise BankCsvImportError(
                ("Fehlende Pflichtspalten: " + ", ".join(missing) + ".",)
            )

        transactions: list[BankTransaction] = []
        errors: list[str] = []
        seen_ids: dict[str, int] = {}
        try:
            rows = iter(reader)
            for row in rows:
                line_number = reader.line_num
                if None in row or any(value is None for value in row.values()):
                    errors.append(f"Zeile {line_number}: Die Spaltenanzahl ist ungültig.")
                    continue
                raw_values = tuple(row[header] for header in headers)
                source_record = BankTransactionCsvRecord(
                    line_number=line_number,
                    headers=tuple(headers),
                    values=raw_values,
                )
                try:
                    transaction = self._normalize_row(row, source_record)
                except ValueError as exc:
                    errors.append(f"Zeile {line_number}: {exc}")
                    continue
                previous_line = seen_ids.get(transaction.external_transaction_id)
                if previous_line is not None:
                    errors.append(
                        f"Zeile {line_number}: Doppelte Transaction ID "
                        f"{transaction.external_transaction_id!r} (bereits in Zeile {previous_line})."
                    )
                    continue
                seen_ids[transaction.external_transaction_id] = line_number
                transactions.append(transaction)
        except csv.Error as exc:
            errors.append(f"Zeile {reader.line_num}: CSV-Formatfehler: {exc}")

        if errors:
            raise BankCsvImportError(tuple(errors))
        if not transactions:
            raise BankCsvImportError(("Die CSV-Datei enthält keine Transaktionen.",))
        return tuple(transactions)

    @staticmethod
    def _normalize_row(row: dict[str, str], source_record: BankTransactionCsvRecord) -> BankTransaction:
        transaction_id = row["Transaction ID"].strip()
        if not transaction_id:
            raise ValueError("Transaction ID ist ein Pflichtfeld und darf nicht leer sein.")
        status = row["Status"].strip()
        if not status:
            raise ValueError("Status ist ein Pflichtfeld und darf nicht leer sein.")
        settlement_date = _parse_date(row["Settlement date (local)"], "Settlement date (local)")
        amount = _parse_amount(row["Total amount (incl. VAT)"])
        currency = row["Currency"].strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", currency):
            raise ValueError("Currency muss aus genau drei Buchstaben bestehen.")
        settled = status.casefold() == "completed"
        operation_date = row.get("Operation date (local)")
        transaction_date = (
            _parse_date(operation_date, "Operation date (local)")
            if operation_date and operation_date.strip()
            else None
        )
        return BankTransaction(
            import_source=BankImportSource.QONTO_CSV,
            external_transaction_id=transaction_id,
            booking_date=settlement_date,
            transaction_date=transaction_date,
            counterparty=row["Counterparty name"],
            reference=row["Reference"],
            amount=amount,
            currency=currency,
            transaction_status=status,
            import_validation_status=(
                TransactionImportStatus.READY
                if settled
                else TransactionImportStatus.NOT_SETTLED
            ),
            source_record=source_record,
        )


def _parse_date(value: str, field_name: str) -> date:
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} ist ein Pflichtfeld und darf nicht leer sein.")
    try:
        parsed = datetime.strptime(text, "%d.%m.%Y").date()
    except ValueError as exc:
        raise ValueError(f"{field_name} muss ein gültiges Datum im Format TT.MM.JJJJ sein.") from exc
    if parsed.strftime("%d.%m.%Y") != text:
        raise ValueError(f"{field_name} muss exakt im Format TT.MM.JJJJ angegeben sein.")
    return parsed


def _parse_amount(value: str) -> Decimal:
    text = value.strip()
    if not _AMOUNT_PATTERN.fullmatch(text):
        raise ValueError(
            "Total amount (incl. VAT) muss im Testformat mit Dezimalkomma "
            "und genau zwei Nachkommastellen angegeben sein (ohne Tausendertrennzeichen)."
        )
    try:
        amount = Decimal(text.replace(",", "."))
    except InvalidOperation as exc:
        raise ValueError("Total amount (incl. VAT) ist kein gültiger Dezimalbetrag.") from exc
    if amount == Decimal("0.00"):
        raise ValueError("Total amount (incl. VAT) darf nicht 0,00 sein.")
    return amount

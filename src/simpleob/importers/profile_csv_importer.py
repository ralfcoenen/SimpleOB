"""Strenger profilgesteuerter CSV-Import in normalisierte Banktransaktionen."""

import csv
import re
from datetime import datetime
from decimal import Decimal, DecimalException
from pathlib import Path

from simpleob.domain.bank_transaction import (
    BankTransaction,
    BankTransactionCsvRecord,
    TransactionImportStatus,
)
from simpleob.domain.csv_import_profile import CsvColumn, CsvImportProfile
from simpleob.domain.money import to_decimal
from simpleob.importers.bank_csv_errors import BankCsvImportError


class ProfileCsvImporter:
    def __init__(self, profile: CsvImportProfile):
        if not isinstance(profile, CsvImportProfile):
            raise TypeError("profile muss ein CsvImportProfile sein.")
        self.profile = profile

    def load(self, path: Path) -> tuple[BankTransaction, ...]:
        if not isinstance(path, Path):
            raise TypeError("path muss ein Path sein.")
        try:
            with path.open("r", encoding=self.profile.encoding, newline="") as stream:
                return self.load_file(stream)
        except UnicodeError as exc:
            raise BankCsvImportError(
                (f"CSV-Zeichencodierung ungültig ({self.profile.encoding}).",)
            ) from exc
        except OSError as exc:
            raise BankCsvImportError(
                (f"CSV-Datei konnte nicht gelesen werden: {exc}",)
            ) from exc

    def load_file(self, stream) -> tuple[BankTransaction, ...]:
        reader = csv.reader(stream, delimiter=self.profile.delimiter, strict=True)
        errors = []
        transactions = []
        seen = {}
        try:
            headers = next(reader, None)
            if not headers or any(not h.strip() for h in headers):
                raise BankCsvImportError(
                    ("Zeile 1: CSV-Kopfzeile fehlt oder enthält leere Spaltennamen.",)
                )
            if len(headers) != len(set(headers)):
                raise BankCsvImportError(
                    ("Zeile 1: CSV-Kopfzeile enthält doppelte Spaltennamen.",)
                )
            missing = [
                b.column
                for b in self.profile.bindings()
                if b.required and b.column not in headers
            ]
            if missing:
                raise BankCsvImportError(
                    ("Zeile 1: Fehlende Pflichtspalten: " + ", ".join(missing),)
                )
            for values in reader:
                # Wie DictReader im bisherigen Importer: vollständig leere Zeilen ignorieren.
                if not values:
                    continue
                line = reader.line_num
                if len(values) != len(headers):
                    errors.append(f"Zeile {line}: Die Spaltenanzahl ist ungültig.")
                    continue
                record = BankTransactionCsvRecord(line, tuple(headers), tuple(values))
                try:
                    transaction = self._row(
                        dict(zip(headers, values, strict=True)), record
                    )
                    previous = seen.get(transaction.external_transaction_id)
                    if previous is not None:
                        raise ValueError(
                            f"Doppelte Transaktions-ID (bereits in Zeile {previous})."
                        )
                    seen[transaction.external_transaction_id] = line
                    transactions.append(transaction)
                except ValueError as exc:
                    errors.append(f"Zeile {line}: {exc}")
        except csv.Error as exc:
            errors.append(f"Zeile {reader.line_num}: CSV-Formatfehler: {exc}")
        except UnicodeError as exc:
            errors.append(
                f"Zeile {reader.line_num + 1}: Ungültige Zeichencodierung: {exc}"
            )
        if errors:
            raise BankCsvImportError(tuple(errors))
        if not transactions:
            raise BankCsvImportError(("Die CSV-Datei enthält keine Transaktionen.",))
        return tuple(transactions)

    @staticmethod
    def _value(row, binding: CsvColumn | None):
        return row.get(binding.column, "").strip() if binding else ""

    def _date(self, text, field):
        try:
            value = datetime.strptime(text, self.profile.date_format).date()
            if value.strftime(self.profile.date_format) != text:
                raise ValueError()
            return value
        except ValueError as exc:
            raise ValueError(
                f"{field}: Datum muss exakt {self.profile.date_format} entsprechen."
            ) from exc

    def _amount(self, text):
        decimal = re.escape(self.profile.decimal_separator)
        thousands = self.profile.thousands_separator
        integer = r"(?:0|[1-9][0-9]*)"
        if thousands is not None:
            group = re.escape(thousands)
            integer = rf"(?:{integer}|[1-9][0-9]{{0,2}}(?:{group}[0-9]{{3}})+)"
        if not re.fullmatch(rf"[+-]?{integer}{decimal}[0-9]{{2}}", text):
            raise ValueError(
                "Betrag muss ein vollständiger Dezimalbetrag mit genau zwei Nachkommastellen und gültiger Gruppierung sein."
            )
        if thousands:
            text = text.replace(thousands, "")
        amount = Decimal(text.replace(self.profile.decimal_separator, "."))
        try:
            normalized = to_decimal(amount)
        except DecimalException as exc:
            raise ValueError(
                "Betrag überschreitet die unterstützte Genauigkeit."
            ) from exc
        if normalized != amount:
            raise ValueError("Betrag ist nicht centgenau darstellbar.")
        return normalized

    def _row(self, row, record):
        profile = self.profile

        def value(binding):
            return self._value(row, binding)

        spec = profile.amount
        if spec.model == "signed":
            amount = self._amount(value(spec.column))
            if spec.positive_means == "outflow":
                amount = -amount
        else:
            incoming = (
                self._amount(value(spec.inflow_column))
                if value(spec.inflow_column)
                else Decimal("0")
            )
            outgoing = (
                self._amount(value(spec.outflow_column))
                if value(spec.outflow_column)
                else Decimal("0")
            )
            if incoming < 0 or outgoing < 0 or (incoming > 0) == (outgoing > 0):
                raise ValueError(
                    "Genau eine Eingang-/Ausgangsspalte muss positiv sein; negative Werte sind unzulässig."
                )
            amount = incoming - outgoing
        if not amount:
            raise ValueError("Der Betrag darf nicht null sein.")
        status_spec = profile.status
        if status_spec.column is None:
            status = "profile_assumed_settled"
            validation = TransactionImportStatus.READY
        else:
            status = value(status_spec.column)
            if not status:
                raise ValueError("Status darf nicht leer sein.")
            normalize = (lambda s: s) if status_spec.case_sensitive else str.casefold
            mapping = {normalize(k): v for k, v in status_spec.mapping}
            target = mapping.get(normalize(status))
            if target is None:
                if status_spec.unmapped == "error":
                    raise ValueError(f"Unbekannter Status: {status!r}")
                target = "not_settled"
            validation = TransactionImportStatus(target)
        columns = profile.columns
        optional_date = value(columns.transaction_date)
        return BankTransaction(
            import_source=profile.import_source,
            external_transaction_id=value(columns.external_transaction_id),
            booking_date=self._date(value(columns.booking_date), "Buchungsdatum"),
            transaction_date=self._date(optional_date, "Transaktionsdatum")
            if optional_date
            else None,
            counterparty=value(columns.counterparty),
            reference=value(columns.reference),
            amount=amount,
            currency=value(columns.currency).upper(),
            transaction_status=status,
            import_validation_status=validation,
            source_record=record,
        )

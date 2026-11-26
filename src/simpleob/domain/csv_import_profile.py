"""Mandantenübergreifende CSV-Formatprofile ohne Konten oder Zugangsdaten."""

import codecs
import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from simpleob.domain.bank_transaction import BankImportSource


def _text(value: str) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(
            "Eine nichtleere Zeichenkette ohne Rand-Leerzeichen ist erforderlich."
        )


@dataclass(frozen=True, slots=True)
class CsvColumn:
    """Einheitliche Spaltenbindung; None am Verwendungsort bedeutet unzugeordnet."""

    column: str
    required: bool = True

    def __post_init__(self):
        _text(self.column)
        if type(self.required) is not bool:
            raise ValueError("required muss bool sein.")


@dataclass(frozen=True, slots=True)
class CsvColumns:
    external_transaction_id: CsvColumn
    booking_date: CsvColumn
    currency: CsvColumn
    transaction_date: CsvColumn | None = None
    counterparty: CsvColumn | None = None
    reference: CsvColumn | None = None

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            binding = getattr(self, name)
            if binding is not None and not isinstance(binding, CsvColumn):
                raise ValueError(f"Ungültige Spaltenbindung: {name}")
            if name in ("external_transaction_id", "booking_date", "currency"):
                if binding is None or not binding.required:
                    raise ValueError(f"Pflichtspalte fehlt: {name}")


@dataclass(frozen=True, slots=True)
class CsvAmount:
    model: str
    column: CsvColumn | None = None
    positive_means: str = "inflow"
    inflow_column: CsvColumn | None = None
    outflow_column: CsvColumn | None = None

    def __post_init__(self):
        if self.positive_means not in ("inflow", "outflow"):
            raise ValueError("Ungültige Vorzeicheninterpretation.")
        if self.model == "signed":
            bindings = (self.column,)
            invalid = self.inflow_column is not None or self.outflow_column is not None
        elif self.model == "separate":
            bindings = (self.inflow_column, self.outflow_column)
            invalid = self.column is not None or self.positive_means != "inflow"
        else:
            raise ValueError("Unbekanntes Betragsmodell.")
        if invalid or any(
            not isinstance(b, CsvColumn) or not b.required for b in bindings
        ):
            raise ValueError("Widersprüchliche oder fehlende Betragsspalten.")


@dataclass(frozen=True, slots=True)
class CsvStatus:
    column: CsvColumn | None = None
    mapping: tuple[tuple[str, str], ...] = ()
    case_sensitive: bool = False
    unmapped: str = "error"
    assume_settled: bool = False

    def __post_init__(self):
        if (
            type(self.case_sensitive) is not bool
            or type(self.assume_settled) is not bool
        ):
            raise ValueError("Statusoptionen müssen bool sein.")
        if self.unmapped not in ("error", "not_settled"):
            raise ValueError("Ungültige Behandlung unbekannter Statuswerte.")
        if not isinstance(self.mapping, tuple):
            raise ValueError("Statusmapping muss unveränderlich sein.")
        seen = set()
        for pair in self.mapping:
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise ValueError("Ungültiges Statusmapping.")
            key, target = pair
            _text(key)
            normalized = key if self.case_sensitive else key.casefold()
            if normalized in seen or target not in ("ready", "not_settled"):
                raise ValueError("Mehrdeutiges oder ungültiges Statusmapping.")
            seen.add(normalized)
        if self.column is None:
            if not self.assume_settled or self.mapping or self.unmapped != "error":
                raise ValueError(
                    "Ohne Statusspalte muss assume_settled ausdrücklich gesetzt sein."
                )
        elif (
            not isinstance(self.column, CsvColumn)
            or not self.column.required
            or self.assume_settled
        ):
            raise ValueError("Widersprüchliche Statuskonfiguration.")


@dataclass(frozen=True, slots=True)
class CsvImportProfile:
    profile_id: UUID
    name: str
    import_source: BankImportSource
    delimiter: str
    encoding: str
    date_format: str
    decimal_separator: str
    thousands_separator: str | None
    columns: CsvColumns
    amount: CsvAmount
    status: CsvStatus

    def __post_init__(self):
        if not isinstance(self.profile_id, UUID) or not isinstance(
            self.import_source, BankImportSource
        ):
            raise ValueError("Profil-ID oder Importquelle ungültig.")
        _text(self.name)
        if (
            not isinstance(self.delimiter, str)
            or len(self.delimiter) != 1
            or self.delimiter in '\r\n\x00"'
        ):
            raise ValueError("Ungültiges CSV-Trennzeichen.")
        _text(self.encoding)
        try:
            codecs.lookup(self.encoding)
            "".encode(self.encoding)
            b"".decode(self.encoding)
        except (LookupError, TypeError) as exc:
            raise ValueError("Ungeeignete Zeichencodierung.") from exc
        if self.decimal_separator not in (".", ","):
            raise ValueError("Ungültiges Dezimaltrennzeichen.")
        if (
            self.thousands_separator not in (None, ".", ",", " ", "'", "\u00a0")
            or self.thousands_separator == self.decimal_separator
        ):
            raise ValueError("Ungültiges Tausendertrennzeichen.")
        _text(self.date_format)
        directives = re.findall(r"%.", self.date_format)
        if sorted(directives) != ["%Y", "%d", "%m"] or "%" in re.sub(
            r"%[Ymd]", "", self.date_format
        ):
            raise ValueError("Datumsformat muss genau %Y, %m und %d enthalten.")
        datetime(2026, 11, 16).strftime(self.date_format)
        if (
            not isinstance(self.columns, CsvColumns)
            or not isinstance(self.amount, CsvAmount)
            or not isinstance(self.status, CsvStatus)
        ):
            raise ValueError("Ungültige Profilbestandteile.")
        names = [b.column for b in self.bindings()]
        if len(names) != len(set(names)):
            raise ValueError("CSV-Spalten dürfen nicht mehrfach zugeordnet werden.")

    def bindings(self) -> tuple[CsvColumn, ...]:
        bindings = [
            getattr(self.columns, name) for name in self.columns.__dataclass_fields__
        ]
        bindings.extend(
            (
                self.amount.column,
                self.amount.inflow_column,
                self.amount.outflow_column,
                self.status.column,
            )
        )
        return tuple(b for b in bindings if b is not None)


def qonto_compatibility_profile() -> CsvImportProfile:
    """Nur synthetisches Testformat; kein bestätigter originaler Qonto-Export."""
    return CsvImportProfile(
        profile_id=UUID("967116aa-e673-4a7c-9c42-58a790b25bf0"),
        name="Qonto – synthetisches Testformat",
        import_source=BankImportSource.QONTO_CSV,
        delimiter=";",
        encoding="utf-8",
        date_format="%d.%m.%Y",
        decimal_separator=",",
        thousands_separator=None,
        columns=CsvColumns(
            CsvColumn("Transaction ID"),
            CsvColumn("Settlement date (local)"),
            CsvColumn("Currency"),
            CsvColumn("Operation date (local)", False),
            CsvColumn("Counterparty name"),
            CsvColumn("Reference"),
        ),
        amount=CsvAmount("signed", CsvColumn("Total amount (incl. VAT)")),
        status=CsvStatus(
            CsvColumn("Status"), (("completed", "ready"),), unmapped="not_settled"
        ),
    )

"""Mandantenbezogene Einstellungen der informativen KR-Auswertung."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import UUID

from simpleob.domain.money import ZERO, to_decimal


@dataclass(frozen=True, slots=True)
class KrAnnualTurnoverAddition:
    calendar_year: int
    amount: Decimal

    def __post_init__(self) -> None:
        if (
            isinstance(self.calendar_year, bool)
            or not isinstance(self.calendar_year, int)
            or not 1 <= self.calendar_year <= 9999
        ):
            raise ValueError("Das Kalenderjahr ist ungültig.")
        if isinstance(self.amount, (bool, float)):
            raise TypeError("KR-Umsatzergänzungen müssen Decimal-Beträge sein.")
        try:
            raw_amount = Decimal(str(self.amount))
        except InvalidOperation as exc:
            raise ValueError("Umsatzergänzung ist kein gültiger Betrag.") from exc
        if not raw_amount.is_finite():
            raise ValueError("Umsatzergänzungen müssen endliche Beträge sein.")
        if raw_amount < ZERO:
            raise ValueError("Umsatzergänzungen dürfen nicht negativ sein.")
        if raw_amount != raw_amount.quantize(Decimal("0.01")):
            raise ValueError("Umsatzergänzungen dürfen höchstens zwei Nachkommastellen haben.")
        amount = to_decimal(self.amount)
        object.__setattr__(self, "amount", amount)


@dataclass(frozen=True, slots=True)
class KrSettings:
    company_id: UUID
    activity_start_date: date | None = None
    waiver_declared: bool = False
    waiver_date: date | None = None
    external_turnovers: tuple[KrAnnualTurnoverAddition, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.company_id, UUID):
            raise TypeError("company_id must be a UUID")
        if self.activity_start_date is not None and not isinstance(
            self.activity_start_date, date
        ):
            raise TypeError("activity_start_date must be a date or None")
        if not isinstance(self.waiver_declared, bool):
            raise TypeError("waiver_declared must be a bool")
        if self.waiver_date is not None and not isinstance(self.waiver_date, date):
            raise TypeError("waiver_date must be a date or None")
        if self.waiver_declared and self.waiver_date is None:
            raise ValueError("Bei dokumentiertem Verzicht ist ein Datum erforderlich.")
        if not self.waiver_declared and self.waiver_date is not None:
            raise ValueError("Ein Verzichtsdatum benötigt einen dokumentierten Verzicht.")
        if not isinstance(self.external_turnovers, tuple) or not all(
            isinstance(item, KrAnnualTurnoverAddition)
            for item in self.external_turnovers
        ):
            raise TypeError("external_turnovers must contain annual turnover values")
        years = [item.calendar_year for item in self.external_turnovers]
        if len(years) != len(set(years)):
            raise ValueError("Je Kalenderjahr darf nur eine Umsatzergänzung existieren.")

    def external_turnover_for(self, calendar_year: int) -> Decimal:
        return next(
            (
                item.amount
                for item in self.external_turnovers
                if item.calendar_year == calendar_year
            ),
            ZERO,
        )

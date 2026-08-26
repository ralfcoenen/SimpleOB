"""Anlagenbericht."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from openbilanz.domain.money import ZERO


@dataclass(frozen=True, slots=True)
class FixedAssetReportRow:
    """Eine Zeile des Anlagenberichts."""

    asset_code: str
    description: str
    asset_account_number: str
    acquisition_date: date
    acquisition_cost: Decimal
    opening_depreciation: Decimal
    current_depreciation: Decimal
    accumulated_depreciation: Decimal
    closing_book_value: Decimal
    disposal_date: date | None


@dataclass(frozen=True, slots=True)
class FixedAssetReport:
    """Anlagenübersicht für ein Geschäftsjahr."""

    start_date: date
    end_date: date
    rows: tuple[FixedAssetReportRow, ...]

    @property
    def acquisition_cost_total(self) -> Decimal:
        """Summe der Anschaffungskosten."""

        return sum(
            (
                row.acquisition_cost
                for row in self.rows
            ),
            start=ZERO,
        )

    @property
    def opening_depreciation_total(self) -> Decimal:
        """Kumulierte AfA vor Beginn des Geschäftsjahres."""

        return sum(
            (
                row.opening_depreciation
                for row in self.rows
            ),
            start=ZERO,
        )

    @property
    def current_depreciation_total(self) -> Decimal:
        """AfA des Geschäftsjahres."""

        return sum(
            (
                row.current_depreciation
                for row in self.rows
            ),
            start=ZERO,
        )

    @property
    def accumulated_depreciation_total(
        self,
    ) -> Decimal:
        """Kumulierte AfA bis zum Ende des Geschäftsjahres."""

        return sum(
            (
                row.accumulated_depreciation
                for row in self.rows
            ),
            start=ZERO,
        )

    @property
    def closing_book_value_total(self) -> Decimal:
        """Summe der Buchwerte zum Ende des Geschäftsjahres."""

        return sum(
            (
                row.closing_book_value
                for row in self.rows
            ),
            start=ZERO,
        )

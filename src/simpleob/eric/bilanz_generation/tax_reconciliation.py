"""Fachliches Modell für HGBM-Überleitungsrechnungen."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class TaxReconciliationKind(Enum):
    """Von SimpleOB unterstützte Art einer Überleitungsrechnung."""

    CHANGE_VALUE = "hbst.transfer.kind.changeValue"


@dataclass(frozen=True, slots=True)
class TaxReconciliationChange:
    """Wertänderung einer einzelnen Taxonomieposition."""

    concept_name: str
    actual_period: Decimal
    previous_period: Decimal | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.concept_name, str):
            raise TypeError("concept_name must be a string")

        if not self.concept_name.strip():
            raise ValueError("concept_name must not be blank")

        if not isinstance(self.actual_period, Decimal):
            raise TypeError("actual_period must be a Decimal")

        if (
            self.previous_period is not None
            and not isinstance(self.previous_period, Decimal)
        ):
            raise TypeError(
                "previous_period must be a Decimal or None"
            )


@dataclass(frozen=True, slots=True)
class TaxReconciliationTransfer:
    """Eine steuerliche Überleitung eines HGBM-Abschlusses."""

    kind: TaxReconciliationKind
    asset_changes: tuple[TaxReconciliationChange, ...] = ()
    equity_liability_changes: tuple[
        TaxReconciliationChange,
        ...,
    ] = ()
    income_statement_changes: tuple[
        TaxReconciliationChange,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.kind, TaxReconciliationKind):
            raise TypeError(
                "kind must be a TaxReconciliationKind"
            )

        for field_name, changes in (
            ("asset_changes", self.asset_changes),
            (
                "equity_liability_changes",
                self.equity_liability_changes,
            ),
            (
                "income_statement_changes",
                self.income_statement_changes,
            ),
        ):
            if not isinstance(changes, tuple):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

            if not all(
                isinstance(change, TaxReconciliationChange)
                for change in changes
            ):
                raise TypeError(
                    f"{field_name} must contain only "
                    "TaxReconciliationChange objects"
                )

        if not (
            self.asset_changes
            or self.equity_liability_changes
            or self.income_statement_changes
        ):
            raise ValueError(
                "tax reconciliation transfer must contain "
                "at least one change"
            )

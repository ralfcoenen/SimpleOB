"""Umsatzsteuerliche Konfiguration eines Mandanten."""

from dataclasses import dataclass
from datetime import date

from openbilanz.domain.vat_taxation_method import (
    VatTaxationMethod,
)
from openbilanz.domain.vat_taxation_type import (
    VatTaxationType,
)


@dataclass(frozen=True, slots=True)
class VatConfiguration:
    """Umsatzsteuerliche Behandlung ab einem bestimmten Datum."""

    taxation_type: VatTaxationType
    effective_from: date
    taxation_method: VatTaxationMethod = (
        VatTaxationMethod.AGREED
    )
    def __post_init__(self) -> None:
        if not isinstance(
            self.taxation_type,
            VatTaxationType,
        ):
            raise TypeError(
                "taxation_type must be a VatTaxationType"
            )

        if not isinstance(
            self.effective_from,
            date,
        ):
            raise TypeError(
                "effective_from must be a date"
            )
        if not isinstance(
            self.taxation_method,
            VatTaxationMethod,
        ):
            raise TypeError(
                "taxation_method must be a VatTaxationMethod"
            )

    @property
    def is_small_business(self) -> bool:
        """Gibt an, ob § 19 UStG angewendet wird."""

        return (
            self.taxation_type
            is VatTaxationType.SMALL_BUSINESS
        )

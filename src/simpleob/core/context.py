"""Aktueller Anwendungskontext."""

from dataclasses import dataclass

from simpleob.domain.company import Company
from simpleob.domain.fiscal_year import FiscalYear


@dataclass(frozen=True, slots=True)
class ApplicationContext:
    """Beschreibt den aktuell geöffneten Buchhaltungsbestand."""

    company: Company
    fiscal_year: FiscalYear

    def __post_init__(self) -> None:
        """Validiert den Anwendungskontext."""

        if not isinstance(self.company, Company):
            raise TypeError(
                "company must be a Company"
            )

        if not isinstance(
            self.fiscal_year,
            FiscalYear,
        ):
            raise TypeError(
                "fiscal_year must be a FiscalYear"
            )

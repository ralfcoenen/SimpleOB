"""Startpunkt der OpenBilanz-Anwendung."""

from datetime import date
from uuid import uuid4

from openbilanz.core.context import ApplicationContext
from openbilanz.domain.company import Company
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.ui.main_window import MainWindow


def main() -> None:
    """Startet OpenBilanz."""

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    context = ApplicationContext(
        company=company,
        fiscal_year=fiscal_year,
    )

    window = MainWindow(
        context=context,
    )
    window.mainloop()


if __name__ == "__main__":
    main()

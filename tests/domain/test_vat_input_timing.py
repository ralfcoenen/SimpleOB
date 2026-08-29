"""Tests für die zeitliche Zuordnung des Vorsteuerabzugs."""

from datetime import date
from uuid import uuid4

import pytest

from openbilanz.domain.vat_input_timing import VatInputTiming


def test_uses_invoice_received_date_when_it_is_later() -> None:
    """Der Vorsteuerabzug wartet auf die später eingegangene Rechnung."""

    timing = VatInputTiming(
        booking_id=uuid4(),
        service_date=date(2026, 3, 28),
        invoice_received_date=date(2026, 4, 4),
    )

    assert timing.deductible_date == date(
        2026,
        4,
        4,
    )


def test_uses_service_date_when_it_is_later() -> None:
    """Der Vorsteuerabzug wartet auf die spätere Leistung."""

    timing = VatInputTiming(
        booking_id=uuid4(),
        service_date=date(2026, 4, 10),
        invoice_received_date=date(2026, 4, 2),
    )

    assert timing.deductible_date == date(
        2026,
        4,
        10,
    )


def test_rejects_invalid_dates() -> None:
    """Datumsfelder müssen echte date-Objekte sein."""

    with pytest.raises(
        TypeError,
        match="service_date must be a date",
    ):
        VatInputTiming(
            booking_id=uuid4(),
            service_date="2026-04-10",  # type: ignore[arg-type]
            invoice_received_date=date(2026, 4, 2),
        )

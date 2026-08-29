"""Tests für die Kleinunternehmerbeurteilung."""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

from openbilanz.domain.small_business_vat_revenue_event import (
    SmallBusinessVatRevenueEvent,
)
from openbilanz.domain.small_business_vat_status import (
    SmallBusinessVatStatus,
)
from openbilanz.services.small_business_vat_service import (
    SmallBusinessVatService,
)


def test_foundation_year_below_limit_is_applicable() -> None:
    """Im Gründungsjahr gilt die 25.000-Euro-Grenze."""

    revenue_service = Mock()
    company_id = uuid4()

    revenue_service.revenue_for_calendar_year.return_value = (
        Decimal("20000.00")
    )

    service = SmallBusinessVatService(
        revenue_service=revenue_service
    )

    result = service.assess(
        company_id=company_id,
        calendar_year=2026,
        foundation_year=2026,
    )

    assert result.previous_year_revenue is None
    assert result.current_year_revenue == Decimal("20000.00")
    assert result.applicable_at_year_start is True
    assert result.current_limit == Decimal("25000.00")
    assert result.status is SmallBusinessVatStatus.APPLICABLE


def test_foundation_year_above_limit_is_exceeded() -> None:
    """Eine Überschreitung im Gründungsjahr wird erkannt."""

    revenue_service = Mock()
    company_id = uuid4()

    revenue_service.revenue_for_calendar_year.return_value = (
        Decimal("25000.01")
    )

    service = SmallBusinessVatService(
        revenue_service=revenue_service
    )

    result = service.assess(
        company_id=company_id,
        calendar_year=2026,
        foundation_year=2026,
    )

    assert result.current_limit == Decimal("25000.00")
    assert result.status is (
        SmallBusinessVatStatus.LIMIT_EXCEEDED
    )


def test_existing_company_below_previous_year_limit_is_applicable() -> None:
    """Ein zulässiges Vorjahr eröffnet § 19 im Folgejahr."""

    revenue_service = Mock()
    company_id = uuid4()

    revenue_service.revenue_for_calendar_year.side_effect = (
        lambda *, company_id, calendar_year: (
            Decimal("20000.00")
            if calendar_year == 2025
            else Decimal("50000.00")
        )
    )

    service = SmallBusinessVatService(
        revenue_service=revenue_service
    )

    result = service.assess(
        company_id=company_id,
        calendar_year=2026,
        foundation_year=2025,
    )

    assert result.previous_year_revenue == Decimal("20000.00")
    assert result.current_year_revenue == Decimal("50000.00")
    assert result.applicable_at_year_start is True
    assert result.current_limit == Decimal("100000.00")
    assert result.status is SmallBusinessVatStatus.APPLICABLE


def test_existing_company_above_previous_year_limit_is_not_applicable() -> None:
    """Ein zu hoher Vorjahresumsatz schließt § 19 aus."""

    revenue_service = Mock()
    company_id = uuid4()

    revenue_service.revenue_for_calendar_year.side_effect = (
        lambda *, company_id, calendar_year: (
            Decimal("25000.01")
            if calendar_year == 2025
            else Decimal("1000.00")
        )
    )

    service = SmallBusinessVatService(
        revenue_service=revenue_service
    )

    result = service.assess(
        company_id=company_id,
        calendar_year=2026,
        foundation_year=2024,
    )

    assert result.previous_year_revenue == Decimal("25000.01")
    assert result.applicable_at_year_start is False
    assert result.status is (
        SmallBusinessVatStatus.NOT_APPLICABLE
    )

def test_limit_exceedance_returns_none_at_exact_limit() -> None:
    """Der exakte Grenzbetrag ist noch keine Überschreitung."""

    revenue_service = Mock()
    company_id = uuid4()

    event = SmallBusinessVatRevenueEvent(
        event_date=date(2026, 8, 1),
        amount=Decimal("100000.00"),
        revenue_id=uuid4(),
        booking_id=uuid4(),
    )

    revenue_service.revenue_events_for_calendar_year.return_value = (
        event,
    )

    service = SmallBusinessVatService(
        revenue_service=revenue_service
    )

    result = service.limit_exceedance(
        company_id=company_id,
        calendar_year=2026,
        foundation_year=2025,
    )

    assert result is None

def test_detects_current_year_limit_exceedance() -> None:
    """Der erste Umsatz über 100.000 Euro wird erkannt."""

    revenue_service = Mock()
    company_id = uuid4()

    first_event = SmallBusinessVatRevenueEvent(
        event_date=date(2026, 6, 1),
        amount=Decimal("99500.00"),
        revenue_id=uuid4(),
        booking_id=uuid4(),
    )

    second_event = SmallBusinessVatRevenueEvent(
        event_date=date(2026, 8, 1),
        amount=Decimal("1000.00"),
        revenue_id=uuid4(),
        booking_id=uuid4(),
    )

    revenue_service.revenue_events_for_calendar_year.return_value = (
        first_event,
        second_event,
    )

    service = SmallBusinessVatService(
        revenue_service=revenue_service
    )

    result = service.limit_exceedance(
        company_id=company_id,
        calendar_year=2026,
        foundation_year=2025,
    )

    assert result is not None
    assert result.limit == Decimal("100000.00")
    assert result.revenue_before == Decimal("99500.00")
    assert result.revenue_after == Decimal("100500.00")
    assert result.event is second_event

def test_detects_foundation_year_limit_exceedance() -> None:
    """Im Gründungsjahr gilt die 25.000-Euro-Grenze."""

    revenue_service = Mock()
    company_id = uuid4()

    first_event = SmallBusinessVatRevenueEvent(
        event_date=date(2026, 3, 1),
        amount=Decimal("24000.00"),
        revenue_id=uuid4(),
        booking_id=uuid4(),
    )

    second_event = SmallBusinessVatRevenueEvent(
        event_date=date(2026, 5, 1),
        amount=Decimal("1500.00"),
        revenue_id=uuid4(),
        booking_id=uuid4(),
    )

    revenue_service.revenue_events_for_calendar_year.return_value = (
        first_event,
        second_event,
    )

    service = SmallBusinessVatService(
        revenue_service=revenue_service
    )

    result = service.limit_exceedance(
        company_id=company_id,
        calendar_year=2026,
        foundation_year=2026,
    )

    assert result is not None
    assert result.limit == Decimal("25000.00")
    assert result.revenue_before == Decimal("24000.00")
    assert result.revenue_after == Decimal("25500.00")
    assert result.event is second_event

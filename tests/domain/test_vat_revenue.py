"""Tests für umsatzsteuerliche Ausgangsumsätze."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from openbilanz.domain.vat_payment_allocation import (
    VatPaymentAllocation,
)
from openbilanz.domain.vat_payment_kind import VatPaymentKind
from openbilanz.domain.vat_revenue import VatRevenue
from openbilanz.domain.vat_revenue_kind import VatRevenueKind


def test_creates_vat_revenue() -> None:
    revenue = VatRevenue(
        booking_id=uuid4(),
        gross_amount=Decimal("1000.00"),
        revenue_kind=VatRevenueKind.NORMAL,
        payment_kind=VatPaymentKind.RECEIVABLE,
        service_date=date(2026, 8, 29),
    )

    assert revenue.gross_amount == Decimal("1000.00")
    assert revenue.revenue_kind is VatRevenueKind.NORMAL
    assert revenue.payment_kind is VatPaymentKind.RECEIVABLE


def test_rejects_zero_vat_revenue_amount() -> None:
    with pytest.raises(
        ValueError,
        match="gross_amount must be greater than 0.00",
    ):
        VatRevenue(
            booking_id=uuid4(),
            gross_amount=Decimal("0.00"),
            revenue_kind=VatRevenueKind.NORMAL,
            payment_kind=VatPaymentKind.IMMEDIATE,
            service_date=date(2026, 8, 29),
        )


def test_creates_vat_payment_allocation() -> None:
    allocation = VatPaymentAllocation(
        revenue_id=uuid4(),
        payment_booking_id=uuid4(),
        amount=Decimal("600.00"),
    )

    assert allocation.amount == Decimal("600.00")


def test_rejects_zero_payment_allocation_amount() -> None:
    with pytest.raises(
        ValueError,
        match="amount must be greater than 0.00",
    ):
        VatPaymentAllocation(
            revenue_id=uuid4(),
            payment_booking_id=uuid4(),
            amount=Decimal("0.00"),
        )

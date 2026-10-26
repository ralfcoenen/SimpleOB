from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from PySide6.QtWidgets import QApplication

from simpleob.domain.open_item_payment import (
    OpenInvoiceSummary,
    PaymentDirection,
)
from simpleob.domain.payment_allocation_correction import (
    CorrectablePaymentAllocation,
)
from simpleob.ui_qt.payment_allocation_correction_dialog import (
    PaymentAllocationCorrectionDialog,
)


class _CorrectionService:
    def __init__(self, allocation, target):
        self.allocation = allocation
        self.target = target

    def list_correctable_allocations(self, _company_id):
        return (self.allocation,)

    def list_open_targets(self, *, company_id, partner_id, direction):
        assert company_id == self.allocation.company_id
        assert partner_id == self.allocation.partner_id
        assert direction is self.allocation.direction
        return (self.target,)


@pytest.mark.parametrize(
    ("direction", "document_number", "target_number", "expected_label"),
    (
        (
            PaymentDirection.CUSTOMER_RECEIPT,
            "AR-2026-0001",
            "AR-2026-0002",
            "Kundenzahlung",
        ),
        (
            PaymentDirection.SUPPLIER_PAYMENT,
            "AP-2026-0001",
            "AP-2026-0002",
            "Lieferantenzahlung",
        ),
    ),
)
def test_correction_dialog_shows_readable_payment_and_invoice_references(
    direction,
    document_number,
    target_number,
    expected_label,
):
    app = QApplication.instance() or QApplication([])
    company_id = uuid4()
    partner_id = uuid4()
    payment_id = uuid4()
    event_id = uuid4()
    source_open_item_id = uuid4()
    target_open_item_id = uuid4()
    allocation = CorrectablePaymentAllocation(
        company_id=company_id,
        partner_id=partner_id,
        partner_name="Holger Grosser",
        payment_id=payment_id,
        payment_date=date(2026, 4, 15),
        payment_booking_date=date(2026, 4, 16),
        payment_amount=Decimal("149.00"),
        payment_voucher_no="BANK-042",
        recorded_at=datetime(2026, 4, 16, 15, 30, 12, tzinfo=timezone.utc),
        direction=direction,
        original_event_id=event_id,
        original_amount=Decimal("30.00"),
        corrected_amount=Decimal("0.00"),
        correctable_amount=Decimal("30.00"),
        source_open_item_id=source_open_item_id,
        source_document_number=document_number,
    )
    target = OpenInvoiceSummary(
        company_id=company_id,
        partner_id=partner_id,
        open_item_id=target_open_item_id,
        direction=direction,
        document_number=target_number,
        document_date=date(2026, 4, 10),
        due_date=date(2026, 5, 10),
        original_amount=Decimal("119.00"),
        open_amount=Decimal("119.00"),
        partner_name="Holger Grosser",
    )
    dialog = PaymentAllocationCorrectionDialog(
        None,
        company_id=company_id,
        fiscal_year=None,
        service=_CorrectionService(allocation, target),
    )

    source_label = dialog._source.currentText()
    assert expected_label in source_label
    assert "Holger Grosser" in source_label
    assert document_number in source_label
    assert "15.04.2026" in source_label
    assert "16.04.2026" in source_label
    assert "30.00 EUR" in source_label
    assert "149.00 EUR" in source_label
    assert "BANK-042" in source_label
    assert str(payment_id) not in source_label
    assert str(event_id) not in source_label
    assert "Holger Grosser" in dialog._target.currentText()
    assert target_number in dialog._target.currentText()
    assert str(target_open_item_id) not in dialog._target.currentText()

    dialog.close()
    app.processEvents()

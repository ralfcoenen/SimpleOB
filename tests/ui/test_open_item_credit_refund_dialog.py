from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from simpleob.domain.open_item_offset import CreditOffsetSummary, OffsetDirection
from simpleob.ui_qt.open_item_credit_refund_dialog import (
    OpenItemCreditRefundDialog,
)


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


class PartnerRepository:
    def __init__(self):
        self.customer = SimpleNamespace(
            partner_id=uuid4(), name="Kunden GmbH", is_customer=True, is_supplier=False
        )
        self.supplier = SimpleNamespace(
            partner_id=uuid4(), name="Lieferanten GmbH", is_customer=False, is_supplier=True
        )
        self.calls = []

    def list_for_company(self, _company_id, *, customers_only=False, suppliers_only=False):
        self.calls.append((customers_only, suppliers_only))
        if customers_only:
            return (self.customer,)
        if suppliers_only:
            return (self.supplier,)
        return (self.customer, self.supplier)


class OffsetService:
    def __init__(self, partners):
        self.partners = partners
        self.calls = []
        self.credits = {
            (partners.customer.partner_id, OffsetDirection.CUSTOMER): (
                CreditOffsetSummary(
                    company_id=uuid4(), partner_id=partners.customer.partner_id,
                    open_item_id=uuid4(), direction=OffsetDirection.CUSTOMER,
                    document_number="CN-2026-01", original_amount=Decimal("100.00"),
                    available_amount=Decimal("100.00"), account_number="2400",
                ),
                CreditOffsetSummary(
                    company_id=uuid4(), partner_id=partners.customer.partner_id,
                    open_item_id=uuid4(), direction=OffsetDirection.CUSTOMER,
                    document_number="Storno AR-2026-02", original_amount=Decimal("50.00"),
                    available_amount=Decimal("25.00"), account_number="2400",
                ),
            ),
            (partners.supplier.partner_id, OffsetDirection.SUPPLIER): (
                CreditOffsetSummary(
                    company_id=uuid4(), partner_id=partners.supplier.partner_id,
                    open_item_id=uuid4(), direction=OffsetDirection.SUPPLIER,
                    document_number="CN-2026-03", original_amount=Decimal("75.00"),
                    available_amount=Decimal("75.00"), account_number="1300",
                ),
            ),
        }

    def list_open_credits(self, *, company_id, partner_id, direction):
        self.calls.append((company_id, partner_id, direction))
        return self.credits.get((partner_id, direction), ())


class RefundService:
    def __init__(self):
        self.calls = []
        self.cash_bank_account_numbers_result = frozenset({"1000", "1600"})

    def cash_bank_account_numbers(self, _company_id):
        return self.cash_bank_account_numbers_result

    def post_refund(self, **kwargs):
        self.calls.append(kwargs)


def _dialog(partners, offsets, service, account_objects):
    company_id = uuid4()
    dialog = OpenItemCreditRefundDialog(
        None,
        company_id=company_id,
        fiscal_year=SimpleNamespace(),
        service=service,
        offset_service=offsets,
        partner_repository=partners,
        accounts=account_objects,
    )
    return company_id, dialog


def test_direction_partner_credit_origins_and_active_bank_cash_accounts(app):
    partners = PartnerRepository()
    offsets = OffsetService(partners)
    service = RefundService()
    accounts = (
        SimpleNamespace(number="1000", name="Bank", is_active=True),
        SimpleNamespace(number="1600", name="Kasse", is_active=True),
        SimpleNamespace(number="1800", name="Inaktiv", is_active=False),
        SimpleNamespace(number="8400", name="Nicht Finanzkonto", is_active=True),
    )
    _company_id, dialog = _dialog(partners, offsets, service, accounts)

    assert dialog._partner_box.count() == 1
    assert dialog._partner_box.currentText() == "Kunden GmbH"
    assert dialog._credit_box.count() == 2
    assert "Gutschrift CN-2026-01" in dialog._credit_box.itemText(0)
    assert "Rechnungsstorno AR-2026-02" in dialog._credit_box.itemText(1)
    assert [dialog._account_box.itemData(i) for i in range(dialog._account_box.count())] == [
        "1000", "1600"
    ]

    dialog._direction_box.setCurrentIndex(1)
    assert dialog._partner_box.currentText() == "Lieferanten GmbH"
    assert dialog._credit_box.count() == 1
    assert "Gutschrift CN-2026-03" in dialog._credit_box.currentText()
    assert partners.calls[-1] == (False, True)
    dialog.close()


@pytest.mark.parametrize("amount", ("25,00", "100,00"), ids=("partial", "full"))
def test_partial_and_full_refund_pass_confirmed_values_to_service(
    app, monkeypatch, amount
):
    partners = PartnerRepository()
    offsets = OffsetService(partners)
    service = RefundService()
    accounts = (SimpleNamespace(number="1600", name="Kasse", is_active=True),)
    company_id, dialog = _dialog(partners, offsets, service, accounts)
    credit_index = 0 if amount == "100,00" else 1
    selected_credit = offsets.credits[(partners.customer.partner_id, OffsetDirection.CUSTOMER)][credit_index]
    dialog._credit_box.setCurrentIndex(credit_index)
    dialog._account_box.setCurrentIndex(0)
    dialog._amount.setText(amount)
    dialog._refund_date.setText("15.4.2026")
    dialog._booking_date.setText("16.4.2026")
    confirmations = []
    monkeypatch.setattr(
        "simpleob.ui_qt.open_item_credit_refund_dialog.QMessageBox.question",
        lambda *_args: confirmations.append(_args[2]) or QMessageBox.StandardButton.Yes,
    )
    monkeypatch.setattr(
        "simpleob.ui_qt.open_item_credit_refund_dialog.QMessageBox.critical",
        lambda *_args: pytest.fail("Gültige Rückerstattung wurde abgelehnt."),
    )

    dialog._post_refund()

    assert dialog.result() == dialog.DialogCode.Accepted
    assert len(service.calls) == 1
    call = service.calls[0]
    assert call["company_id"] == company_id
    assert call["partner_id"] == partners.customer.partner_id
    assert call["open_item_id"] == selected_credit.open_item_id
    assert call["direction"] is OffsetDirection.CUSTOMER
    assert call["amount"] == Decimal(amount.replace(",", "."))
    assert call["cash_bank_account_number"] == "1600"
    assert call["refund_date"] == date(2026, 4, 15)
    assert call["booking_date"] == date(2026, 4, 16)
    assert dialog._refund_date.text() == "15.04.2026"
    assert dialog._booking_date.text() == "16.04.2026"
    assert "Kundenguthaben auszahlen" in confirmations[0]
    expected_origin = (
        "Guthaben-OP: Gutschrift CN-2026-01"
        if credit_index == 0
        else "Guthaben-OP: Rechnungsstorno AR-2026-02"
    )
    assert expected_origin in confirmations[0]
    assert "Kasse" in confirmations[0]


def test_supplier_refund_uses_supplier_direction_and_bank_account(app, monkeypatch):
    partners = PartnerRepository()
    offsets = OffsetService(partners)
    service = RefundService()
    company_id, dialog = _dialog(
        partners,
        offsets,
        service,
        (SimpleNamespace(number="1000", name="Bank", is_active=True),),
    )
    dialog._direction_box.setCurrentIndex(1)
    dialog._amount.setText("75,00")
    monkeypatch.setattr(
        "simpleob.ui_qt.open_item_credit_refund_dialog.QMessageBox.question",
        lambda *_args: QMessageBox.StandardButton.Yes,
    )

    dialog._post_refund()

    assert len(service.calls) == 1
    assert service.calls[0]["company_id"] == company_id
    assert service.calls[0]["partner_id"] == partners.supplier.partner_id
    assert service.calls[0]["direction"] is OffsetDirection.SUPPLIER
    assert service.calls[0]["amount"] == Decimal("75.00")
    assert service.calls[0]["cash_bank_account_number"] == "1000"


@pytest.mark.parametrize("amount", ("0,00", "25,01"))
def test_nonpositive_or_excess_refund_is_rejected_before_confirmation(
    app, monkeypatch, amount
):
    partners = PartnerRepository()
    offsets = OffsetService(partners)
    service = RefundService()
    company_id, dialog = _dialog(
        partners,
        offsets,
        service,
        (SimpleNamespace(number="1000", name="Bank", is_active=True),),
    )
    dialog._credit_box.setCurrentIndex(1)
    dialog._amount.setText(amount)
    messages = []
    monkeypatch.setattr(
        "simpleob.ui_qt.open_item_credit_refund_dialog.QMessageBox.critical",
        lambda *_args: messages.append(_args[2]),
    )
    monkeypatch.setattr(
        "simpleob.ui_qt.open_item_credit_refund_dialog.QMessageBox.question",
        lambda *_args: pytest.fail("Unzulässiger Betrag darf nicht bestätigt werden."),
    )

    dialog._post_refund()

    assert service.calls == []
    assert messages
    if amount == "25,01":
        assert "übersteigt den verfügbaren Rest von 25,00 EUR" in messages[0]
    else:
        assert "größer als 0,00" in messages[0]
    dialog.close()

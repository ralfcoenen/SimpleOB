from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from PySide6.QtWidgets import QApplication, QMessageBox

from simpleob.date_input import GermanDateEdit
from simpleob.domain.open_item_payment import PaymentDirection
from simpleob.ui_qt.open_item_offset_dialog import OpenItemOffsetDialog
from simpleob.ui_qt.open_item_payment_dialog import OpenItemPaymentDialog


def _app():
    return QApplication.instance() or QApplication([])


def test_payment_dialog_uses_central_dates_and_passes_normalized_values(monkeypatch):
    app = _app()
    company_id, partner_id, open_item_id = uuid4(), uuid4(), uuid4()
    invoice = SimpleNamespace(
        direction=PaymentDirection.CUSTOMER_RECEIPT,
        partner_id=partner_id,
        partner_name="Kunden GmbH",
        open_item_id=open_item_id,
        document_number="AR-2026-001",
        document_date=date(2026, 1, 2),
        open_amount=Decimal("10.00"),
    )

    class Service:
        calls = []

        def list_open_invoices(self, _company_id):
            return (invoice,)

        def payment_account_numbers(self, _company_id):
            return ("1200",)

        def post_payment_allocations(self, **kwargs):
            self.calls.append(kwargs)

    service = Service()
    dialog = OpenItemPaymentDialog(
        None,
        company_id=company_id,
        fiscal_year=None,
        service=service,
        accounts=(SimpleNamespace(number="1200", name="Bank", is_active=True),),
    )
    assert isinstance(dialog._payment_date, GermanDateEdit)
    assert isinstance(dialog._booking_date, GermanDateEdit)
    dialog._amount.setText("10,00")
    dialog._allocations_table.item(0, 2).setText("10,00")
    dialog._payment_date.setText("1.2.2026")
    dialog._booking_date.setText("2.2.2026")
    monkeypatch.setattr(
        "simpleob.ui_qt.open_item_payment_dialog.QMessageBox.question",
        lambda *_args: QMessageBox.StandardButton.Yes,
    )
    monkeypatch.setattr(
        "simpleob.ui_qt.open_item_payment_dialog.QMessageBox.critical",
        lambda *_args: (_ for _ in ()).throw(AssertionError("Zahlung abgewiesen")),
    )

    dialog._post_payment()

    assert service.calls[0]["payment_date"] == date(2026, 2, 1)
    assert service.calls[0]["booking_date"] == date(2026, 2, 2)
    assert dialog._payment_date.text() == "01.02.2026"
    assert dialog._booking_date.text() == "02.02.2026"
    dialog.close()
    app.processEvents()


def test_offset_dialog_uses_central_dates_and_passes_normalized_values(monkeypatch):
    app = _app()
    company_id, partner_id = uuid4(), uuid4()
    invoice_id, credit_id = uuid4(), uuid4()
    invoice = SimpleNamespace(
        open_item_id=invoice_id,
        document_number="AR-2026-001",
        open_amount=Decimal("20.00"),
    )
    credit = SimpleNamespace(
        open_item_id=credit_id,
        document_number="CN-2026-001",
        available_amount=Decimal("20.00"),
    )

    class PartnerRepository:
        def list_for_company(self, *_args, **_kwargs):
            return (SimpleNamespace(partner_id=partner_id, name="Kunden GmbH"),)

    class Service:
        calls = []

        def list_open_invoices(self, **_kwargs):
            return (invoice,)

        def list_open_credits(self, **_kwargs):
            return (credit,)

        def post_offset(self, **kwargs):
            self.calls.append(kwargs)

    service = Service()
    dialog = OpenItemOffsetDialog(
        None,
        company_id=company_id,
        fiscal_year=None,
        service=service,
        partner_repository=PartnerRepository(),
    )
    assert isinstance(dialog._settlement_date, GermanDateEdit)
    assert isinstance(dialog._booking_date, GermanDateEdit)
    dialog._amount.setText("10,00")
    dialog._settlement_date.setText("1.2.2026")
    dialog._booking_date.setText("2.2.2026")
    monkeypatch.setattr(
        "simpleob.ui_qt.open_item_offset_dialog.QMessageBox.question",
        lambda *_args: QMessageBox.StandardButton.Yes,
    )
    monkeypatch.setattr(
        "simpleob.ui_qt.open_item_offset_dialog.QMessageBox.critical",
        lambda *_args: (_ for _ in ()).throw(AssertionError("Verrechnung abgewiesen")),
    )

    dialog._post_offset()

    assert service.calls[0]["settlement_date"] == date(2026, 2, 1)
    assert service.calls[0]["booking_date"] == date(2026, 2, 2)
    assert dialog._settlement_date.text() == "01.02.2026"
    assert dialog._booking_date.text() == "02.02.2026"
    dialog.close()
    app.processEvents()

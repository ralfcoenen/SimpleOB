from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from simpleob.domain.open_item_credit_refund_reversal import (
    OpenItemCreditRefundReversalCandidate,
)
from simpleob.domain.open_item_offset import OffsetDirection
from simpleob.ui_qt.main_window import MainWindow
from simpleob.ui_qt.open_item_credit_refund_reversal_dialog import (
    OpenItemCreditRefundReversalDialog,
)


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


class ReversalService:
    def __init__(self, candidates):
        self.candidates = tuple(candidates)
        self.list_calls = []
        self.calls = []

    def list_candidates(self, *, company_id, fiscal_year):
        self.list_calls.append((company_id, fiscal_year))
        return self.candidates

    def reverse_refund(self, **kwargs):
        self.calls.append(kwargs)


def _candidate(
    direction,
    *,
    reversal_count=0,
    booking_date=date(2026, 4, 13),
    journal_reversal_booking_date=date(2026, 4, 14),
):
    refund_id = uuid4()
    reversal_id = uuid4() if reversal_count == 1 else None
    return OpenItemCreditRefundReversalCandidate(
        refund_id=refund_id,
        partner_id=uuid4(),
        partner_name=(
            "Kunden GmbH"
            if direction is OffsetDirection.CUSTOMER
            else "Lieferanten GmbH"
        ),
        direction=direction,
        amount=Decimal("42.50"),
        refund_date=date(2026, 4, 12),
        booking_date=booking_date,
        original_booking_id=uuid4(),
        original_voucher_no="RB-2026-0042",
        journal_reversal_count=reversal_count,
        journal_reversal_booking_id=reversal_id,
        journal_reversal_booking_date=(
            journal_reversal_booking_date if reversal_id else None
        ),
    )


@pytest.mark.parametrize(
    ("direction", "reversal_count", "booking_date", "message"),
    [
        (
            OffsetDirection.CUSTOMER,
            0,
            date(2026, 4, 15),
            "Es wird eine Hauptbuchgegenbuchung",
        ),
        (
            OffsetDirection.SUPPLIER,
            1,
            date(2026, 4, 14),
            "ausschließlich die fehlende OP-Rücknahme",
        ),
    ],
)
def test_selection_displays_case_and_calls_service_only_after_confirmation(
    app, monkeypatch, direction, reversal_count, booking_date, message
):
    candidate = _candidate(direction, reversal_count=reversal_count)
    service = ReversalService((candidate,))
    company_id, fiscal_year = uuid4(), SimpleNamespace()
    dialog = OpenItemCreditRefundReversalDialog(
        None,
        company_id=company_id,
        fiscal_year=fiscal_year,
        service=service,
    )
    if direction is OffsetDirection.SUPPLIER:
        dialog._direction_box.setCurrentIndex(1)
    if reversal_count == 0:
        dialog._return_booking_date.setText("15.4.2026")

    assert dialog._partner_box.currentText() == candidate.partner_name
    assert dialog._refund_box.count() == 1
    assert dialog._refund_box.currentText() == "13.04.2026 · 42,50 €"
    assert dialog._refund_box.currentData() == str(candidate.refund_id)
    assert str(candidate.refund_id) not in dialog._refund_box.currentText()
    assert str(candidate.original_booking_id) not in dialog._refund_box.currentText()
    assert dialog._amount.text() == "42,50 EUR"
    assert dialog._refund_booking_date.text() == "13.04.2026"
    assert dialog._scenario.wordWrap()
    assert dialog._reason.minimumWidth() >= 400
    assert message in dialog._scenario.text()
    if reversal_count == 1:
        assert dialog._return_booking_date.isReadOnly()
        assert dialog._return_booking_date.text() == "14.04.2026"
        assert str(candidate.journal_reversal_booking_id) not in dialog._existing_reversal.text()
    else:
        assert not dialog._return_booking_date.isReadOnly()

    dialog._reason.setText("Versehentlich gebucht")
    confirmations = []
    monkeypatch.setattr(
        "simpleob.ui_qt.open_item_credit_refund_reversal_dialog.QMessageBox.question",
        lambda *_args: confirmations.append(_args[2]) or QMessageBox.StandardButton.Yes,
    )
    monkeypatch.setattr(
        "simpleob.ui_qt.open_item_credit_refund_reversal_dialog.QMessageBox.critical",
        lambda *_args: pytest.fail("Gültige Rücknahme wurde abgewiesen."),
    )

    dialog._reverse()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert len(service.calls) == 1
    assert service.calls[0] == {
        "company_id": company_id,
        "fiscal_year": fiscal_year,
        "refund_id": candidate.refund_id,
        "reason": "Versehentlich gebucht",
        "booking_date": booking_date,
    }
    assert dialog._return_booking_date.text() == (
        "15.04.2026" if reversal_count == 0 else "14.04.2026"
    )
    assert (
        "Hauptbuchgegenbuchung"
        if reversal_count == 0
        else "Es wird nur die OP-Rücknahme ergänzt"
    ) in confirmations[0]


def test_reason_is_required_and_cancel_does_not_call_service(app, monkeypatch):
    candidate = _candidate(OffsetDirection.CUSTOMER)
    service = ReversalService((candidate,))
    dialog = OpenItemCreditRefundReversalDialog(
        None,
        company_id=uuid4(),
        fiscal_year=SimpleNamespace(),
        service=service,
    )
    assert not dialog._ok_button.isEnabled()
    dialog._reason.setText("   ")
    assert not dialog._ok_button.isEnabled()

    monkeypatch.setattr(
        "simpleob.ui_qt.open_item_credit_refund_reversal_dialog.QMessageBox.question",
        lambda *_args: QMessageBox.StandardButton.No,
    )
    dialog._reason.setText("Irrtum")
    assert dialog._ok_button.isEnabled()
    dialog._reverse()
    assert service.calls == []
    assert dialog.result() != QDialog.DialogCode.Accepted


@pytest.mark.parametrize("existing_reversal", [False, True])
def test_booking_date_before_refund_is_visible_and_cannot_be_confirmed(
    app, monkeypatch, existing_reversal
):
    today = date.today()
    original_booking_date = date.fromordinal(today.toordinal() + 7)
    candidate = _candidate(
        OffsetDirection.CUSTOMER,
        reversal_count=int(existing_reversal),
        booking_date=original_booking_date,
        journal_reversal_booking_date=today,
    )
    service = ReversalService((candidate,))
    dialog = OpenItemCreditRefundReversalDialog(
        None,
        company_id=uuid4(),
        fiscal_year=SimpleNamespace(),
        service=service,
    )
    if not existing_reversal:
        dialog._return_booking_date.setText(today.strftime("%d.%m.%Y"))
    dialog._reason.setText("Irrtum")

    assert "nicht vor" in dialog._date_error.text()
    assert not dialog._ok_button.isEnabled()
    confirmations = []
    errors = []
    monkeypatch.setattr(
        "simpleob.ui_qt.open_item_credit_refund_reversal_dialog.QMessageBox.question",
        lambda *_args: confirmations.append(True),
    )
    monkeypatch.setattr(
        "simpleob.ui_qt.open_item_credit_refund_reversal_dialog.QMessageBox.critical",
        lambda *_args: errors.append(_args[2]),
    )

    dialog._reverse()

    assert confirmations == []
    assert errors and "nicht vor" in errors[0]
    assert service.calls == []


def test_dialog_reports_service_validation_error(app, monkeypatch):
    candidate = _candidate(OffsetDirection.CUSTOMER)

    class FailingService(ReversalService):
        def reverse_refund(self, **kwargs):
            raise ValueError("Das Geschäftsjahr ist nicht offen.")

    service = FailingService((candidate,))
    dialog = OpenItemCreditRefundReversalDialog(
        None,
        company_id=uuid4(),
        fiscal_year=SimpleNamespace(),
        service=service,
    )
    dialog._reason.setText("Irrtum")
    monkeypatch.setattr(
        "simpleob.ui_qt.open_item_credit_refund_reversal_dialog.QMessageBox.question",
        lambda *_args: QMessageBox.StandardButton.Yes,
    )
    errors = []
    monkeypatch.setattr(
        "simpleob.ui_qt.open_item_credit_refund_reversal_dialog.QMessageBox.critical",
        lambda *_args: errors.append(_args[2]),
    )

    dialog._reverse()

    assert errors == ["Das Geschäftsjahr ist nicht offen."]
    assert dialog.result() != QDialog.DialogCode.Accepted


def test_main_window_opens_reversal_dialog_and_refreshes_after_success(monkeypatch):
    calls = []

    class Dialog:
        def __init__(self, parent, **kwargs):
            calls.append(("dialog", parent, kwargs))

        def exec(self):
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(
        "simpleob.ui_qt.main_window.OpenItemCreditRefundReversalDialog", Dialog
    )
    service = ReversalService(())
    company_id, fiscal_year = uuid4(), SimpleNamespace()
    window = SimpleNamespace(
        _open_item_credit_refund_reversal_service=service,
        _workspace=SimpleNamespace(is_closed=False),
        _context=SimpleNamespace(
            company=SimpleNamespace(company_id=company_id),
            fiscal_year=fiscal_year,
        ),
        _refresh_after_credit_refund=lambda: calls.append(("refresh",)),
    )

    MainWindow._open_credit_refund_reversal_dialog(window)

    assert calls[0][0:2] == ("dialog", window)
    assert calls[0][2] == {
        "company_id": company_id,
        "fiscal_year": fiscal_year,
        "service": service,
    }
    assert calls[1] == ("refresh",)

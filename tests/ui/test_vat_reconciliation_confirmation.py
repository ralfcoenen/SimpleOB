from datetime import date
from decimal import Decimal

from PySide6.QtWidgets import QMessageBox

from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.services.vat_reconciliation_service import (
    VatReconciliationProposal,
)
from simpleob.ui_qt import main_window


def _proposal() -> VatReconciliationProposal:
    fiscal_year = FiscalYear(date(2026, 1, 1), date(2026, 12, 31))
    booking = Booking(
        booking_date=fiscal_year.end_date,
        description="Umsatzsteuerverrechnung Konto 1771 zum Jahresabschluss",
        lines=(
            BookingLine("3840", EntrySide.CREDIT, Decimal("100.00")),
            BookingLine("1771", EntrySide.DEBIT, Decimal("100.00")),
        ),
    )
    return VatReconciliationProposal(
        fiscal_year=fiscal_year,
        account_balances=(),
        existing_clearing_balance=Decimal("0.00"),
        resulting_clearing_balance=Decimal("-100.00"),
        bookings=(booking,),
        snapshot=("unchanged",),
    )


class _Workspace:
    is_closed = False

    def __init__(self) -> None:
        self.confirmed = []

    def build_vat_reconciliation_proposal(self, *, chart_of_accounts):
        return _proposal()

    def confirm_vat_reconciliation(
        self,
        *,
        proposal,
        chart_of_accounts,
        confirmed,
    ):
        self.confirmed.append(confirmed)
        return proposal.bookings


class _Window:
    def __init__(self) -> None:
        self._workspace = _Workspace()
        self._chart_of_accounts = object()
        self._vat_reconciliation_proposal_text = (
            main_window.MainWindow._vat_reconciliation_proposal_text
        )

    def _refresh_journal(self) -> None:
        pass

    def _refresh_balance_sheet(self) -> None:
        pass

    def _refresh_closing(self) -> None:
        pass


def test_declining_vat_proposal_does_not_book(monkeypatch) -> None:
    window = _Window()
    monkeypatch.setattr(
        main_window.QMessageBox,
        "question",
        lambda *args: QMessageBox.StandardButton.No,
    )

    main_window.MainWindow._propose_vat_reconciliation(window)

    assert window._workspace.confirmed == []


def test_accepting_vat_proposal_calls_persistence_with_confirmation(
    monkeypatch,
) -> None:
    window = _Window()
    confirmation_texts = []

    def confirm_question(*args):
        confirmation_texts.append(args[2])
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(
        main_window.QMessageBox,
        "question",
        confirm_question,
    )
    monkeypatch.setattr(
        main_window.QMessageBox,
        "information",
        lambda *args: None,
    )

    main_window.MainWindow._propose_vat_reconciliation(window)

    assert window._workspace.confirmed == [True]
    assert len(confirmation_texts) == 1
    assert "ausschließlich vorhandene Hauptbuchsalden" in confirmation_texts[0]
    assert "sachliche und zeitliche Zuordnung" in confirmation_texts[0]
    assert "Vorauszahlungen und Erstattungen" in confirmation_texts[0]

from datetime import date
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QMessageBox

from simpleob.domain.accounting_account_roles import AccountingAccountRoles
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.vat_accounts import VatAccounts
from simpleob.services.vat_reconciliation_service import (
    VatAccountBalance,
    VatReconciliationProposal,
)
from simpleob.ui_qt import main_window
from simpleob.ui_qt.vat_reconciliation_preview_dialog import (
    VatReconciliationPreviewDialog,
)

_APP = QApplication.instance() or QApplication([])


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
        account_balances=(
            VatAccountBalance(
                account_number="3840",
                account_name="Umsatzsteuer laufendes Jahr",
                debit_balance=Decimal("0.00"),
                credit_balance=Decimal("100.00"),
                opening_balance=Decimal("0.00"),
            ),
            VatAccountBalance(
                account_number="1771",
                account_name="Umsatzsteuer 7 %",
                debit_balance=Decimal("100.00"),
                credit_balance=Decimal("0.00"),
                opening_balance=Decimal("0.00"),
            ),
        ),
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

    def load_account_configuration(self):
        return (
            None,
            None,
            AccountingAccountRoles(
                cash_accounts=frozenset(),
                bank_accounts=frozenset(),
                general_rate_sales_accounts=frozenset(),
                vat_advance_payments=frozenset({"3820"}),
                vat_current_year=frozenset({"3840"}),
                vat_prior_year_receivables=frozenset({"1422"}),
                vat_prior_year_payables=frozenset({"3841"}),
            ),
        )

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

    def _refresh_journal(self) -> None:
        pass

    def _refresh_balance_sheet(self) -> None:
        pass

    def _refresh_closing(self) -> None:
        pass


class _ClosingWorkspace(_Workspace):
    def __init__(self, *, balances=()) -> None:
        super().__init__()
        from simpleob.accounting.ledger import Ledger

        self.ledger = Ledger()
        for account_number, side, amount in balances:
            if side == "debit":
                self.ledger.post(account_number, "1000", amount)
            else:
                self.ledger.post("1000", account_number, amount)
        self.closed = []

    def load_account_configuration(self):
        _controls, _vat_accounts, roles = super().load_account_configuration()
        return (
            None,
            VatAccounts(
                input_tax_7="1575",
                input_tax_19="1571",
                output_tax_7="1775",
                output_tax_19="1771",
            ),
            roles,
        )

    def close_fiscal_year(self, **kwargs):
        self.closed.append(kwargs)
        return type("Result", (), {"net_income": Decimal("0.00")})()


class _FakeMessageBox:
    Icon = QMessageBox.Icon
    ButtonRole = QMessageBox.ButtonRole
    StandardButton = QMessageBox.StandardButton
    choice = "Abbrechen"
    choices = {}
    instances = []
    question_calls = 0
    question_answer = QMessageBox.StandardButton.No

    def __init__(self, parent=None) -> None:
        self.buttons = []
        self.informative_text = ""
        self.__class__.instances.append(self)

    def setIcon(self, icon) -> None:
        self.icon = icon

    def setWindowTitle(self, title) -> None:
        self.title = title

    def setText(self, text) -> None:
        self.text = text

    def setInformativeText(self, text) -> None:
        self.informative_text = text

    def addButton(self, label, role):
        button = type("Button", (), {"text": label})()
        self.buttons.append(button)
        return button

    def setDefaultButton(self, button) -> None:
        self.default_button = button

    def exec(self) -> int:
        return 0

    def clickedButton(self):
        choice = self.__class__.choices.get(self.title, self.choice)
        return next(
            button for button in self.buttons
            if button.text == choice
        )

    @classmethod
    def question(cls, *args):
        cls.question_calls += 1
        return cls.question_answer

    @classmethod
    def critical(cls, *args):
        pass

    @classmethod
    def information(cls, *args):
        pass


class _ClosingWindow:
    def __init__(self, *, balances=()) -> None:
        self._workspace = _ClosingWorkspace(balances=balances)
        self._chart_of_accounts = type(
            "Chart",
            (),
            {"account": lambda self, number: type(
                "Account", (), {"name": f"Konto {number}"}
            )()},
        )()
        self._current_income_statement = object()
        self._proposed = False
        self._closing_frame = type(
            "ClosingFrame",
            (),
            {
                "update_net_income": lambda self, amount: None,
                "mark_closed": lambda self: None,
            },
        )()

    def _propose_vat_reconciliation(self) -> None:
        self._proposed = True

    def _unreconciled_vat_source_balances(self):
        return main_window.MainWindow._unreconciled_vat_source_balances(self)

    def _refresh_after_closing(self):
        pass


def test_declining_vat_proposal_does_not_book(monkeypatch) -> None:
    window = _Window()
    monkeypatch.setattr(
        main_window,
        "VatReconciliationPreviewDialog",
        lambda *args, **kwargs: type(
            "Dialog", (), {"exec": lambda self: QDialog.DialogCode.Rejected}
        )(),
    )
    monkeypatch.setattr(
        main_window.QMessageBox,
        "warning",
        lambda *args: None,
    )

    main_window.MainWindow._propose_vat_reconciliation(window)

    assert window._workspace.confirmed == []


def test_accepting_vat_proposal_calls_persistence_with_confirmation(
    monkeypatch,
) -> None:
    window = _Window()
    monkeypatch.setattr(
        main_window,
        "VatReconciliationPreviewDialog",
        lambda *args, **kwargs: type(
            "Dialog", (), {"exec": lambda self: QDialog.DialogCode.Accepted}
        )(),
    )
    monkeypatch.setattr(
        main_window.QMessageBox,
        "information",
        lambda *args: None,
    )

    main_window.MainWindow._propose_vat_reconciliation(window)

    assert window._workspace.confirmed == [True]


def test_preview_dialog_shows_tables_result_and_responsibility_hint() -> None:
    dialog = VatReconciliationPreviewDialog(
        None,
        proposal=_proposal(),
        clearing_account_number="3840",
    )
    try:
        assert dialog.windowTitle() == "Umsatzsteuerverrechnung · Vorschau"
        assert dialog.findChild(QLabel, "vatReconciliationHeading").text() == (
            "Umsatzsteuerverrechnung"
        )
        assert (
            "Geschäftsjahr 01.01.2026 – 31.12.2026"
            in dialog.findChild(QLabel, "vatReconciliationFiscalYear").text()
        )
        assert dialog.account_table.rowCount() == 2
        assert dialog.account_table.item(0, 0).text() == "3840"
        assert dialog.account_table.item(0, 2).text() == "0,00 €"
        assert dialog.account_table.item(0, 3).text() == "100,00 €"
        assert (
            dialog.account_table.item(0, 2).textAlignment()
            & Qt.AlignmentFlag.AlignRight
        )
        assert dialog.booking_table.rowCount() == 1
        assert dialog.booking_table.item(0, 0).text().startswith("1771 ·")
        assert dialog.booking_table.item(0, 1).text().startswith("3840 ·")
        assert dialog.booking_table.item(0, 2).text() == "100,00 €"
        assert "Umsatzsteuerverbindlichkeit" in dialog.result_label.text()
        assert "sachliche und zeitliche Zuordnung" in dialog.hint_label.text()
        assert "Geschäftsjahr bleibt" in dialog.hint_label.text()
        assert "erneute Umsatzsteuerverrechnung erforderlich" in (
            dialog.hint_label.text()
        )
        assert not dialog.hint_label.isHidden()
        assert dialog.cancel_button.text() == "Abbrechen"
        assert dialog.apply_button.text() == "Buchungen übernehmen"

        dialog.apply_button.click()
        assert dialog.result() == QDialog.DialogCode.Accepted
    finally:
        dialog.close()


def test_preview_cancel_or_close_never_accepts_booking() -> None:
    proposal = _proposal()
    cancel_dialog = VatReconciliationPreviewDialog(
        None,
        proposal=proposal,
        clearing_account_number="3840",
    )
    cancel_dialog.cancel_button.click()
    assert cancel_dialog.result() == QDialog.DialogCode.Rejected

    close_dialog = VatReconciliationPreviewDialog(
        None,
        proposal=proposal,
        clearing_account_number="3840",
    )
    close_dialog.close()
    assert close_dialog.result() == QDialog.DialogCode.Rejected


def test_preview_without_bookings_disables_accept_button() -> None:
    proposal = _proposal()
    proposal = VatReconciliationProposal(
        fiscal_year=proposal.fiscal_year,
        account_balances=proposal.account_balances,
        existing_clearing_balance=Decimal("0.00"),
        resulting_clearing_balance=Decimal("0.00"),
        bookings=(),
        snapshot=proposal.snapshot,
    )
    dialog = VatReconciliationPreviewDialog(
        None,
        proposal=proposal,
        clearing_account_number="3840",
    )
    try:
        assert "Nullsaldo" in dialog.result_label.text()
        assert not dialog.apply_button.isEnabled()
    finally:
        dialog.close()


def _prepare_closing_warning(
    monkeypatch, *, choice="Abbrechen", choices=None
) -> None:
    _FakeMessageBox.instances.clear()
    _FakeMessageBox.question_calls = 0
    _FakeMessageBox.question_answer = QMessageBox.StandardButton.No
    _FakeMessageBox.choice = choice
    _FakeMessageBox.choices = choices or {}
    monkeypatch.setattr(main_window, "QMessageBox", _FakeMessageBox)


def test_closing_warns_for_remaining_vat_source_balances(monkeypatch) -> None:
    window = _ClosingWindow(balances=(("1771", "credit", "100.00"),))
    _prepare_closing_warning(monkeypatch)

    main_window.MainWindow._close_fiscal_year(window)

    warning = _FakeMessageBox.instances[0]
    assert "Umsatzsteuer-, Vorsteuer- oder Vorauszahlungskonten" in warning.text
    assert "1771 · Konto 1771: Habensaldo 100,00 €" in warning.informative_text
    assert _FakeMessageBox.question_calls == 0
    assert window._workspace.closed == []


def test_closing_has_no_extra_warning_when_vat_source_accounts_are_zero(
    monkeypatch,
) -> None:
    window = _ClosingWindow(balances=(("3840", "credit", "100.00"),))
    _prepare_closing_warning(monkeypatch)

    main_window.MainWindow._close_fiscal_year(window)

    assert _FakeMessageBox.instances == []
    assert _FakeMessageBox.question_calls == 1
    assert window._workspace.closed == []


def test_closing_can_continue_after_vat_warning(monkeypatch) -> None:
    window = _ClosingWindow(balances=(("1571", "debit", "50.00"),))
    _prepare_closing_warning(
        monkeypatch,
        choices={
            "Umsatzsteuerkonten nicht verrechnet": "Ohne Verrechnung fortfahren",
            "Bilanzdarstellung": "Variante A – vor Ergebnisverwendung",
        },
    )
    _FakeMessageBox.question_answer = QMessageBox.StandardButton.Yes

    main_window.MainWindow._close_fiscal_year(window)

    assert _FakeMessageBox.question_calls == 1
    assert len(window._workspace.closed) == 1


def test_aborting_vat_warning_leaves_fiscal_year_open(monkeypatch) -> None:
    window = _ClosingWindow(balances=(("3820", "debit", "75.00"),))
    _prepare_closing_warning(monkeypatch, choice="Abbrechen")

    main_window.MainWindow._close_fiscal_year(window)

    assert _FakeMessageBox.question_calls == 0
    assert window._workspace.closed == []


def test_closing_warning_can_open_vat_reconciliation(monkeypatch) -> None:
    window = _ClosingWindow(balances=(("1771", "credit", "100.00"),))
    _prepare_closing_warning(
        monkeypatch,
        choice="Umsatzsteuerverrechnung aufrufen",
    )

    main_window.MainWindow._close_fiscal_year(window)

    assert window._proposed
    assert _FakeMessageBox.question_calls == 0
    assert window._workspace.closed == []

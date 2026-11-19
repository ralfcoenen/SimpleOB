from PySide6.QtWidgets import QApplication

from simpleob.domain.account import Account
from simpleob.domain.account_type import AccountType
from simpleob.domain.person_account_role import PersonAccountRole
from simpleob.domain.template_account import TemplateAccount
from simpleob.ui_qt.booking_frame import BookingFrame


def _app():
    return QApplication.instance() or QApplication([])


def test_booking_account_labels_and_row_show_person_account_role():
    _app()
    partner_name = "Gleichnamig GmbH"
    debtor = Account(
        TemplateAccount("10000", partner_name, AccountType.ASSET),
        person_account_role=PersonAccountRole.DEBITOR,
    )
    creditor = Account(
        TemplateAccount("70000", partner_name, AccountType.LIABILITY),
        person_account_role=PersonAccountRole.KREDITOR,
    )
    frame = BookingFrame(
        accounts=(debtor, creditor),
        equity_contribution_account_numbers=frozenset(),
        on_booking_created=lambda *_args: None,
    )

    assert frame._account_display_name(debtor) == "10000 – Debitor – Gleichnamig GmbH"
    assert frame._account_display_name(creditor) == "70000 – Kreditor – Gleichnamig GmbH"
    assert frame._resolve_account("10000") is debtor
    assert frame._resolve_account("Debitor – Gleichnamig GmbH") is debtor
    assert frame._resolve_account("Kreditor – Gleichnamig GmbH") is creditor

    row = frame._rows[0]
    row.account_entry.setText("10000")
    assert row.name_item.text() == "Debitor – Gleichnamig GmbH"
    frame.close()

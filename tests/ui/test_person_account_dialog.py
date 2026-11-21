from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QMessageBox,
    QTableWidget,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from simpleob.database.business_partner_repository import BusinessPartnerRepository
from simpleob.database.company_repository import CompanyRepository
from simpleob.database.database import Base
from simpleob.database.person_account_repository import PersonAccountRepository
from simpleob.domain.business_partner import BusinessPartner
from simpleob.domain.company import Company
from simpleob.domain.person_account_role import PersonAccountRole
from simpleob.ui_qt import main_window as main_window_module
from simpleob.ui_qt.account_table_helpers import AccountNumberTableWidgetItem
from simpleob.ui_qt.main_window import MainWindow
from simpleob.ui_qt.person_account_dialog import PersonAccountDialog


def _setup_repository():
    app = QApplication.instance() or QApplication([])
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    company = Company(company_id=uuid4(), name="UI Test")
    CompanyRepository(session).add(company)
    return app, engine, session, company, PersonAccountRepository(session)


@pytest.mark.parametrize(
    ("roles", "is_customer", "is_supplier", "expected_numbers"),
    [
        (
            (PersonAccountRole.DEBITOR,),
            True,
            False,
            {PersonAccountRole.DEBITOR: "10000"},
        ),
        (
            (PersonAccountRole.KREDITOR,),
            False,
            True,
            {PersonAccountRole.KREDITOR: "70000"},
        ),
        (
            (PersonAccountRole.DEBITOR, PersonAccountRole.KREDITOR),
            True,
            True,
            {
                PersonAccountRole.DEBITOR: "10000",
                PersonAccountRole.KREDITOR: "70000",
            },
        ),
    ],
)
def test_new_partner_is_created_with_selected_roles_and_numbers(
    roles, is_customer, is_supplier, expected_numbers
):
    app, engine, session, company, repository = _setup_repository()
    dialog = PersonAccountDialog(
        None, company_id=company.company_id, repository=repository
    )
    dialog._role_checks[PersonAccountRole.DEBITOR].setChecked(
        PersonAccountRole.DEBITOR in roles
    )
    dialog._role_checks[PersonAccountRole.KREDITOR].setChecked(
        PersonAccountRole.KREDITOR in roles
    )
    dialog._name.setText("Gemeinsamer Partner")

    dialog._save()

    assert dialog.saved is not None
    assert len(dialog.saved_accounts) == len(roles)
    assert {
        account.role: account.account_number for account in dialog.saved_accounts
    } == expected_numbers
    assert dialog.saved.partner.is_customer is is_customer
    assert dialog.saved.partner.is_supplier is is_supplier
    assert len(repository.list_for_company(company_id=company.company_id)) == len(roles)
    session.close()
    engine.dispose()
    app.processEvents()


def test_dialog_requires_at_least_one_role(monkeypatch):
    app, engine, session, company, repository = _setup_repository()
    dialog = PersonAccountDialog(
        None, company_id=company.company_id, repository=repository
    )
    dialog._role_checks[PersonAccountRole.DEBITOR].setChecked(False)
    warnings = []
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *args: warnings.append(args[-1])
    )

    dialog._save()

    assert dialog.saved_accounts == ()
    assert warnings and "mindestens ein" in warnings[0].lower()
    assert repository.list_for_company(company_id=company.company_id) == ()
    session.close()
    engine.dispose()
    app.processEvents()


def test_number_suggestions_are_independent_and_role_specific():
    app, engine, session, company, repository = _setup_repository()
    dialog = PersonAccountDialog(
        None, company_id=company.company_id, repository=repository
    )

    assert dialog._number_fields[PersonAccountRole.DEBITOR].text() == "10000"
    assert dialog._number_fields[PersonAccountRole.KREDITOR].text() == ""
    dialog._role_checks[PersonAccountRole.KREDITOR].setChecked(True)
    assert dialog._number_fields[PersonAccountRole.KREDITOR].text() == "70000"
    session.close()
    engine.dispose()
    app.processEvents()


@pytest.mark.parametrize(
    ("existing_role", "added_role", "existing_number", "added_number"),
    [
        (
            PersonAccountRole.DEBITOR,
            PersonAccountRole.KREDITOR,
            "10000",
            "70000",
        ),
        (
            PersonAccountRole.KREDITOR,
            PersonAccountRole.DEBITOR,
            "70000",
            "10000",
        ),
    ],
)
def test_existing_partner_can_get_missing_role_without_changing_old_number(
    existing_role, added_role, existing_number, added_number
):
    app, engine, session, company, repository = _setup_repository()
    existing = repository.create(
        company_id=company.company_id,
        role=existing_role,
        name="Vorhandener Partner",
        account_number=existing_number,
    )
    dialog = PersonAccountDialog(
        None, company_id=company.company_id, repository=repository
    )
    dialog._partner_choice.setCurrentIndex(
        dialog._partner_choice.findData(str(existing.partner.partner_id))
    )

    existing_check = dialog._role_checks[existing_role]
    added_check = dialog._role_checks[added_role]
    assert existing_check.isChecked()
    assert not existing_check.isEnabled()
    assert dialog._number_fields[existing_role].text() == existing_number
    assert dialog._number_fields[existing_role].isReadOnly()
    assert not added_check.isChecked()
    assert added_check.isEnabled()

    added_check.setChecked(True)
    assert dialog._number_fields[added_role].text() == added_number
    dialog._save()

    assert len(dialog.saved_accounts) == 1
    assert dialog.saved_accounts[0].role is added_role
    accounts = repository.accounts_for_partner(
        company_id=company.company_id, partner_id=existing.partner.partner_id
    )
    assert {account.role: account.account_number for account in accounts} == {
        existing_role: existing_number,
        added_role: added_number,
    }
    session.close()
    engine.dispose()
    app.processEvents()


def test_partner_without_account_for_existing_role_keeps_role_locked_and_gets_proposal():
    app, engine, session, company, repository = _setup_repository()
    partner = BusinessPartner(
        company_id=company.company_id,
        name="Kunde ohne Personenkonto",
        is_customer=True,
        is_supplier=False,
    )
    BusinessPartnerRepository(session).add(partner)
    dialog = PersonAccountDialog(
        None, company_id=company.company_id, repository=repository
    )
    dialog._partner_choice.setCurrentIndex(
        dialog._partner_choice.findData(str(partner.partner_id))
    )

    debtor_check = dialog._role_checks[PersonAccountRole.DEBITOR]
    assert debtor_check.isChecked()
    assert not debtor_check.isEnabled()
    assert dialog._number_fields[PersonAccountRole.DEBITOR].text() == "10000"
    assert not dialog._number_fields[PersonAccountRole.DEBITOR].isReadOnly()
    assert not dialog._role_checks[PersonAccountRole.KREDITOR].isChecked()
    session.close()
    engine.dispose()
    app.processEvents()


def test_existing_partner_with_both_accounts_displays_locked_numbers(monkeypatch):
    app, engine, session, company, repository = _setup_repository()
    debtor = BusinessPartner(
        company_id=company.company_id,
        name="Beide Rollen",
        is_customer=True,
        is_supplier=True,
    )
    BusinessPartnerRepository(session).add(debtor)
    repository.create_many(
        company_id=company.company_id,
        account_numbers={
            PersonAccountRole.DEBITOR: "10000",
            PersonAccountRole.KREDITOR: "70000",
        },
        name=debtor.name,
        partner_id=debtor.partner_id,
    )
    dialog = PersonAccountDialog(
        None, company_id=company.company_id, repository=repository
    )
    dialog._partner_choice.setCurrentIndex(
        dialog._partner_choice.findData(str(debtor.partner_id))
    )

    for role, number in (
        (PersonAccountRole.DEBITOR, "10000"),
        (PersonAccountRole.KREDITOR, "70000"),
    ):
        assert dialog._role_checks[role].isChecked()
        assert not dialog._role_checks[role].isEnabled()
        assert dialog._number_fields[role].text() == number
        assert dialog._number_fields[role].isReadOnly()

    warning = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: warning.append(args[-1]))
    dialog._save()
    assert warning and "fehlendes" in warning[0]
    session.close()
    engine.dispose()
    app.processEvents()


def test_manual_number_is_validated_for_selected_role(monkeypatch):
    app, engine, session, company, repository = _setup_repository()
    dialog = PersonAccountDialog(
        None, company_id=company.company_id, repository=repository
    )
    number = dialog._number_fields[PersonAccountRole.DEBITOR]
    number.setText("70000")
    dialog._name.setText("Falscher Nummernkreis")
    warnings = []
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *args: warnings.append(args[-1])
    )

    dialog._save()

    assert dialog.saved is None
    assert warnings and "Nummernkreis" in warnings[0]
    assert repository.partners_for_company(company_id=company.company_id) == ()
    session.close()
    engine.dispose()
    app.processEvents()


def test_manual_numbers_within_each_role_range_are_saved(monkeypatch):
    app, engine, session, company, repository = _setup_repository()
    dialog = PersonAccountDialog(
        None, company_id=company.company_id, repository=repository
    )
    dialog._number_fields[PersonAccountRole.DEBITOR].setText("12345")
    dialog._role_checks[PersonAccountRole.KREDITOR].setChecked(True)
    dialog._number_fields[PersonAccountRole.KREDITOR].setText("71234")
    dialog._name.setText("Manueller Nummerntest")
    warnings = []
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *args: warnings.append(args[-1])
    )

    dialog._save()

    assert warnings == []
    assert {
        account.role: account.account_number for account in dialog.saved_accounts
    } == {
        PersonAccountRole.DEBITOR: "12345",
        PersonAccountRole.KREDITOR: "71234",
    }
    session.close()
    engine.dispose()
    app.processEvents()


def test_editing_existing_account_keeps_role_and_number_immutable():
    app, engine, session, company, repository = _setup_repository()
    created = repository.create(
        company_id=company.company_id,
        role=PersonAccountRole.KREDITOR,
        name="Lieferant",
    )
    dialog = PersonAccountDialog(
        None,
        company_id=company.company_id,
        role=created.role,
        repository=repository,
        existing=created,
    )
    assert dialog._role_checks == {}
    assert dialog._number.isReadOnly()
    assert dialog._number.text() == created.account_number
    assert dialog._role is PersonAccountRole.KREDITOR
    session.close()
    engine.dispose()
    app.processEvents()


def test_main_window_refreshes_once_and_selects_all_created_accounts(monkeypatch):
    app = QApplication.instance() or QApplication([])
    accounts = (
        SimpleNamespace(account_number="10000"),
        SimpleNamespace(account_number="70000"),
    )

    class AcceptedDialog:
        saved_accounts = accounts

        def __init__(self, *_args, **_kwargs):
            pass

        @staticmethod
        def exec():
            return 1

    monkeypatch.setattr(main_window_module, "PersonAccountDialog", AcceptedDialog)
    table = QTableWidget(0, 1)
    table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    refresh_accounts = Mock()

    def refresh_table():
        refresh_accounts()
        table.setRowCount(2)
        table.setItem(0, 0, AccountNumberTableWidgetItem("10000"))
        table.setItem(1, 0, AccountNumberTableWidgetItem("70000"))

    window = SimpleNamespace(
        _person_account_repository=object(),
        _workspace=SimpleNamespace(is_open=True),
        _context=SimpleNamespace(company=SimpleNamespace(company_id=uuid4())),
        _activate_account_editing_mode=Mock(),
        _reload_chart_of_accounts=Mock(return_value=(object(), ())),
        _refresh_person_account_reports=Mock(),
        _refresh_accounts=refresh_table,
        _account_table=table,
    )

    MainWindow._open_new_person_account(window)

    assert refresh_accounts.call_count == 1
    assert {
        table.item(index.row(), 0).text()
        for index in table.selectionModel().selectedRows()
    } == {"10000", "70000"}
    table.close()
    app.processEvents()

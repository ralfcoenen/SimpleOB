from uuid import uuid4

import pytest
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from simpleob.database.business_partner_repository import BusinessPartnerRepository
from simpleob.database.company_repository import CompanyRepository
from simpleob.database.database import Base
from simpleob.database.person_account_repository import PersonAccountRepository
from simpleob.domain.business_partner import BusinessPartner
from simpleob.domain.company import Company
from simpleob.domain.person_account_role import PersonAccountRole
from simpleob.ui_qt.person_account_dialog import PersonAccountDialog


def _setup_repository():
    app = QApplication.instance() or QApplication([])
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    company = Company(company_id=uuid4(), name="UI Test")
    CompanyRepository(session).add(company)
    return app, engine, session, company, PersonAccountRepository(session)


def test_dialog_creates_person_account_without_hgb_fields():
    app, engine, session, company, repository = _setup_repository()
    dialog = PersonAccountDialog(
        None,
        company_id=company.company_id,
        role=PersonAccountRole.DEBITOR,
        repository=repository,
    )
    assert dialog._number.text() == "10000"
    assert not any("HGB" in label.text() for label in dialog.findChildren(QLabel))
    dialog._name.setText("Dialog Kunde")
    dialog._save()
    assert dialog.saved is not None
    assert dialog.saved.account_number == "10000"
    assert dialog.saved.partner.name == "Dialog Kunde"
    session.close()
    engine.dispose()
    app.processEvents()


def test_dialog_suggests_numbers_for_both_roles():
    app, engine, session, company, repository = _setup_repository()
    debtor = PersonAccountDialog(
        None, company_id=company.company_id, role=PersonAccountRole.DEBITOR,
        repository=repository,
    )
    creditor = PersonAccountDialog(
        None, company_id=company.company_id, role=PersonAccountRole.KREDITOR,
        repository=repository,
    )
    assert debtor._number.text() == "10000"
    assert creditor._number.text() == "70000"
    assert debtor._debtor_radio.isChecked()
    assert creditor._creditor_radio.isChecked()
    session.close()
    engine.dispose()
    app.processEvents()


def test_role_switch_refreshes_automatic_suggestion():
    app, engine, session, company, repository = _setup_repository()
    partner_account = repository.create(
        company_id=company.company_id,
        role=PersonAccountRole.DEBITOR,
        name="Kunde mit Debitorenkonto",
    )
    dialog = PersonAccountDialog(
        None, company_id=company.company_id, role=PersonAccountRole.KREDITOR,
        repository=repository,
    )
    dialog._debtor_radio.setChecked(True)
    assert dialog._role is PersonAccountRole.DEBITOR
    assert dialog._number.text() == "10001"
    assert dialog._partner_choice.findData(str(partner_account.partner.partner_id)) == -1
    session.close()
    engine.dispose()
    app.processEvents()


def test_partner_choices_match_debtor_creditor_and_both_roles():
    app, engine, session, company, repository = _setup_repository()
    partners = BusinessPartnerRepository(session)
    debtor_only = BusinessPartner(
        company_id=company.company_id,
        name="Nur Debitor",
        is_customer=True,
        is_supplier=False,
    )
    creditor_only = BusinessPartner(
        company_id=company.company_id,
        name="Nur Kreditor",
        is_customer=False,
        is_supplier=True,
    )
    both_roles = BusinessPartner(
        company_id=company.company_id,
        name="Debitor und Kreditor",
        is_customer=True,
        is_supplier=True,
    )
    for partner in (debtor_only, creditor_only, both_roles):
        partners.add(partner)

    dialog = PersonAccountDialog(
        None,
        company_id=company.company_id,
        role=PersonAccountRole.DEBITOR,
        repository=repository,
    )
    debtor_ids = {
        dialog._partner_choice.itemData(index)
        for index in range(1, dialog._partner_choice.count())
    }
    assert debtor_ids == {
        str(debtor_only.partner_id),
        str(both_roles.partner_id),
    }

    dialog._creditor_radio.setChecked(True)
    creditor_ids = {
        dialog._partner_choice.itemData(index)
        for index in range(1, dialog._partner_choice.count())
    }
    assert creditor_ids == {
        str(creditor_only.partner_id),
        str(both_roles.partner_id),
    }
    assert dialog._partner_choice.itemData(0) is None
    session.close()
    engine.dispose()
    app.processEvents()


def test_role_switch_resets_partner_selection_that_is_not_valid_for_new_role():
    app, engine, session, company, repository = _setup_repository()
    debtor = BusinessPartner(
        company_id=company.company_id,
        name="Nur Debitor",
        is_customer=True,
        is_supplier=False,
    )
    BusinessPartnerRepository(session).add(debtor)
    dialog = PersonAccountDialog(
        None,
        company_id=company.company_id,
        role=PersonAccountRole.DEBITOR,
        repository=repository,
    )
    dialog._partner_choice.setCurrentIndex(
        dialog._partner_choice.findData(str(debtor.partner_id))
    )
    assert dialog._partner_choice.currentData() == str(debtor.partner_id)

    dialog._creditor_radio.setChecked(True)

    assert dialog._partner_choice.currentIndex() == 0
    assert dialog._partner_choice.currentData() is None
    session.close()
    engine.dispose()
    app.processEvents()


@pytest.mark.parametrize(
    ("role", "is_customer", "is_supplier"),
    [
        (PersonAccountRole.DEBITOR, True, False),
        (PersonAccountRole.KREDITOR, False, True),
    ],
)
def test_new_partner_gets_only_the_selected_role(role, is_customer, is_supplier):
    app, engine, session, company, repository = _setup_repository()
    dialog = PersonAccountDialog(
        None,
        company_id=company.company_id,
        role=role,
        repository=repository,
    )
    dialog._name.setText("Neuer Geschäftspartner")
    dialog._save()

    assert dialog.saved is not None
    assert dialog.saved.role is role
    assert dialog.saved.partner.is_customer is is_customer
    assert dialog.saved.partner.is_supplier is is_supplier
    session.close()
    engine.dispose()
    app.processEvents()


def test_manual_number_is_kept_or_replaced_only_after_confirmation(monkeypatch):
    app, engine, session, company, repository = _setup_repository()
    dialog = PersonAccountDialog(
        None, company_id=company.company_id, role=PersonAccountRole.DEBITOR,
        repository=repository,
    )
    dialog._number.selectAll()
    dialog._number.insert("12345")
    assert dialog._number_is_manual

    monkeypatch.setattr(
        QMessageBox, "question", lambda *args: QMessageBox.StandardButton.No
    )
    dialog._creditor_radio.setChecked(True)
    assert dialog._number.text() == "12345"
    assert dialog._role is PersonAccountRole.KREDITOR

    monkeypatch.setattr(
        QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes
    )
    dialog._debtor_radio.setChecked(True)
    assert dialog._number.text() == "10000"
    assert not dialog._number_is_manual
    session.close()
    engine.dispose()
    app.processEvents()


def test_manual_number_is_validated_for_selected_role(monkeypatch):
    app, engine, session, company, repository = _setup_repository()
    dialog = PersonAccountDialog(
        None, company_id=company.company_id, role=PersonAccountRole.DEBITOR,
        repository=repository,
    )
    dialog._number.setText("70000")
    dialog._name.setText("Falscher Nummernkreis")
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: warnings.append(args[-1]))
    dialog._save()
    assert dialog.saved is None
    assert warnings and "Nummernkreis" in warnings[0]
    session.close()
    engine.dispose()
    app.processEvents()


def test_editing_existing_account_keeps_role_immutable():
    app, engine, session, company, repository = _setup_repository()
    created = repository.create(
        company_id=company.company_id,
        role=PersonAccountRole.KREDITOR,
        name="Lieferant",
    )
    dialog = PersonAccountDialog(
        None, company_id=company.company_id, role=created.role,
        repository=repository, existing=created,
    )
    assert dialog._debtor_radio is None
    assert dialog._creditor_radio is None
    assert dialog._number.isReadOnly()
    assert dialog._role is PersonAccountRole.KREDITOR
    session.close()
    engine.dispose()
    app.processEvents()

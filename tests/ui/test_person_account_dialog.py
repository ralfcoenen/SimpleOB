from uuid import uuid4

from PySide6.QtWidgets import QApplication, QLabel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from simpleob.database.company_repository import CompanyRepository
from simpleob.database.database import Base
from simpleob.database.person_account_repository import PersonAccountRepository
from simpleob.domain.company import Company
from simpleob.domain.person_account_role import PersonAccountRole
from simpleob.ui_qt.person_account_dialog import PersonAccountDialog


def test_dialog_creates_person_account_without_hgb_fields():
    app = QApplication.instance() or QApplication([])
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    company = Company(company_id=uuid4(), name="UI Test")
    CompanyRepository(session).add(company)
    repository = PersonAccountRepository(session)
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

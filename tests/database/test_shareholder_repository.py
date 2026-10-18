"""Tests für die Persistenz von Gesellschaftern."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from simpleob.database.company_repository import (
    CompanyRepository,
)
from simpleob.database.database import Base
from simpleob.database.shareholder_repository import (
    ShareholderRepository,
)
from simpleob.domain.company import Company
from simpleob.domain.shareholder import Shareholder


def _shareholder(
    *,
    company_id,
    shareholder_number: str = "1",
    name: str = "Muster",
    first_name: str = "Max",
) -> Shareholder:
    """Erzeugt einen Gesellschafter für Repository-Tests."""

    return Shareholder(
        company_id=company_id,
        shareholder_number=shareholder_number,
        name=name,
        first_name=first_name,
        legal_status="NPP",
        share_numerator="1",
        share_denominator="2",
        tax_number="1234567890123",
        tax_id="12345678901",
        wid="DE123456789",
    )


def test_adds_and_loads_shareholder() -> None:
    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    shareholder = _shareholder(
        company_id=company.company_id
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        repository = ShareholderRepository(
            session
        )

        company_repository.add(
            company
        )

        repository.add(
            shareholder=shareholder
        )

        loaded = repository.get(
            shareholder.shareholder_id
        )

    assert loaded == shareholder


def test_lists_shareholders_for_company() -> None:
    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    shareholder_1 = _shareholder(
        company_id=company.company_id,
        shareholder_number="1",
        name="Muster",
        first_name="Max",
    )

    shareholder_2 = _shareholder(
        company_id=company.company_id,
        shareholder_number="2",
        name="Beispiel",
        first_name="Erika",
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        repository = ShareholderRepository(
            session
        )

        company_repository.add(
            company
        )

        repository.add(
            shareholder=shareholder_2
        )

        repository.add(
            shareholder=shareholder_1
        )

        loaded = repository.list_for_company(
            company.company_id
        )

    assert loaded == (
        shareholder_1,
        shareholder_2,
    )


def test_rejects_shareholder_for_unknown_company() -> None:
    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    shareholder = _shareholder(
        company_id=uuid4()
    )

    with Session() as session:
        repository = ShareholderRepository(
            session
        )

        with pytest.raises(
            ValueError,
            match="Unternehmen ist nicht vorhanden",
        ):
            repository.add(
                shareholder=shareholder
            )


def test_rejects_duplicate_shareholder_number_for_company() -> None:
    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    first_shareholder = _shareholder(
        company_id=company.company_id,
        shareholder_number="1",
        name="Muster",
    )

    duplicate_shareholder = _shareholder(
        company_id=company.company_id,
        shareholder_number="1",
        name="Beispiel",
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        repository = ShareholderRepository(
            session
        )

        company_repository.add(
            company
        )

        repository.add(
            shareholder=first_shareholder
        )

        with pytest.raises(
            ValueError,
            match=(
                "Gesellschafter-ID ist für dieses "
                "Unternehmen bereits vorhanden"
            ),
        ):
            repository.add(
                shareholder=duplicate_shareholder
            )


def test_updates_shareholder() -> None:
    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    shareholder = _shareholder(
        company_id=company.company_id
    )

    updated_shareholder = Shareholder(
        shareholder_id=shareholder.shareholder_id,
        company_id=company.company_id,
        shareholder_number="1",
        name="Muster",
        first_name="Maximilian",
        legal_status="NPP",
        share_numerator="3",
        share_denominator="4",
        tax_number="",
        tax_id="",
        wid="",
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        repository = ShareholderRepository(
            session
        )

        company_repository.add(
            company
        )

        repository.add(
            shareholder=shareholder
        )

        repository.update(
            shareholder=updated_shareholder
        )

        loaded = repository.get(
            shareholder.shareholder_id
        )

    assert loaded == updated_shareholder


def test_deletes_shareholder() -> None:
    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    shareholder = _shareholder(
        company_id=company.company_id
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        repository = ShareholderRepository(
            session
        )

        company_repository.add(
            company
        )

        repository.add(
            shareholder=shareholder
        )

        repository.delete(
            shareholder_id=shareholder.shareholder_id
        )

        loaded = repository.get(
            shareholder.shareholder_id
        )

    assert loaded is None

def test_persists_shareholder_tax_number_federal_state() -> None:
    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    shareholder = Shareholder(
        company_id=company.company_id,
        shareholder_number="1",
        name="Muster",
        first_name="Max",
        legal_status="NPP",
        share_numerator="1",
        share_denominator="2",
        tax_number="123/4567/8901",
        tax_number_federal_state="NW",
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        repository = ShareholderRepository(
            session
        )

        company_repository.add(
            company
        )

        repository.add(
            shareholder=shareholder
        )

        loaded = repository.get(
            shareholder.shareholder_id
        )

    assert loaded is not None
    assert loaded.tax_number == "5123045678901"
    assert loaded.tax_number_federal_state == "NW"
    assert loaded == shareholder

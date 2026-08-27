"""Tests für die Umsatzsteuerkonfiguration."""

from datetime import date
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from openbilanz.database.company_repository import (
    CompanyRepository,
)
from openbilanz.database.database import Base
from openbilanz.database.vat_configuration_repository import (
    VatConfigurationRepository,
)
from openbilanz.domain.company import Company
from openbilanz.domain.vat_configuration import (
    VatConfiguration,
)
from openbilanz.domain.vat_taxation_type import (
    VatTaxationType,
)


def test_saves_and_loads_vat_configuration() -> None:
    """Die USt-Konfiguration wird mandantenbezogen gespeichert."""

    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    company = Company(
        company_id=uuid4(),
        name="Musterbetrieb",
    )

    configuration = VatConfiguration(
        taxation_type=VatTaxationType.SMALL_BUSINESS,
        effective_from=date(2027, 1, 1),
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        repository = VatConfigurationRepository(
            session
        )

        company_repository.add(
            company
        )

        repository.save(
            company_id=company.company_id,
            configuration=configuration,
        )

        loaded = repository.load(
            company.company_id
        )

    assert loaded == configuration

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from simpleob.database.company_repository import CompanyRepository
from simpleob.database.database import Base
from simpleob.domain.company import Company
from simpleob.domain.kr_settings import KrAnnualTurnoverAddition, KrSettings


@pytest.mark.parametrize("amount", [Decimal("-0.01"), Decimal("1.001")])
def test_kr_annual_turnover_addition_rejects_invalid_cent_amounts(amount):
    with pytest.raises(ValueError):
        KrAnnualTurnoverAddition(2026, amount)


def test_kr_settings_are_tenant_scoped_and_calendar_year_bound() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            repository = CompanyRepository(session)
            first = Company(uuid4(), "First UG")
            second = Company(uuid4(), "Second UG")
            repository.add(first)
            repository.add(second)

            original = KrSettings(
                company_id=first.company_id,
                activity_start_date=date(2022, 4, 1),
                waiver_declared=True,
                waiver_date=date(2025, 12, 15),
                external_turnovers=(
                    KrAnnualTurnoverAddition(2024, Decimal("1234.56")),
                    KrAnnualTurnoverAddition(2025, Decimal("789.01")),
                ),
            )
            repository.save_kr_settings(original)

            loaded = repository.get_kr_settings(first.company_id)
            assert loaded == original
            assert repository.get_kr_settings(second.company_id) == KrSettings(
                company_id=second.company_id
            )

            edited = KrSettings(
                company_id=first.company_id,
                activity_start_date=original.activity_start_date,
                waiver_declared=original.waiver_declared,
                waiver_date=original.waiver_date,
                external_turnovers=(
                    KrAnnualTurnoverAddition(2024, Decimal("1234.56")),
                    KrAnnualTurnoverAddition(2025, Decimal("800.00")),
                ),
            )
            repository.save_kr_settings(edited, expected_settings=loaded)
            assert repository.get_kr_settings(first.company_id) == edited
    finally:
        engine.dispose()

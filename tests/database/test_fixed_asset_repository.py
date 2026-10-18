"""Tests für die Persistenz von Anlagegütern."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from simpleob.database.company_repository import (
    CompanyRepository,
)
from simpleob.database.database import Base
from simpleob.database.fixed_asset_repository import (
    FixedAssetRepository,
)
from simpleob.domain.company import Company
from simpleob.domain.fixed_asset import FixedAsset


def _fixed_asset(
    *,
    company_id,
    asset_code: str = "A-0001",
    description: str = "MacBook Pro",
) -> FixedAsset:
    """Erzeugt ein Anlagegut für Repository-Tests."""

    return FixedAsset(
        company_id=company_id,
        asset_code=asset_code,
        description=description,
        position_code="HGB.266.AKTIVA.A.II.3",
        asset_account_number="0690",
        depreciation_expense_account_number="4830",
        acquisition_date=date(2026, 3, 15),
        acquisition_cost=Decimal("2400.00"),
        depreciation_start_date=date(2026, 3, 15),
        useful_life_months=36,
    )


def test_adds_and_loads_fixed_asset() -> None:
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

    asset = _fixed_asset(
        company_id=company.company_id
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        repository = FixedAssetRepository(
            session
        )

        company_repository.add(
            company
        )

        repository.add(
            fixed_asset=asset
        )

        loaded = repository.get(
            asset.fixed_asset_id
        )

    assert loaded == asset


def test_lists_fixed_assets_for_company() -> None:
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

    asset_1 = _fixed_asset(
        company_id=company.company_id,
        asset_code="A-0001",
        description="MacBook Pro",
    )

    asset_2 = _fixed_asset(
        company_id=company.company_id,
        asset_code="A-0002",
        description="Büromöbel",
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        repository = FixedAssetRepository(
            session
        )

        company_repository.add(
            company
        )

        repository.add(
            fixed_asset=asset_2
        )

        repository.add(
            fixed_asset=asset_1
        )

        loaded = repository.list_for_company(
            company.company_id
        )

    assert loaded == (
        asset_1,
        asset_2,
    )


def test_rejects_fixed_asset_for_unknown_company() -> None:
    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    asset = _fixed_asset(
        company_id=uuid4()
    )

    with Session() as session:
        repository = FixedAssetRepository(
            session
        )

        with pytest.raises(
            ValueError,
            match="Unternehmen ist nicht vorhanden",
        ):
            repository.add(
                fixed_asset=asset
            )


def test_rejects_duplicate_asset_code_for_company() -> None:
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

    first_asset = _fixed_asset(
        company_id=company.company_id,
        asset_code="A-0001",
    )

    duplicate_asset = _fixed_asset(
        company_id=company.company_id,
        asset_code="A-0001",
        description="Anderes Anlagegut",
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        repository = FixedAssetRepository(
            session
        )

        company_repository.add(
            company
        )

        repository.add(
            fixed_asset=first_asset
        )

        with pytest.raises(
            ValueError,
            match=(
                "Anlagen-ID ist für dieses "
                "Unternehmen bereits vorhanden"
            ),
        ):
            repository.add(
                fixed_asset=duplicate_asset
            )

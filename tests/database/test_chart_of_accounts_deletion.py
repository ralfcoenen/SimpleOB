"""Gezielte Regressionstests zum Löschen von Mandantenkonten."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from simpleob.database.chart_of_accounts_repository import (
    ChartOfAccountsRepository,
)
from simpleob.database.company_repository import CompanyRepository
from simpleob.database.database import Base
from simpleob.database.models import (
    Anlagegut,
    Buchung,
    Buchungszeile,
    KontenrahmenKonfiguration,
    Kontenrolle,
    KontenTaxonomieZuordnung,
    Konto,
    Mandant,
    Wirtschaftsjahr,
)
from simpleob.domain.account import Account
from simpleob.domain.account_type import AccountType
from simpleob.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from simpleob.domain.company import Company
from simpleob.domain.template_account import TemplateAccount


def _repository_context():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    company = Company(company_id=uuid4(), name="Löschtest UG")
    CompanyRepository(session).add(company)
    templates = tuple(
        TemplateAccount(number, f"Konto {number}", AccountType.ASSET)
        for number in ("7000", "7001", "7002", "7003")
    )
    ChartOfAccountsRepository(session).save_for_company(
        company_id=company.company_id,
        chart_of_accounts=ChartOfAccountsTemplate("Test", templates),
        accounts=tuple(Account(template=template) for template in templates),
    )
    mandant = (
        session.query(Mandant)
        .filter(Mandant.company_id == str(company.company_id))
        .one()
    )
    return engine, session, company, mandant


def test_deletes_unused_account_with_taxonomy_and_hgb_mapping():
    engine, session, company, mandant = _repository_context()
    try:
        account = (
            session.query(Konto)
            .filter(
                Konto.mandant_id == mandant.id,
                Konto.account_number == "7000",
            )
            .one()
        )
        account.debit_position_code = "HGB.266.AKTIVA.B.II.4"
        session.add_all(
            (
                KontenTaxonomieZuordnung(
                    mandant_id=mandant.id,
                    account_number="7000",
                    taxonomy_version="6.9",
                    concept_name="sample.current",
                ),
                KontenTaxonomieZuordnung(
                    mandant_id=mandant.id,
                    account_number="7000",
                    taxonomy_version="6.8",
                    concept_name="sample.previous",
                ),
            )
        )
        session.commit()

        blocked = ChartOfAccountsRepository(session).delete_accounts(
            company_id=company.company_id,
            account_numbers=("7000",),
        )

        assert blocked == {}
        assert (
            session.query(Konto)
            .filter(
                Konto.mandant_id == mandant.id,
                Konto.account_number == "7000",
            )
            .count()
            == 0
        )
        assert (
            session.query(KontenTaxonomieZuordnung)
            .filter(
                KontenTaxonomieZuordnung.mandant_id == mandant.id,
                KontenTaxonomieZuordnung.account_number == "7000",
            )
            .count()
            == 0
        )
    finally:
        session.close()
        engine.dispose()


def test_deletes_unused_account_with_hgb_mapping_without_taxonomy():
    engine, session, company, mandant = _repository_context()
    try:
        account = (
            session.query(Konto)
            .filter(
                Konto.mandant_id == mandant.id,
                Konto.account_number == "7000",
            )
            .one()
        )
        account.credit_position_code = "HGB.275.1"
        session.commit()

        blocked = ChartOfAccountsRepository(session).delete_accounts(
            company_id=company.company_id,
            account_numbers=("7000",),
        )

        assert blocked == {}
        assert (
            session.query(Konto)
            .filter(
                Konto.mandant_id == mandant.id,
                Konto.account_number == "7000",
            )
            .count()
            == 0
        )
    finally:
        session.close()
        engine.dispose()


def test_deletes_multiple_unreferenced_accounts_together():
    engine, session, company, mandant = _repository_context()
    try:
        session.add(
            KontenTaxonomieZuordnung(
                mandant_id=mandant.id,
                account_number="7001",
                taxonomy_version="6.9",
                concept_name="sample.one",
            )
        )
        session.commit()

        blocked = ChartOfAccountsRepository(session).delete_accounts(
            company_id=company.company_id,
            account_numbers=("7000", "7001"),
        )

        assert blocked == {}
        assert [
            account.account_number
            for account in session.query(Konto)
            .filter(Konto.mandant_id == mandant.id)
            .order_by(Konto.account_number)
            .all()
            ] == ["7002", "7003"]
        assert (
            session.query(KontenTaxonomieZuordnung)
            .filter(
                KontenTaxonomieZuordnung.mandant_id == mandant.id,
                KontenTaxonomieZuordnung.account_number == "7001",
            )
            .count()
            == 0
        )
    finally:
        session.close()
        engine.dispose()


def test_blocks_account_booked_in_any_fiscal_year_and_aborts_whole_batch():
    engine, session, company, mandant = _repository_context()
    try:
        fiscal_year = Wirtschaftsjahr(
            mandant_id=mandant.id,
            start_date=date(2021, 1, 1),
            end_date=date(2021, 12, 31),
            status="CLOSED",
        )
        session.add(fiscal_year)
        session.flush()
        booking = Buchung(
            booking_id=str(uuid4()),
            wirtschaftsjahr_id=fiscal_year.id,
            booking_date=date(2021, 6, 30),
            description="Alte Buchung",
        )
        session.add(booking)
        session.flush()
        session.add(
            Buchungszeile(
                buchung_id=booking.id,
                position=1,
                account_number="7000",
                side="DEBIT",
                amount=Decimal("10.00"),
            )
        )
        session.commit()

        blocked = ChartOfAccountsRepository(session).delete_accounts(
            company_id=company.company_id,
            account_numbers=("7000", "7001"),
        )

        assert blocked == {
            "7000": ("Buchungen im Geschäftsjahr 2021/2021",)
        }
        assert (
            session.query(Konto)
            .filter(
                Konto.mandant_id == mandant.id,
                Konto.account_number.in_(("7000", "7001")),
            )
            .count()
            == 2
        )
    finally:
        session.close()
        engine.dispose()


def test_blocks_system_tax_and_account_role_references():
    engine, session, company, mandant = _repository_context()
    try:
        session.add(
            KontenrahmenKonfiguration(
                mandant_id=mandant.id,
                opening_balance_account="7000",
                income_summary_account="7003",
                profit_account="7003",
                loss_account="7003",
                profit_loss_carryforward_account="7003",
                statutory_reserve_account="7003",
                other_revenue_reserves_account="7003",
                distribution_liability_account="7003",
                depreciation_expense_account="7003",
                fixed_asset_disposal_gain_account="7003",
                fixed_asset_disposal_loss_account="7003",
                input_tax_7="7003",
                input_tax_19="7001",
                output_tax_7="7003",
                output_tax_19="7003",
            )
        )
        session.add(
            Kontenrolle(
                mandant_id=mandant.id,
                role="CASH",
                account_number="7002",
            )
        )
        session.commit()

        blocked = ChartOfAccountsRepository(session).delete_accounts(
            company_id=company.company_id,
            account_numbers=("7000", "7001", "7002"),
        )

        assert blocked == {
            "7000": ("Eröffnungsbilanzkonto",),
            "7001": ("Vorsteuerkonto 19 %",),
            "7002": ("Kontenrolle CASH",),
        }
        assert (
            session.query(Konto)
            .filter(Konto.mandant_id == mandant.id)
            .count()
            == 4
        )
    finally:
        session.close()
        engine.dispose()


def test_blocks_account_referenced_by_fixed_asset():
    engine, session, company, mandant = _repository_context()
    try:
        session.add(
            Anlagegut(
                fixed_asset_id=str(uuid4()),
                mandant_id=mandant.id,
                asset_code="ANL-1",
                description="Maschine",
                position_code="HGB.266.AKTIVA.A.II.2",
                acquisition_date=date(2020, 1, 1),
                acquisition_cost=Decimal("1000.00"),
                depreciation_start_date=date(2020, 1, 1),
                useful_life_months=120,
                asset_account_number="7000",
                depreciation_expense_account_number="7002",
            )
        )
        session.commit()

        blocked = ChartOfAccountsRepository(session).delete_accounts(
            company_id=company.company_id,
            account_numbers=("7000",),
        )

        assert blocked == {"7000": ("Anlagenkonto ANL-1",)}
        assert (
            session.query(Konto)
            .filter(
                Konto.mandant_id == mandant.id,
                Konto.account_number == "7000",
            )
            .count()
            == 1
        )
    finally:
        session.close()
        engine.dispose()

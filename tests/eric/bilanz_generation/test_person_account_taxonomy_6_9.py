from decimal import Decimal

import pytest

from simpleob.accounting.financial_statement_builder import (
    FinancialStatementBuilder,
)
from simpleob.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from simpleob.accounting.income_statement import IncomeStatement
from simpleob.accounting.ledger import Ledger
from simpleob.accounting.mapper import AccountMapper
from simpleob.domain.account import Account
from simpleob.domain.account_mapping_rule import AccountMappingRule
from simpleob.domain.account_type import AccountType
from simpleob.domain.chart_of_accounts_template import ChartOfAccountsTemplate
from simpleob.domain.person_account_role import PersonAccountRole
from simpleob.domain.template_account import TemplateAccount
from simpleob.eric.bilanz_generation.gaap_ci_6_9_balance_sheet_values import (
    GaapCi69BalanceSheetValueBuilder,
)
from simpleob.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from simpleob.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from simpleob.services.closing_service import ClosingService
from simpleob.services.e_bilanz_account_detail_service import (
    EBilanzAccountDetailService,
)
from simpleob.services.e_bilanz_preparation_service import (
    EBilanzPreparationService,
)


def test_four_person_account_saldos_flow_to_taxonomy_69_and_account_details():
    assets, liabilities = create_hgb_balance_sheet_structure()
    income_statement_root = create_hgb_income_statement_structure()
    positions = HgbFinancialStatementPositionProvider((assets, liabilities))
    receivables = positions.get("HGB.266.AKTIVA.B.II.1")
    payables = positions.get("HGB.266.PASSIVA.C.4")
    bank = positions.get("HGB.266.AKTIVA.B.IV")
    retained_earnings = positions.get("HGB.266.PASSIVA.A.IV")

    template_accounts = (
        TemplateAccount("10000", "Debitor Soll", AccountType.ASSET),
        TemplateAccount("10001", "Debitor Haben", AccountType.ASSET),
        TemplateAccount("70000", "Kreditor Haben", AccountType.LIABILITY),
        TemplateAccount("70001", "Kreditor Soll", AccountType.LIABILITY),
        TemplateAccount("1200", "Bankkonto", AccountType.ASSET),
        TemplateAccount("1800", "Gewinnrücklage", AccountType.EQUITY),
    )
    chart = ChartOfAccountsTemplate(
        "E-Bilanz Testmandant",
        template_accounts,
        account_mapping_rules=(
            AccountMappingRule("1200", bank, None),
            AccountMappingRule("1800", None, retained_earnings),
        ),
        person_account_roles=(
            ("10000", PersonAccountRole.DEBITOR),
            ("10001", PersonAccountRole.DEBITOR),
            ("70000", PersonAccountRole.KREDITOR),
            ("70001", PersonAccountRole.KREDITOR),
        ),
    )
    ledger = Ledger()
    ledger.post("10000", "1800", Decimal("100.00"))
    ledger.post("1800", "10001", Decimal("20.00"))
    ledger.post("1200", "70000", Decimal("60.00"))
    ledger.post("70001", "1800", Decimal("10.00"))
    account_types = {
        account.account_number: account.account_type
        for account in chart.accounts
    }
    statement_builder = FinancialStatementBuilder(AccountMapper(chart))
    preparation = EBilanzPreparationService(
        statement_builder=statement_builder,
        closing_service=ClosingService(),
        account_types=account_types,
        assets=assets,
        liabilities=liabilities,
        income_summary_account_number="8990",
    ).prepare(
        income_statement=IncomeStatement(
            income_statement=income_statement_root,
            amounts={},
        ),
        closed_ledger=ledger,
    )

    assert preparation.balance_sheet_amounts[receivables] == Decimal("110.00")
    assert preparation.balance_sheet_amounts[payables] == Decimal("80.00")
    assert preparation.balance_sheet_amounts[bank] == Decimal("60.00")
    assert preparation.balance_sheet.is_balanced()

    taxonomy_values = GaapCi69BalanceSheetValueBuilder.build(
        balance_sheet=preparation.balance_sheet,
        income_statement=income_statement_root,
    )
    assert taxonomy_values[("bs.ass.currAss.receiv.trade",)] == Decimal("110.00")
    assert taxonomy_values[("bs.eqLiab.liab.trade",)] == Decimal("80.00")
    assert taxonomy_values[("bs.ass.currAss.cashEquiv",)] == Decimal("60.00")

    accounts = tuple(
        Account(
            template=template,
            person_account_role=dict(chart.person_account_roles).get(
                template.account_number
            ),
        )
        for template in template_accounts
    )
    detail_service = EBilanzAccountDetailService(
        account_mapper=AccountMapper(chart),
        accounts=accounts,
    )
    details = detail_service.build_for_e_bilanz(
        pre_closing_ledger=Ledger(),
        closed_ledger=ledger,
    )
    person_details = {
        detail.account_number: detail
        for detail in details
        if detail.account_number in {"10000", "10001", "70000", "70001"}
    }

    assert set(person_details) == {"10000", "10001", "70000", "70001"}
    assert {
        number: detail.position.code
        for number, detail in person_details.items()
    } == {
        "10000": "HGB.266.AKTIVA.B.II.1",
        "10001": "HGB.266.PASSIVA.C.4",
        "70000": "HGB.266.PASSIVA.C.4",
        "70001": "HGB.266.AKTIVA.B.II.1",
    }
    assert {
        number: detail.account_description
        for number, detail in person_details.items()
    } == {
        "10000": "Debitor Soll",
        "10001": "Debitor Haben",
        "70000": "Kreditor Haben",
        "70001": "Kreditor Soll",
    }
    assert {
        number: detail.balance
        for number, detail in person_details.items()
    } == {
        "10000": Decimal("100.00"),
        "10001": Decimal("-20.00"),
        "70000": Decimal("-60.00"),
        "70001": Decimal("10.00"),
    }
    assert len(details) == 6
    # Kontennachweise sind Erläuterungen. Sie werden nicht nochmals in die
    # primären Bilanzwerte oder Taxonomie-Summen addiert.
    assert taxonomy_values[("bs.ass.currAss.receiv.trade",)] == Decimal("110.00")
    assert taxonomy_values[("bs.eqLiab.liab.trade",)] == Decimal("80.00")


def test_ebilanz_preparation_rejects_unclassified_account_without_mapping():
    assets, liabilities = create_hgb_balance_sheet_structure()
    income_statement_root = create_hgb_income_statement_structure()
    chart = ChartOfAccountsTemplate(
        "Unvollständiger Kontenrahmen",
        (TemplateAccount("10000", "Nicht zugeordnet", AccountType.ASSET),),
    )
    ledger = Ledger()
    ledger.get_or_create_account("10000").add_debit(Decimal("50.00"))
    preparation = EBilanzPreparationService(
        statement_builder=FinancialStatementBuilder(AccountMapper(chart)),
        closing_service=ClosingService(),
        account_types={"10000": AccountType.ASSET},
        assets=assets,
        liabilities=liabilities,
        income_summary_account_number="8990",
    )

    with pytest.raises(
        ValueError,
        match="keine gültige Personenkontenzuordnung",
    ):
        preparation.prepare(
            income_statement=IncomeStatement(
                income_statement=income_statement_root,
                amounts={},
            ),
            closed_ledger=ledger,
        )

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.domain.account_mapping_rule import AccountMappingRule

import pytest


def test_account_mapping_rule_may_define_only_debit_position() -> None:
    debit_position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.IV",
        name="Kassenbestand und Guthaben bei Kreditinstituten",
    )

    rule = AccountMappingRule(
        account_number="1200",
        debit_position=debit_position,
        credit_position=None,
    )

    assert rule.debit_position is debit_position
    assert rule.credit_position is None
    
def test_account_mapping_rule_may_define_only_credit_position() -> None:
    credit_position = FinancialStatementPosition(
        code="HGB.266.PASSIVA.C.2",
        name="Verbindlichkeiten gegenüber Kreditinstituten",
    )

    rule = AccountMappingRule(
        account_number="9000",
        debit_position=None,
        credit_position=credit_position,
    )

    assert rule.debit_position is None
    assert rule.credit_position is credit_position
    
def test_account_mapping_rule_requires_at_least_one_target_position() -> None:
    with pytest.raises(
        ValueError,
        match="at least one target position must be defined",
    ):
        AccountMappingRule(
            account_number="1200",
            debit_position=None,
            credit_position=None,
        )
    

def test_account_mapping_rule_requires_string_account_number() -> None:
    debit_position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.IV",
        name="Kassenbestand und Guthaben bei Kreditinstituten",
    )
    credit_position = FinancialStatementPosition(
        code="HGB.266.PASSIVA.C.2",
        name="Verbindlichkeiten gegenüber Kreditinstituten",
    )

    with pytest.raises(TypeError):
        AccountMappingRule(
            account_number=1200,
            debit_position=debit_position,
            credit_position=credit_position,
        )

def test_account_mapping_rule_stores_account_and_target_positions() -> None:
    debit_position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.IV",
        name="Kassenbestand und Guthaben bei Kreditinstituten",
    )
    credit_position = FinancialStatementPosition(
        code="HGB.266.PASSIVA.C.2",
        name="Verbindlichkeiten gegenüber Kreditinstituten",
    )

    rule = AccountMappingRule(
        account_number="1200",
        debit_position=debit_position,
        credit_position=credit_position,
    )

    assert rule.account_number == "1200"
    assert rule.debit_position is debit_position
    assert rule.credit_position is credit_position
    
from decimal import Decimal

import pytest

from openbilanz.accounting.account_balance import AccountBalance
from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.ledger import Ledger
from openbilanz.domain.account import Account
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.template_account import TemplateAccount
from openbilanz.services.e_bilanz_account_detail_service import (
    EBilanzAccountDetailService,
)


class StubAccountMapper:
    def __init__(
        self,
        position: FinancialStatementPosition,
    ) -> None:
        self.position = position
        self.received_balances: list[AccountBalance] = []

    def position_for(
        self,
        balance: AccountBalance,
    ) -> FinancialStatementPosition:
        self.received_balances.append(balance)
        return self.position


def _account(
    number: str,
    name: str,
    account_type: AccountType = AccountType.ASSET,
) -> Account:
    return Account(
        template=TemplateAccount(
            account_number=number,
            name=name,
            account_type=account_type,
        )
    )


def _position() -> FinancialStatementPosition:
    return FinancialStatementPosition(
        code="assets.cash",
        name="Kassenbestand",
    )


def test_builds_account_detail_from_ledger() -> None:
    ledger = Ledger()
    ledger.post("1200", "1800", Decimal("1000.00"))

    mapper = StubAccountMapper(_position())

    service = EBilanzAccountDetailService(
        account_mapper=mapper,
        accounts=(
            _account("1200", "Bank"),
            _account("1800", "Gegenkonto"),
        ),
    )

    details = service.build(ledger=ledger)

    assert len(details) == 2

    assert details[0].account_number == "1200"
    assert details[0].account_description == "Bank"
    assert details[0].balance == Decimal("1000.00")

    assert details[1].account_number == "1800"
    assert details[1].account_description == "Gegenkonto"
    assert details[1].balance == Decimal("-1000.00")

    assert len(mapper.received_balances) == 2


def test_ignores_zero_balance_accounts() -> None:
    ledger = Ledger()
    ledger.post("1200", "1800", Decimal("1000.00"))
    ledger.post("1800", "1200", Decimal("1000.00"))

    mapper = StubAccountMapper(_position())

    service = EBilanzAccountDetailService(
        account_mapper=mapper,
        accounts=(
            _account("1200", "Bank"),
            _account("1800", "Gegenkonto"),
        ),
    )

    assert service.build(ledger=ledger) == ()
    assert mapper.received_balances == []


def test_rejects_missing_account_description() -> None:
    ledger = Ledger()
    ledger.post("1200", "1800", Decimal("1000.00"))

    service = EBilanzAccountDetailService(
        account_mapper=StubAccountMapper(_position()),
        accounts=(
            _account("1200", "Bank"),
        ),
    )

    with pytest.raises(
        ValueError,
        match="Keine Kontenbezeichnung für Konto 1800",
    ):
        service.build(ledger=ledger)


def test_builds_e_bilanz_details_from_pre_and_post_closing_ledgers() -> None:
    pre_closing_ledger = Ledger()
    pre_closing_ledger.post(
        "1200",
        "8400",
        Decimal("1000.00"),
    )
    pre_closing_ledger.post(
        "4930",
        "1200",
        Decimal("200.00"),
    )

    closed_ledger = Ledger()
    closed_ledger.post(
        "1200",
        "0800",
        Decimal("800.00"),
    )

    mapper = StubAccountMapper(_position())

    service = EBilanzAccountDetailService(
        account_mapper=mapper,
        accounts=(
            _account(
                "1200",
                "Bank",
                AccountType.ASSET,
            ),
            _account(
                "0800",
                "Gezeichnetes Kapital",
                AccountType.EQUITY,
            ),
            _account(
                "8400",
                "Erlöse",
                AccountType.REVENUE,
            ),
            _account(
                "4930",
                "Bürobedarf",
                AccountType.EXPENSE,
            ),
        ),
    )

    details = service.build_for_e_bilanz(
        pre_closing_ledger=pre_closing_ledger,
        closed_ledger=closed_ledger,
    )

    details_by_account = {
        detail.account_number: detail
        for detail in details
    }

    assert set(details_by_account) == {
        "0800",
        "1200",
        "4930",
        "8400",
    }

    assert details_by_account["8400"].balance == Decimal(
        "-1000.00"
    )
    assert details_by_account["4930"].balance == Decimal(
        "200.00"
    )
    assert details_by_account["1200"].balance == Decimal(
        "800.00"
    )
    assert details_by_account["0800"].balance == Decimal(
        "-800.00"
    )

    assert (
        details_by_account["8400"].account_description
        == "Erlöse"
    )
    assert (
        details_by_account["4930"].account_description
        == "Bürobedarf"
    )
    assert (
        details_by_account["1200"].account_description
        == "Bank"
    )
    assert (
        details_by_account["0800"].account_description
        == "Gezeichnetes Kapital"
    )

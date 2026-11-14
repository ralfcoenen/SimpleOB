"""Tests für GAAP-CI-Unterpositionswerte aus Kontennachweisen."""

from decimal import Decimal

import pytest

from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.domain.e_bilanz_account_detail import (
    EBilanzAccountDetail,
)
from simpleob.eric.bilanz_generation.gaap_ci_6_9_account_detail_values import (
    GaapCi69AccountDetailValueBuilder,
)


def _detail(
    *,
    position_code: str,
    account_number: str,
    account_description: str,
    balance: str,
) -> EBilanzAccountDetail:
    return EBilanzAccountDetail(
        position=FinancialStatementPosition(
            code=position_code,
            name=position_code,
        ),
        account_number=account_number,
        account_description=account_description,
        balance=Decimal(balance),
    )


def test_builds_bga_value() -> None:
    details = (
        _detail(
            position_code="HGB.266.AKTIVA.A.II.3",
            account_number="0400",
            account_description=(
                "Betriebs- und Geschäftsausstattung"
            ),
            balance="5000.00",
        ),
    )

    values = GaapCi69AccountDetailValueBuilder.build(
        account_details=details,
    )

    assert values == {
        (
            "bs.ass.fixAss.tan.otherEquipm.otherbga",
        ): Decimal("5000.00"),
    }


def test_splits_other_and_tax_liabilities() -> None:
    details = (
        _detail(
            position_code="HGB.266.PASSIVA.C.8",
            account_number="1700",
            account_description="Sonstige Verbindlichkeiten",
            balance="-4000.00",
        ),
        _detail(
            position_code="HGB.266.PASSIVA.C.8",
            account_number="1776",
            account_description="Umsatzsteuer 19 %",
            balance="-798.32",
        ),
        _detail(
            position_code="HGB.266.PASSIVA.C.8",
            account_number="3840",
            account_description="Umsatzsteuer laufendes Jahr",
            balance="-3247.93",
        ),
        _detail(
            position_code="HGB.266.PASSIVA.C.8",
            account_number="3841",
            account_description="Umsatzsteuerverbindlichkeiten Vorjahr",
            balance="-100.00",
        ),
        _detail(
            position_code="HGB.266.AKTIVA.B.II.4",
            account_number="3840",
            account_description="Umsatzsteuer laufendes Jahr",
            balance="3247.93",
        ),
    )

    values = GaapCi69AccountDetailValueBuilder.build(
        account_details=details,
        tax_liability_accounts=(
            "1771",
            "1776",
            "3840",
            "3841",
        ),
    )

    assert values == {
        (
            "bs.eqLiab.liab.other.other",
        ): Decimal("4000.00"),
        (
            "bs.eqLiab.liab.other.theroffTax",
        ): Decimal("4146.25"),
    }

def test_build_maps_general_rate_sales_to_value_bearing_chain() -> None:
    detail = EBilanzAccountDetail(
        position=FinancialStatementPosition(
            code="HGB.275.GKV.1",
            name="Umsatzerlöse",
        ),
        account_number="8400",
        account_description="Umsatzerlöse 19 %",
        balance=Decimal("-4201.68"),
    )

    values = GaapCi69AccountDetailValueBuilder.build(
        account_details=(detail,),
        general_rate_sales_accounts=("8400",),
    )

    assert values == {
        (
            "is.netIncome.regular.operatingTC."
            "grossTradingProfit.totalOutput",
        ): Decimal("4201.68"),
        (
            "is.netIncome.regular.operatingTC."
            "grossTradingProfit.totalOutput.netSales",
        ): Decimal("4201.68"),
        (
            "is.netIncome.regular.operatingTC."
            "grossTradingProfit.totalOutput.netSales."
            "grossSales",
        ): Decimal("4201.68"),
        (
            "is.netIncome.regular.operatingTC."
            "grossTradingProfit.totalOutput.netSales."
            "grossSales.generalRateVAT",
        ): Decimal("4201.68"),
    }

def test_adds_multiple_accounts_for_same_concept() -> None:
    details = (
        _detail(
            position_code="HGB.266.PASSIVA.C.8",
            account_number="1700",
            account_description="Sonstige Verbindlichkeiten",
            balance="-3000.00",
        ),
        _detail(
            position_code="HGB.266.PASSIVA.C.8",
            account_number="1710",
            account_description="Weitere Verbindlichkeiten",
            balance="-1000.00",
        ),
    )

    values = GaapCi69AccountDetailValueBuilder.build(
        account_details=details,
    )

    assert values == {
        (
            "bs.eqLiab.liab.other.other",
        ): Decimal("4000.00"),
    }


def test_ignores_unrelated_positions() -> None:
    details = (
        _detail(
            position_code="HGB.266.AKTIVA.B.IV",
            account_number="1200",
            account_description="Bank",
            balance="15000.00",
        ),
    )

    values = GaapCi69AccountDetailValueBuilder.build(
        account_details=details,
    )

    assert values == {}


def test_rejects_non_tuple_account_details() -> None:
    with pytest.raises(
        TypeError,
        match="account_details must be a tuple",
    ):
        GaapCi69AccountDetailValueBuilder.build(
            account_details=[],
        )


def test_rejects_invalid_account_detail() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "account_details must contain "
            "EBilanzAccountDetail objects"
        ),
    ):
        GaapCi69AccountDetailValueBuilder.build(
            account_details=("invalid",),
        )


def test_rejects_empty_configured_account_number() -> None:
    with pytest.raises(
        ValueError,
        match="account numbers must not be empty",
    ):
        GaapCi69AccountDetailValueBuilder.build(
            account_details=(),
            tax_liability_accounts=(" ",),
        )

def test_uses_explicit_account_taxonomy_concept_as_fallback() -> None:
    detail = _detail(
        position_code="HGB.266.AKTIVA.B.II.1",
        account_number="1400",
        account_description="Forderungen aus Lieferungen und Leistungen",
        balance="2500.00",
    )

    values = GaapCi69AccountDetailValueBuilder.build(
        account_details=(detail,),
        account_taxonomy_concepts={
            "1400": (
                "bs.ass.currAss.receiv.trade.other"
            ),
        },
    )

    assert values == {
        (
            "bs.ass.currAss.receiv.trade.other",
        ): Decimal("2500.00"),
    }


def test_rolls_deep_taxonomy_values_up_without_double_counting() -> None:
    lease_fix_other = (
        "is.netIncome.regular.operatingTC."
        "otherCost.leaseFix.other"
    )
    lease_fix = (
        "is.netIncome.regular.operatingTC."
        "otherCost.leaseFix"
    )
    lease_movable_other = (
        "is.netIncome.regular.operatingTC."
        "otherCost.leaseMoveable.other"
    )
    lease_movable = (
        "is.netIncome.regular.operatingTC."
        "otherCost.leaseMovable"
    )

    details = (
        _detail(
            position_code="HGB.275.GKV.8",
            account_number="6310",
            account_description="Miete unbewegliche Wirtschaftsgüter",
            balance="700.00",
        ),
        _detail(
            position_code="HGB.275.GKV.8",
            account_number="6311",
            account_description="Weitere Miete unbewegliche Wirtschaftsgüter",
            balance="500.00",
        ),
        _detail(
            position_code="HGB.275.GKV.8",
            account_number="6835",
            account_description="Miete bewegliche Wirtschaftsgüter",
            balance="800.00",
        ),
    )

    values = GaapCi69AccountDetailValueBuilder.build(
        account_details=details,
        account_taxonomy_concepts={
            "6310": lease_fix_other,
            "6311": lease_fix_other,
            "6835": lease_movable_other,
        },
        account_taxonomy_calculation_ancestors={
            "6310": ((lease_fix, Decimal("1")),),
            "6311": ((lease_fix, Decimal("1")),),
            "6835": ((lease_movable, Decimal("1")),),
        },
    )

    assert values == {
        (lease_fix_other,): Decimal("1200.00"),
        (lease_fix,): Decimal("1200.00"),
        (lease_movable_other,): Decimal("800.00"),
        (lease_movable,): Decimal("800.00"),
    }
    assert (
        "is.netIncome.regular.operatingTC.otherCost",
    ) not in values

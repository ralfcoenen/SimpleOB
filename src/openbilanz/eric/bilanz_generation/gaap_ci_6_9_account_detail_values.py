"""Werthaltige GAAP-CI-Unterpositionen aus SimpleOB-Kontennachweisen."""

from __future__ import annotations

from collections.abc import Iterable

from openbilanz.domain.e_bilanz_account_detail import (
    EBilanzAccountDetail,
)
from openbilanz.domain.money import ZERO
from openbilanz.eric.bilanz_generation.fact_plan_resolver import (
    FactPlanPath,
    FactPlanValue,
)


class GaapCi69AccountDetailValueBuilder:
    """Erzeugt ERiC-relevante GAAP-CI-Werte aus Einzelkontensalden."""

    _BGA_POSITION = "HGB.266.AKTIVA.A.II.3"
    _OTHER_LIABILITIES_POSITION = "HGB.266.PASSIVA.C.8"
    _SALES_POSITION = "HGB.275.GKV.1"

    _BGA_CONCEPT = (
        "bs.ass.fixAss.tan.otherEquipm.otherbga"
    )
    _OTHER_LIABILITIES_CONCEPT = (
        "bs.eqLiab.liab.other.other"
    )
    _TAX_LIABILITIES_CONCEPT = (
        "bs.eqLiab.liab.other.theroffTax"
    )
    _GENERAL_RATE_SALES_CONCEPTS = (
        (
            "is.netIncome.regular.operatingTC."
            "grossTradingProfit.totalOutput"
        ),
        (
            "is.netIncome.regular.operatingTC."
            "grossTradingProfit.totalOutput.netSales"
        ),
        (
            "is.netIncome.regular.operatingTC."
            "grossTradingProfit.totalOutput.netSales."
            "grossSales"
        ),
        (
            "is.netIncome.regular.operatingTC."
            "grossTradingProfit.totalOutput.netSales."
            "grossSales.generalRateVAT"
        ),
    )
    @classmethod
    def build(
        cls,
        *,
        account_details: tuple[EBilanzAccountDetail, ...],
        tax_liability_accounts: Iterable[str] = (),
        general_rate_sales_accounts: Iterable[str] = (),
    ) -> dict[FactPlanPath, FactPlanValue]:
        """Erzeugt die konkret ableitbaren GAAP-CI-Unterpositionen."""

        if not isinstance(account_details, tuple):
            raise TypeError(
                "account_details must be a tuple"
            )

        for detail in account_details:
            if not isinstance(detail, EBilanzAccountDetail):
                raise TypeError(
                    "account_details must contain "
                    "EBilanzAccountDetail objects"
                )

        tax_accounts = cls._normalize_account_numbers(
            tax_liability_accounts
        )
        sales_accounts = cls._normalize_account_numbers(
            general_rate_sales_accounts
        )

        values: dict[FactPlanPath, FactPlanValue] = {}

        for detail in account_details:
            if detail.balance == ZERO:
                continue

            position_code = detail.position.code
            account_number = detail.account_number

            if position_code == cls._BGA_POSITION:
                cls._add_value(
                    values=values,
                    concept_name=cls._BGA_CONCEPT,
                    amount=detail.balance,
                )
                continue

            if position_code == cls._OTHER_LIABILITIES_POSITION:
                concept_name = (
                    cls._TAX_LIABILITIES_CONCEPT
                    if account_number in tax_accounts
                    else cls._OTHER_LIABILITIES_CONCEPT
                )

                cls._add_value(
                    values=values,
                    concept_name=concept_name,
                    amount=abs(detail.balance),
                )
                continue
            if (
                position_code == cls._SALES_POSITION
                and account_number in sales_accounts
            ):
                for concept_name in cls._GENERAL_RATE_SALES_CONCEPTS:
                    cls._add_value(
                        values=values,
                        concept_name=concept_name,
                        amount=abs(detail.balance),
                    )
        return values

    @staticmethod
    def _normalize_account_numbers(
        account_numbers: Iterable[str],
    ) -> frozenset[str]:
        result: set[str] = set()

        for account_number in account_numbers:
            if not isinstance(account_number, str):
                raise TypeError(
                    "account numbers must be strings"
                )

            normalized = account_number.strip()

            if not normalized:
                raise ValueError(
                    "account numbers must not be empty"
                )

            result.add(normalized)

        return frozenset(result)

    @staticmethod
    def _add_value(
        *,
        values: dict[FactPlanPath, FactPlanValue],
        concept_name: str,
        amount,
    ) -> None:
        path = (concept_name,)

        previous = values.get(path)

        if previous is None:
            values[path] = amount
            return

        values[path] = previous + amount

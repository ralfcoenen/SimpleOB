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
    _CASH_POSITION = "HGB.266.AKTIVA.B.IV"
    _INPUT_TAX_RECEIVABLE_POSITION = "HGB.266.AKTIVA.B.II.4"

    _CASH_CONCEPT = (
        "bs.ass.currAss.cashEquiv.cash"
    )
    _BANK_CONCEPT = (
        "bs.ass.currAss.cashEquiv.bank"
    )
    _INPUT_TAX_RECEIVABLE_CONCEPT = (
        "bs.ass.currAss.receiv.other.vat"
    )


    @classmethod
    def build(
        cls,
        *,
        account_details: tuple[EBilanzAccountDetail, ...],
        tax_liability_accounts: Iterable[str] = (),
        general_rate_sales_accounts: Iterable[str] = (),
        cash_accounts: Iterable[str] = (),
        bank_accounts: Iterable[str] = (),
        input_tax_receivable_accounts: Iterable[str] = (),
        account_taxonomy_concepts: dict[str, str] | None = None,
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
        cash_account_numbers = cls._normalize_account_numbers(
            cash_accounts
        )
        bank_account_numbers = cls._normalize_account_numbers(
            bank_accounts
        )
        input_tax_accounts = cls._normalize_account_numbers(
            input_tax_receivable_accounts
        )
        taxonomy_concepts = cls._normalize_taxonomy_concepts(
            account_taxonomy_concepts
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

            if position_code == cls._CASH_POSITION:
                if account_number in cash_account_numbers:
                    cls._add_value(
                        values=values,
                        concept_name=cls._CASH_CONCEPT,
                        amount=abs(detail.balance),
                    )
                    continue

                if account_number in bank_account_numbers:
                    cls._add_value(
                        values=values,
                        concept_name=cls._BANK_CONCEPT,
                        amount=abs(detail.balance),
                    )
                    continue

            if (
                position_code
                == cls._INPUT_TAX_RECEIVABLE_POSITION
                and account_number in input_tax_accounts
            ):
                cls._add_value(
                    values=values,
                    concept_name=cls._INPUT_TAX_RECEIVABLE_CONCEPT,
                    amount=abs(detail.balance),
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
                continue
            concept_name = taxonomy_concepts.get(
                account_number
            )
            if concept_name is not None:
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
    def _normalize_taxonomy_concepts(
        account_taxonomy_concepts: dict[str, str] | None,
    ) -> dict[str, str]:
        if account_taxonomy_concepts is None:
            return {}

        if not isinstance(
            account_taxonomy_concepts,
            dict,
        ):
            raise TypeError(
                "account_taxonomy_concepts must be a dict"
            )

        result: dict[str, str] = {}

        for account_number, concept_name in (
            account_taxonomy_concepts.items()
        ):
            if not isinstance(account_number, str):
                raise TypeError(
                    "taxonomy account numbers must be strings"
                )

            if not isinstance(concept_name, str):
                raise TypeError(
                    "taxonomy concept names must be strings"
                )

            normalized_account_number = (
                account_number.strip()
            )
            normalized_concept_name = (
                concept_name.strip()
            )

            if not normalized_account_number:
                raise ValueError(
                    "taxonomy account numbers must not be empty"
                )

            if not normalized_concept_name:
                raise ValueError(
                    "taxonomy concept names must not be empty"
                )

            result[
                normalized_account_number
            ] = normalized_concept_name

        return result

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

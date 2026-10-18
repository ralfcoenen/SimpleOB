from datetime import date
from decimal import Decimal

from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.domain.e_bilanz_account_detail import (
    EBilanzAccountDetail,
)
from simpleob.taxonomy.account_balance_builder import (
    AccountBalanceBuilder,
)
from simpleob.taxonomy.concept import (
    TaxonomyBalance,
    TaxonomyConcept,
    TaxonomyPeriodType,
)
from simpleob.taxonomy.concept_set import TaxonomyConceptSet
from simpleob.taxonomy.context import TaxonomyContext
from simpleob.taxonomy.label_set import TaxonomyLabelSet
from simpleob.taxonomy.model import TaxonomyModel
from simpleob.taxonomy.presentation_set import (
    TaxonomyPresentationSet,
)


class StubTaxonomyMapper:
    def __init__(
        self,
        concept: TaxonomyConcept,
    ) -> None:
        self.concept = concept

    def concept_for(
        self,
        position: FinancialStatementPosition,
    ) -> TaxonomyConcept:
        return self.concept


def _concept(
    *,
    name: str,
    concept_id: str,
    type_name: str,
) -> TaxonomyConcept:
    return TaxonomyConcept(
        name=name,
        concept_id=concept_id,
        type_name=type_name,
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=None,
        abstract=False,
        nillable=True,
    )


def _taxonomy_model(
    *concepts: TaxonomyConcept,
) -> TaxonomyModel:
    return TaxonomyModel(
        concepts=TaxonomyConceptSet(
            concepts=concepts,
        ),
        labels=TaxonomyLabelSet(
            labels=(),
        ),
        presentation=TaxonomyPresentationSet(
            relations=(),
        ),
    )


def test_builds_account_balance_tuple() -> None:
    position = FinancialStatementPosition(
        code="assets.cash",
        name="Bank",
    )

    detail = EBilanzAccountDetail(
        position=position,
        account_number="1200",
        account_description="Bank",
        balance=Decimal("1000.00"),
    )

    target_concept = TaxonomyConcept(
        name="bs.ass.currAss.cashEquiv.bank",
        concept_id="de-gaap-ci_bs.ass.currAss.cashEquiv.bank",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.INSTANT,
        balance=TaxonomyBalance.DEBIT,
        abstract=False,
        nillable=True,
    )

    taxonomy_model = _taxonomy_model(
        _concept(
            name=(
                "detailedInformation."
                "accountbalances.positionName"
            ),
            concept_id="position-name",
            type_name="xbrli:QNameItemType",
        ),
        _concept(
            name=(
                "detailedInformation."
                "accountbalances.accountNumber"
            ),
            concept_id="account-number",
            type_name="xbrli:stringItemType",
        ),
        _concept(
            name=(
                "detailedInformation."
                "accountbalances.accountDescription"
            ),
            concept_id="account-description",
            type_name="xbrli:stringItemType",
        ),
        _concept(
            name=(
                "detailedInformation."
                "accountbalances.amount"
            ),
            concept_id="amount",
            type_name="xbrli:monetaryItemType",
        ),
        _concept(
            name=(
                "detailedInformation."
                "accountbalances.notPossible"
            ),
            concept_id="not-possible",
            type_name="xbrli:booleanItemType",
        ),
    )

    context = TaxonomyContext(
        entity_identifier="company",
        entity_scheme="urn:test",
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    builder = AccountBalanceBuilder(
        taxonomy_model=taxonomy_model,
        taxonomy_mapper=StubTaxonomyMapper(
            target_concept
        ),
    )

    result = builder.build(
        detail=detail,
        context=context,
    )

    assert result.position_name.value == (
        "de-gaap-ci:bs.ass.currAss.cashEquiv.bank"
    )
    assert result.account_number.value == "1200"
    assert result.account_description.value == "Bank"
    assert result.amount.amount == Decimal("1000.00")
    assert result.amount.unit.measure == "iso4217:EUR"
    assert result.not_possible.value == "false"

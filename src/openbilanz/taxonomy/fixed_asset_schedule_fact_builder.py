"""E-Bilanz-Facts des Anlagenspiegels."""

from datetime import date
from decimal import Decimal

from openbilanz.reporting.fixed_asset_schedule import (
    FixedAssetSchedule,
    FixedAssetScheduleRow,
)
from openbilanz.taxonomy.concept import TaxonomyPeriodType
from openbilanz.taxonomy.context import TaxonomyContext
from openbilanz.taxonomy.context_dimension import (
    TaxonomyContextDimension,
)
from openbilanz.taxonomy.fact import TaxonomyFact
from openbilanz.taxonomy.model import TaxonomyModel
from openbilanz.taxonomy.unit import TaxonomyUnit


class FixedAssetScheduleFactBuilder:
    """Erzeugt dimensionale GAAP-CI-Facts des Anlagenspiegels."""

    _POSITION_MEMBERS = {
        "HGB.266.AKTIVA.A.II.2": (
            "de-gaap-ci:bs.ass.fixAss.tan.machinery"
        ),
        "HGB.266.AKTIVA.A.II.3": (
            "de-gaap-ci:bs.ass.fixAss.tan.otherEquipm"
        ),
    }

    _VALUE_CONCEPT_IDS = {
        "opening_cost": (
            "de-gaap-ci_grossCost.beginning_short"
        ),
        "additions": (
            "de-gaap-ci_gross.addition_short"
        ),
        "disposals": (
            "de-gaap-ci_gross.release_short"
        ),
        "current_depreciation": (
            "de-gaap-ci_accDepr.DeprPeriod_short"
        ),
    }

    def __init__(
        self,
        *,
        taxonomy_model: TaxonomyModel,
    ) -> None:
        self._taxonomy_model = taxonomy_model

    def build(
        self,
        *,
        schedule: FixedAssetSchedule,
        entity_identifier: str,
        entity_scheme: str,
        fiscal_year_start: date,
        fiscal_year_end: date,
        unit: TaxonomyUnit,
    ) -> tuple[TaxonomyFact, ...]:
        """Erzeugt die Facts des Kurzform-Anlagenspiegels."""

        facts: list[TaxonomyFact] = []

        for row in schedule.rows:
            facts.extend(
                self._facts_for_row(
                    row=row,
                    entity_identifier=entity_identifier,
                    entity_scheme=entity_scheme,
                    fiscal_year_start=fiscal_year_start,
                    fiscal_year_end=fiscal_year_end,
                    unit=unit,
                )
            )

        return tuple(facts)

    def _facts_for_row(
        self,
        *,
        row: FixedAssetScheduleRow,
        entity_identifier: str,
        entity_scheme: str,
        fiscal_year_start: date,
        fiscal_year_end: date,
        unit: TaxonomyUnit,
    ) -> tuple[TaxonomyFact, ...]:
        member = self._POSITION_MEMBERS.get(
            row.position_code
        )

        if member is None:
            raise ValueError(
                "Keine E-Bilanz-Anlagenspiegel-Zuordnung "
                f"für HGB-Position {row.position_code}."
            )

        context = TaxonomyContext(
            entity_identifier=entity_identifier,
            entity_scheme=entity_scheme,
            period_type=TaxonomyPeriodType.DURATION,
            start_date=fiscal_year_start,
            end_date=fiscal_year_end,
            dimensions=(
                TaxonomyContextDimension(
                    dimension=(
                        "de-gaap-ci:dim_taxTrans"
                    ),
                    member="de-gaap-ci:dim_comBal",
                ),
                TaxonomyContextDimension(
                    dimension=(
                        "de-gaap-ci:"
                        "dim_changes.nt.ass.gross_short"
                    ),
                    member=member,
                ),
            ),
        )

        values = {
            "opening_cost": row.opening_cost,
            "additions": row.additions,
            "disposals": row.disposals,
            "current_depreciation": (
                row.current_depreciation
            ),
        }

        facts: list[TaxonomyFact] = []

        for field_name, amount in values.items():
            if amount == Decimal("0.00"):
                continue

            concept_id = self._VALUE_CONCEPT_IDS[
                field_name
            ]

            concept = (
                self._taxonomy_model.concepts.by_id(
                    concept_id
                )
            )

            if concept is None:
                raise ValueError(
                    "Anlagenspiegel-Concept wurde "
                    f"nicht gefunden: {concept_id}"
                )

            facts.append(
                TaxonomyFact(
                    concept=concept,
                    amount=amount,
                    context=context,
                    unit=unit,
                )
            )

        return tuple(facts)

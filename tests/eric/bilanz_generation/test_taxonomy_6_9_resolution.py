"""Integrationstest für Profil, Werte und Resolver der Taxonomie 6.9."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from openbilanz.domain.company import Company
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.eric.bilanz_generation.fact_plan_resolver import (
    FactPlanResolver,
)
from openbilanz.eric.bilanz_generation.gaap_ci_6_9_values import (
    GaapCi69Values,
)
from openbilanz.eric.bilanz_generation.taxonomy_6_9 import (
    create_profile_6_9,
)
from openbilanz.eric.bilanz_generation.taxonomy_6_9_values import (
    Taxonomy69ValueBuilder,
)
from openbilanz.taxonomy.arelle_adapter import ArelleAdapter
from openbilanz.taxonomy.concept import TaxonomyPeriodType
from openbilanz.taxonomy.concept_set import TaxonomyConceptSet
from openbilanz.taxonomy.context import TaxonomyContext
from openbilanz.taxonomy.gcd_company_data import GcdCompanyData
from openbilanz.taxonomy.gcd_company_identifiers import (
    GcdCompanyIdentifiers,
)
from openbilanz.taxonomy.gcd_report_profile import GcdReportProfile
from openbilanz.taxonomy.resolver import TaxonomyResolver
from openbilanz.taxonomy.taxonomy import TaxonomyVersion

TAXONOMY_ROOT = Path(
    "data/taxonomy"
).resolve()

GCD_69_ENTRY_POINT = (
    TAXONOMY_ROOT
    / "6.9"
    / "de-gcd-2025-04-01"
    / "de-gcd-2025-04-01-shell.xsd"
)

TEST_ENTITY_SCHEME = "urn:openbilanz:company-id"


@pytest.mark.integration
def test_standard_69_values_can_be_resolved_against_profile() -> None:
    """Standarddaten lassen sich vollständig gegen das 6.9-Profil auflösen."""

    version_root = TAXONOMY_ROOT / "6.9"

    if not version_root.is_dir():
        pytest.skip(
            "Taxonomy 6.9 is not installed locally"
        )

    if not GCD_69_ENTRY_POINT.is_file():
        pytest.skip(
            "Taxonomy 6.9 GCD entry point is not installed locally"
        )

    profile = create_profile_6_9()

    company_data = GcdCompanyData(
        company=Company(
            company_id=uuid4(),
            name="Beispiel UG",
        ),
        tax_number="5123045678901",
        legal_form="UG (haftungsbeschränkt)",
        street="Musterstraße",
        house_number="12",
        postal_code="52351",
        city="Düren",
        country="Deutschland",
        business="Softwareentwicklung",
    )

    identifiers = GcdCompanyIdentifiers(
        tax_number_13="5123045678901",
    )

    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    gaap_ci_values = GaapCi69Values(
        net_income=Decimal("4500.00"),
        earnings_after_taxes=Decimal("4600.00"),
        operating_total_cost=Decimal("5000.00"),
        gross_trading_profit=Decimal("6000.00"),
    )

    values = Taxonomy69ValueBuilder.build(
        company_data=company_data,
        identifiers=identifiers,
        fiscal_year=fiscal_year,
        report_profile=GcdReportProfile.standard(),
        gaap_ci_values=gaap_ci_values,
    )

    taxonomy_resolver = TaxonomyResolver(
        root=TAXONOMY_ROOT,
    )

    gaap_ci_entry_point = (
        taxonomy_resolver.gaap_ci_fiscal_entry_point(
            TaxonomyVersion.V6_9
        )
    )

    adapter = ArelleAdapter()

    try:
        gcd_model = adapter.model(
            GCD_69_ENTRY_POINT
        )

        gaap_ci_model = adapter.model(
            gaap_ci_entry_point
        )
    finally:
        adapter.close()

    concepts = TaxonomyConceptSet(
        concepts=(
            gcd_model.concepts.concepts
            + gaap_ci_model.concepts.concepts
        ),
    )

    entity_identifier = str(
        company_data.company.company_id
    )

    instant_context = TaxonomyContext(
        entity_identifier=entity_identifier,
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.INSTANT,
        start_date=None,
        end_date=fiscal_year.end_date,
    )

    duration_context = TaxonomyContext(
        entity_identifier=entity_identifier,
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=fiscal_year.start_date,
        end_date=fiscal_year.end_date,
    )

    resolved = FactPlanResolver.resolve(
        fact_plan=profile.fact_plan,
        concepts=concepts,
        contexts={
            TaxonomyPeriodType.INSTANT: instant_context,
            TaxonomyPeriodType.DURATION: duration_context,
        },
        values=values,
    )

    assert resolved.nodes

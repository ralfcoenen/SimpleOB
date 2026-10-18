"""Integrationstest für die neue XBRL-Serialisierung der Taxonomie 6.9."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from simpleob.domain.company import Company
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.eric.bilanz_generation.fact_plan_resolver import (
    FactPlanResolver,
)
from simpleob.eric.bilanz_generation.gaap_ci_6_9_values import (
    GaapCi69Values,
)
from simpleob.eric.bilanz_generation.resolved_fact_plan_xbrl_serializer import (
    ResolvedFactPlanXbrlSerializer,
)
from simpleob.eric.bilanz_generation.taxonomy_6_9 import (
    create_profile_6_9,
)
from simpleob.eric.bilanz_generation.taxonomy_6_9_values import (
    Taxonomy69ValueBuilder,
)
from simpleob.taxonomy.arelle_adapter import ArelleAdapter
from simpleob.taxonomy.concept import TaxonomyPeriodType
from simpleob.taxonomy.concept_set import TaxonomyConceptSet
from simpleob.taxonomy.context import TaxonomyContext
from simpleob.taxonomy.gcd_company_data import GcdCompanyData
from simpleob.taxonomy.gcd_company_identifiers import (
    GcdCompanyIdentifiers,
)
from simpleob.taxonomy.gcd_report_profile import GcdReportProfile
from simpleob.taxonomy.resolver import TaxonomyResolver
from simpleob.taxonomy.taxonomy import TaxonomyVersion
from simpleob.taxonomy.unit import TaxonomyUnit

TAXONOMY_ROOT = Path(
    "data/taxonomy"
).resolve()

GCD_69_ENTRY_POINT = (
    TAXONOMY_ROOT
    / "6.9"
    / "de-gcd-2025-04-01"
    / "de-gcd-2025-04-01-shell.xsd"
)

GCD_NAMESPACE = (
    "http://www.xbrl.de/taxonomies/"
    "de-gcd-2025-04-01"
)

GAAP_CI_NAMESPACE = (
    "http://www.xbrl.de/taxonomies/"
    "de-gaap-ci-2025-04-01"
)

XSI_NAMESPACE = (
    "http://www.w3.org/2001/XMLSchema-instance"
)

TEST_ENTITY_SCHEME = "urn:openbilanz:company-id"


@pytest.mark.integration
def test_standard_69_profile_can_be_serialized_to_xbrl_elements() -> None:
    """Das echte 6.9-Profil wird bis zu konkreten XML-Elementen aufgelöst."""

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

    contexts = {
        "ctx-instant-2026": instant_context,
        "ctx-duration-2026": duration_context,
    }

    resolved = FactPlanResolver.resolve(
        fact_plan=profile.fact_plan,
        concepts=concepts,
        contexts={
            TaxonomyPeriodType.INSTANT: instant_context,
            TaxonomyPeriodType.DURATION: duration_context,
        },
        values=values,
    )

    eur_unit = TaxonomyUnit.eur()
    pure_unit = TaxonomyUnit.pure()

    serializer = ResolvedFactPlanXbrlSerializer()

    elements = serializer.serialize(
        resolved_fact_plan=resolved,
        contexts=contexts,
        units={
            "EUR": eur_unit,
            "PURE": pure_unit,
        },
        taxonomy_namespace=GAAP_CI_NAMESPACE,
        taxonomy_namespaces={
            "de-gcd": GCD_NAMESPACE,
            "de-gaap-ci": GAAP_CI_NAMESPACE,
        },
    )

    assert elements

    elements_by_tag = {
        element.tag: element
        for element in elements
    }

    company_name = elements_by_tag[
        f"{{{GCD_NAMESPACE}}}"
        "genInfo.company.id.name"
    ]

    assert company_name.text == "Beispiel UG"
    assert company_name.attrib["contextRef"] == (
        "ctx-duration-2026"
    )

    net_income = elements_by_tag[
        f"{{{GAAP_CI_NAMESPACE}}}"
        "is.netIncome"
    ]

    assert net_income.text == "4500.00"
    assert net_income.attrib["contextRef"] == (
        "ctx-duration-2026"
    )
    assert net_income.attrib["unitRef"] == "EUR"
    assert net_income.attrib["decimals"] == "2"

    according_to = elements_by_tag[
        f"{{{GCD_NAMESPACE}}}"
        "genInfo.report.id.accordingTo"
    ]

    assert "contextRef" not in according_to.attrib

    according_to_id_no = according_to.find(
        f"{{{GCD_NAMESPACE}}}"
        "genInfo.report.id.accordingTo.idNo"
    )

    assert according_to_id_no is not None
    assert "contextRef" not in according_to_id_no.attrib

    according_to_st13 = according_to_id_no.find(
        f"{{{GCD_NAMESPACE}}}"
        "genInfo.company.id.idNo.type.companyId.ST13"
    )

    assert according_to_st13 is not None
    assert according_to_st13.attrib[
        f"{{{XSI_NAMESPACE}}}nil"
    ] == "true"

    country_iso = elements_by_tag[
        f"{{{GCD_NAMESPACE}}}"
        "genInfo.company.id.location.country.isoCode"
    ]

    assert country_iso.attrib[
        f"{{{XSI_NAMESPACE}}}nil"
    ] == "true"

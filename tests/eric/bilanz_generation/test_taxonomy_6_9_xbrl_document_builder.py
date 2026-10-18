"""Integrationstest für die vollständige neue 6.9-XBRL-Instanz."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
from xml.etree import ElementTree as ET

import pytest

from simpleob.domain.company import Company
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.eric.bilanz_generation.fact_plan_resolver import (
    FactPlanResolver,
)
from simpleob.eric.bilanz_generation.gaap_ci_6_9_values import (
    GaapCi69Values,
)
from simpleob.eric.bilanz_generation.taxonomy_6_9 import (
    create_profile_6_9,
)
from simpleob.eric.bilanz_generation.taxonomy_6_9_values import (
    Taxonomy69ValueBuilder,
)
from simpleob.eric.bilanz_generation.taxonomy_6_9_xbrl_document_builder import (
    GAAP_CI_69_NAMESPACE,
    GCD_69_NAMESPACE,
    Taxonomy69XbrlDocumentBuilder,
)
from simpleob.taxonomy.arelle_adapter import ArelleAdapter
from simpleob.taxonomy.concept import TaxonomyPeriodType
from simpleob.taxonomy.concept_set import TaxonomyConceptSet
from simpleob.taxonomy.context import TaxonomyContext
from simpleob.taxonomy.entry_point import TaxonomyEntryPoint
from simpleob.taxonomy.gcd_company_data import GcdCompanyData
from simpleob.taxonomy.gcd_company_identifiers import (
    GcdCompanyIdentifiers,
)
from simpleob.taxonomy.gcd_report_profile import GcdReportProfile
from simpleob.taxonomy.resolver import TaxonomyResolver
from simpleob.taxonomy.taxonomy import TaxonomyVersion
from simpleob.taxonomy.unit import TaxonomyUnit
from simpleob.taxonomy.xbrl_writer import (
    LINK_NAMESPACE,
    XBRLI_NAMESPACE,
    XLINK_NAMESPACE,
    XSI_NAMESPACE,
)

TAXONOMY_ROOT = Path(
    "data/taxonomy"
).resolve()

GCD_69_ENTRY_POINT_PATH = (
    TAXONOMY_ROOT
    / "6.9"
    / "de-gcd-2025-04-01"
    / "de-gcd-2025-04-01-shell.xsd"
)

TEST_ENTITY_SCHEME = (
    "urn:openbilanz:company-id"
)


@pytest.mark.integration
def test_standard_69_profile_builds_complete_xbrl_instance() -> None:
    """Der neue 6.9-Pfad erzeugt eine vollständige XBRL-Instanz."""

    version_root = (
        TAXONOMY_ROOT
        / "6.9"
    )

    if not version_root.is_dir():
        pytest.skip(
            "Taxonomy 6.9 is not installed locally"
        )

    if not GCD_69_ENTRY_POINT_PATH.is_file():
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
        start_date=date(
            2026,
            1,
            1,
        ),
        end_date=date(
            2026,
            12,
            31,
        ),
    )

    gaap_ci_values = GaapCi69Values(
        net_income=Decimal(
            "4500.00"
        ),
        earnings_after_taxes=Decimal(
            "4600.00"
        ),
        operating_total_cost=Decimal(
            "5000.00"
        ),
        gross_trading_profit=Decimal(
            "6000.00"
        ),
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

    gcd_entry_point = TaxonomyEntryPoint.from_file(
        GCD_69_ENTRY_POINT_PATH
    )

    gaap_ci_entry_point_path = (
        taxonomy_resolver.gaap_ci_fiscal_entry_point(
            TaxonomyVersion.V6_9
        )
    )

    gaap_ci_entry_point = TaxonomyEntryPoint.from_file(
        gaap_ci_entry_point_path
    )

    adapter = ArelleAdapter()

    try:
        gcd_model = adapter.model(
            GCD_69_ENTRY_POINT_PATH
        )

        gaap_ci_model = adapter.model(
            gaap_ci_entry_point_path
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

    units = {
        "EUR": TaxonomyUnit.eur(),
        "PURE": TaxonomyUnit.pure(),
    }

    builder = Taxonomy69XbrlDocumentBuilder()

    root = builder.build_element(
        resolved_fact_plan=resolved,
        contexts=contexts,
        units=units,
        entry_points=(
            gcd_entry_point,
            gaap_ci_entry_point,
        ),
    )

    assert root.tag == (
        f"{{{XBRLI_NAMESPACE}}}xbrl"
    )

    schema_refs = root.findall(
        f"{{{LINK_NAMESPACE}}}schemaRef"
    )

    assert len(schema_refs) == 2

    schema_ref_hrefs = {
        element.attrib[
            f"{{{XLINK_NAMESPACE}}}href"
        ]
        for element in schema_refs
    }

    assert schema_ref_hrefs == {
        gcd_entry_point.schema_ref_uri,
        gaap_ci_entry_point.schema_ref_uri,
    }

    context_elements = root.findall(
        f"{{{XBRLI_NAMESPACE}}}context"
    )

    assert {
        element.attrib["id"]
        for element in context_elements
    } == {
        "ctx-instant-2026",
        "ctx-duration-2026",
    }

    unit_elements = root.findall(
        f"{{{XBRLI_NAMESPACE}}}unit"
    )

    assert {
        element.attrib["id"]
        for element in unit_elements
    } == {
        "EUR",
        "PURE",
    }

    company_name = root.find(
        f"{{{GCD_69_NAMESPACE}}}"
        "genInfo.company.id.name"
    )

    assert company_name is not None
    assert company_name.text == (
        "Beispiel UG"
    )

    report_status = root.find(
        f"{{{GCD_69_NAMESPACE}}}"
        "genInfo.report.id.reportStatus"
    )

    assert report_status is not None

    report_status_value = report_status.find(
        f"{{{GCD_69_NAMESPACE}}}"
        "genInfo.report.id.reportStatus."
        "reportStatus.E"
    )

    assert report_status_value is not None
    assert report_status_value.text == (
        "endgültig"
    )

    according_to = root.find(
        f"{{{GCD_69_NAMESPACE}}}"
        "genInfo.report.id.accordingTo"
    )

    assert according_to is not None

    according_to_id_no = according_to.find(
        f"{{{GCD_69_NAMESPACE}}}"
        "genInfo.report.id.accordingTo.idNo"
    )

    assert according_to_id_no is not None

    according_to_st13 = according_to_id_no.find(
        f"{{{GCD_69_NAMESPACE}}}"
        "genInfo.company.id.idNo.type.companyId.ST13"
    )

    assert according_to_st13 is not None
    assert according_to_st13.attrib[
        f"{{{XSI_NAMESPACE}}}nil"
    ] == "true"

    net_income = root.find(
        f"{{{GAAP_CI_69_NAMESPACE}}}"
        "is.netIncome"
    )

    assert net_income is not None
    assert net_income.text == (
        "4500.00"
    )
    assert net_income.attrib[
        "contextRef"
    ] == "ctx-duration-2026"
    assert net_income.attrib[
        "unitRef"
    ] == "EUR"

    xml = builder.build_xml(
        resolved_fact_plan=resolved,
        contexts=contexts,
        units=units,
        entry_points=(
            gcd_entry_point,
            gaap_ci_entry_point,
        ),
    )

    parsed_root = ET.fromstring(
        xml
    )

    assert parsed_root.tag == (
        f"{{{XBRLI_NAMESPACE}}}xbrl"
    )

"""Tests für den XBRL-Export."""
from datetime import date
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from openbilanz.exporter.xbrl_export import XbrlExporter
from openbilanz.taxonomy.concept import (
    TaxonomyBalance,
    TaxonomyConcept,
    TaxonomyPeriodType,
)
from openbilanz.taxonomy.context import TaxonomyContext
from openbilanz.taxonomy.entry_point import TaxonomyEntryPoint
from openbilanz.taxonomy.fact import TaxonomyFact
from openbilanz.taxonomy.gcd_company_id_no import (
    GcdCompanyIdNo,
)
from openbilanz.taxonomy.gcd_domestic_branch_of_foreign_company import (
    GcdDomesticBranchOfForeignCompany,
)
from openbilanz.taxonomy.gcd_entity_with_taxable_purpose_business import (
    GcdEntityWithTaxablePurposeBusiness,
)
from openbilanz.taxonomy.gcd_report_element import (
    GcdReportElement,
)
from openbilanz.taxonomy.gcd_shareholder_tuple import (
    GcdShareDivideKeyTuple,
    GcdShareholderLegalStatusTuple,
    GcdShareholderTuple,
)
from openbilanz.taxonomy.resolver import TaxonomyResolver
from openbilanz.taxonomy.taxonomy import TaxonomyVersion
from openbilanz.taxonomy.text_fact import TaxonomyTextFact
from openbilanz.taxonomy.unit import TaxonomyUnit

DE_GAAP_CI_NAMESPACE = (
    "http://www.xbrl.de/taxonomies/"
    "de-gaap-ci-2024-04-01"
)

TEST_ENTITY_SCHEME = (
    "http://www.bundesfinanzministerium.de"
)


def test_xbrl_exporter_serializes_instance() -> None:
    """Der Exporter erzeugt eine vollständige XBRL-Instanz."""

    concept = TaxonomyConcept(
        name="bs.ass.fixAss",
        concept_id="de-gaap-ci_bs.ass.fixAss",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.INSTANT,
        balance=TaxonomyBalance.DEBIT,
        abstract=False,
        nillable=True,
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.INSTANT,
        start_date=None,
        end_date=date(2025, 12, 31),
    )

    unit = TaxonomyUnit.eur()

    fact = TaxonomyFact(
        concept=concept,
        amount=Decimal("125000.00"),
        context=context,
        unit=unit,
    )

    entry_point = TaxonomyEntryPoint(
        path=Path(
            "de-gaap-ci-2024-04-01-shell-fiscal.xsd"
        ),
        namespace=(
            "http://www.xbrl.de/taxonomies/"
            "de-gaap-ci-2024-04-01/shell-fiscal"
        ),
        schema_imports=(),
    )

    exporter = XbrlExporter()

    xml = exporter.export(
        contexts={
            "ctx-2025": context,
        },
        units={
            "EUR": unit,
        },
        facts=(fact,),
        taxonomy_namespace=DE_GAAP_CI_NAMESPACE,
        entry_points=(entry_point,),
    )

    assert xml.startswith(
        "<?xml version="
    )
    assert "encoding='utf-8'" in xml

    assert (
        "de-gaap-ci-2024-04-01-shell-fiscal.xsd"
        in xml
    )

    assert "bs.ass.fixAss" in xml
    assert "125000.00" in xml
    assert 'contextRef="ctx-2025"' in xml
    assert 'unitRef="EUR"' in xml


def test_xbrl_exporter_uses_real_taxonomy_entry_point() -> None:
    """Der Exporter verwendet Metadaten eines realen GAAP-CI-Entry-Points."""

    taxonomy_root = Path(
        "/tmp/openbilanz-taxonomy"
    )

    version_root = taxonomy_root / "6.8"

    if not version_root.is_dir():
        pytest.skip(
            "Taxonomy 6.8 is not installed locally"
        )

    resolver = TaxonomyResolver(
        root=taxonomy_root
    )

    entry_point_path = resolver.gaap_ci_fiscal_entry_point(
        TaxonomyVersion.V6_8
    )

    entry_point = TaxonomyEntryPoint.from_file(
        entry_point_path
    )

    concept = TaxonomyConcept(
        name="bs.ass.fixAss",
        concept_id="de-gaap-ci_bs.ass.fixAss",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.INSTANT,
        balance=TaxonomyBalance.DEBIT,
        abstract=False,
        nillable=True,
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.INSTANT,
        start_date=None,
        end_date=date(2025, 12, 31),
    )

    unit = TaxonomyUnit.eur()

    fact = TaxonomyFact(
        concept=concept,
        amount=Decimal("125000.00"),
        context=context,
        unit=unit,
    )

    exporter = XbrlExporter()

    xml = exporter.export(
        contexts={
            "ctx-2025": context,
        },
        units={
            "EUR": unit,
        },
        facts=(fact,),
        taxonomy_namespace=(
            "http://www.xbrl.de/taxonomies/"
            "de-gaap-ci-2024-04-01"
        ),
        entry_points=(
            entry_point,
        ),
    )

    assert entry_point.namespace == (
        "http://www.xbrl.de/taxonomies/"
        "de-gaap-ci-2024-04-01/shell-fiscal"
    )

    assert entry_point.schema_ref_uri in xml
    assert "bs.ass.fixAss" in xml
    assert "125000.00" in xml

def test_xbrl_exporter_supports_multiple_taxonomy_namespaces() -> None:
    """Der Exporter unterstützt mehrere Taxonomie-Namespaces."""

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    gcd_namespace = (
        "http://www.xbrl.de/taxonomies/"
        "de-gcd-2024-04-01"
    )

    gaap_namespace = (
        "http://www.xbrl.de/taxonomies/"
        "de-gaap-ci-2024-04-01"
    )

    gcd_concept = TaxonomyConcept(
        name="genInfo.company.id.name",
        concept_id="de-gcd_genInfo.company.id.name",
        type_name="xbrli:stringItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    fact = TaxonomyTextFact(
        concept=gcd_concept,
        value="Muster UG (haftungsbeschränkt)",
        context=context,
    )

    exporter = XbrlExporter()

    xml = exporter.export(
        contexts={
            "ctx-2025": context,
        },
        units={},
        facts=(
            fact,
        ),
        taxonomy_namespace=gaap_namespace,
        taxonomy_namespaces={
            "de-gcd": gcd_namespace,
            "de-gaap-ci": gaap_namespace,
        },
        entry_points=(),
    )

    assert (
        "genInfo.company.id.name"
        in xml
    )

def test_xbrl_exporter_serializes_gcd_report_element() -> None:
    """Der Exporter reicht GCD-Report-Elemente bis in die XBRL-Ausgabe durch."""

    gcd_namespace = (
        "http://www.xbrl.de/taxonomies/"
        "de-gcd-2025-04-01"
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    balance_concept = TaxonomyConcept(
        name=(
            "genInfo.report.id.reportElement."
            "reportElements.B"
        ),
        concept_id=(
            "de-gcd_genInfo.report.id.reportElement."
            "reportElements.B"
        ),
        type_name="xbrli:stringItemType",
        substitution_group=(
            "de-gcd:"
            "genInfo.report.id.reportElement."
            "reportElements.head"
        ),
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    income_statement_concept = TaxonomyConcept(
        name=(
            "genInfo.report.id.reportElement."
            "reportElements.GuV"
        ),
        concept_id=(
            "de-gcd_genInfo.report.id.reportElement."
            "reportElements.GuV"
        ),
        type_name="xbrli:stringItemType",
        substitution_group=(
            "de-gcd:"
            "genInfo.report.id.reportElement."
            "reportElements.head"
        ),
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    report_element = GcdReportElement(
        facts=(
            TaxonomyTextFact(
                concept=balance_concept,
                value="Bilanz",
                context=context,
            ),
            TaxonomyTextFact(
                concept=income_statement_concept,
                value="GuV",
                context=context,
            ),
        )
    )

    exporter = XbrlExporter()

    xml = exporter.export(
        contexts={
            "ctx-2025": context,
        },
        units={},
        facts=(),
        report_elements=(
            report_element,
        ),
        taxonomy_namespace=gcd_namespace,
        taxonomy_namespaces={
            "de-gcd": gcd_namespace,
        },
        entry_points=(),
    )

    assert "genInfo.report.id.reportElement" in xml

    assert (
        "genInfo.report.id.reportElement.reportElements.B"
        in xml
    )

    assert (
        "genInfo.report.id.reportElement.reportElements.GuV"
        in xml
    )

    assert ">Bilanz<" in xml
    assert ">GuV<" in xml
    
def test_xbrl_exporter_includes_gcd_company_id_no() -> None:
    """Der Exporter übernimmt das GCD-idNo-Tuple."""

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    gcd_namespace = (
        "http://www.xbrl.de/taxonomies/"
        "de-gcd-2025-04-01"
    )

    concept = TaxonomyConcept(
        name=(
            "genInfo.company.id.idNo.type.companyId.ST13"
        ),
        concept_id=(
            "de-gcd_genInfo.company.id.idNo.type.companyId.ST13"
        ),
        type_name="xbrli:stringItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    company_id_no = GcdCompanyIdNo(
        facts=(
            TaxonomyTextFact(
                concept=concept,
                value="1234567890123",
                context=context,
            ),
        )
    )

    exporter = XbrlExporter()

    xml = exporter.export(
        contexts={
            "ctx-2025": context,
        },
        units={},
        facts=(),
        company_id_nos=(
            company_id_no,
        ),
        taxonomy_namespace=gcd_namespace,
        taxonomy_namespaces={
            "de-gcd": gcd_namespace,
        },
        entry_points=(),
    )

    assert "genInfo.company.id.idNo" in xml
    assert (
        "genInfo.company.id.idNo.type.companyId.ST13"
        in xml
    )
    assert "1234567890123" in xml
    assert 'contextRef="ctx-2025"' in xml
    
def test_xbrl_exporter_includes_gcd_shareholder() -> None:
    """Der Exporter übernimmt ein verschachteltes GCD-Gesellschafter-Tuple."""

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    gcd_namespace = (
        "http://www.xbrl.de/taxonomies/"
        "de-gcd-2025-04-01"
    )

    def text_fact(
        name: str,
        value: str,
    ) -> TaxonomyTextFact:
        return TaxonomyTextFact(
            concept=TaxonomyConcept(
                name=name,
                concept_id="de-gcd_" + name,
                type_name="xbrli:stringItemType",
                substitution_group="xbrli:item",
                period_type=TaxonomyPeriodType.DURATION,
                balance=TaxonomyBalance.NONE,
                abstract=False,
                nillable=True,
            ),
            value=value,
            context=context,
        )

    shareholder = GcdShareholderTuple(
        name=text_fact(
            "genInfo.company.id.shareholder.name",
            "Mustermann",
        ),
        shareholder_id=text_fact(
            "genInfo.company.id.shareholder.id",
            "1",
        ),
        tax_number=text_fact(
            "genInfo.company.id.shareholder.taxnumber",
            "1234567890123",
        ),
        tax_id=text_fact(
            "genInfo.company.id.shareholder.taxid",
            "12345678901",
        ),
        wid=text_fact(
            "genInfo.company.id.shareholder.WID",
            "WID-1",
        ),
        legal_status=GcdShareholderLegalStatusTuple(
            fact=text_fact(
                (
                    "genInfo.company.id.shareholder."
                    "legalStatus.legalStatus.NPP"
                ),
                "NPP",
            ),
        ),
        share_divide_key=GcdShareDivideKeyTuple(
            numerator=text_fact(
                (
                    "genInfo.company.id.shareholder."
                    "ShareDivideKey.numerator"
                ),
                "25",
            ),
            denominator=text_fact(
                (
                    "genInfo.company.id.shareholder."
                    "ShareDivideKey.denominator"
                ),
                "100",
            ),
        ),
    )

    exporter = XbrlExporter()

    xml = exporter.export(
        contexts={
            "ctx-2025": context,
        },
        units={},
        facts=(),
        shareholders=(
            shareholder,
        ),
        taxonomy_namespace=gcd_namespace,
        taxonomy_namespaces={
            "de-gcd": gcd_namespace,
        },
        entry_points=(),
    )

    assert "genInfo.company.id.shareholder" in xml
    assert "genInfo.company.id.shareholder.name" in xml
    assert "Mustermann" in xml

    assert (
        "genInfo.company.id.shareholder.legalStatus"
        in xml
    )
    assert (
        "genInfo.company.id.shareholder."
        "legalStatus.legalStatus.NPP"
        in xml
    )

    assert (
        "genInfo.company.id.shareholder.ShareDivideKey"
        in xml
    )
    assert (
        "genInfo.company.id.shareholder."
        "ShareDivideKey.numerator"
        in xml
    )
    assert (
        "genInfo.company.id.shareholder."
        "ShareDivideKey.denominator"
        in xml
    )

    assert 'contextRef="ctx-2025"' in xml

def test_xbrl_export_includes_gcd_company_classification_tuples() -> None:
    """Der Export enthält beide GCD-Unternehmensklassifikationen."""

    gcd_namespace = (
        "http://www.xbrl.de/taxonomies/"
        "de-gcd-2025-04-01"
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    branch_fact = TaxonomyTextFact(
        concept=TaxonomyConcept(
            name=(
                "genInfo.company.id."
                "domesticBranchOfForeignCompany.HGB"
            ),
            concept_id=(
                "de-gcd_genInfo.company.id."
                "domesticBranchOfForeignCompany.HGB"
            ),
            type_name="xbrli:stringItemType",
            substitution_group="xbrli:item",
            period_type=TaxonomyPeriodType.DURATION,
            balance=TaxonomyBalance.NONE,
            abstract=False,
            nillable=True,
        ),
        value="HGB",
        context=context,
    )

    business_fact = TaxonomyTextFact(
        concept=TaxonomyConcept(
            name=(
                "genInfo.company.id."
                "entityWithTaxablePurposeBusiness.normal"
            ),
            concept_id=(
                "de-gcd_genInfo.company.id."
                "entityWithTaxablePurposeBusiness.normal"
            ),
            type_name="xbrli:stringItemType",
            substitution_group="xbrli:item",
            period_type=TaxonomyPeriodType.DURATION,
            balance=TaxonomyBalance.NONE,
            abstract=False,
            nillable=True,
        ),
        value="normal",
        context=context,
    )

    exporter = XbrlExporter()

    xml = exporter.export(
        contexts={
            "ctx-2025": context,
        },
        units={},
        facts=(),
        taxonomy_namespace=gcd_namespace,
        entry_points=(),
        domestic_branches=(
            GcdDomesticBranchOfForeignCompany(
                fact=branch_fact,
            ),
        ),
        taxable_purpose_businesses=(
            GcdEntityWithTaxablePurposeBusiness(
                fact=business_fact,
            ),
        ),
    )

    root = ET.fromstring(
        xml
    )

    branch_element = root.find(
        f"{{{gcd_namespace}}}"
        "genInfo.company.id.domesticBranchOfForeignCompany"
    )

    assert branch_element is not None

    branch_child = branch_element.find(
        f"{{{gcd_namespace}}}"
        "genInfo.company.id.domesticBranchOfForeignCompany.HGB"
    )

    assert branch_child is not None
    assert branch_child.text == "HGB"
    assert branch_child.get("contextRef") == "ctx-2025"

    business_element = root.find(
        f"{{{gcd_namespace}}}"
        "genInfo.company.id.entityWithTaxablePurposeBusiness"
    )

    assert business_element is not None

    business_child = business_element.find(
        f"{{{gcd_namespace}}}"
        "genInfo.company.id.entityWithTaxablePurposeBusiness.normal"
    )

    assert business_child is not None
    assert business_child.text == "normal"
    assert business_child.get("contextRef") == "ctx-2025"


"""Tests für die XBRL-Serialisierung."""
from datetime import date
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

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
from openbilanz.taxonomy.text_fact import TaxonomyTextFact
from openbilanz.taxonomy.unit import TaxonomyUnit
from openbilanz.taxonomy.xbrl_writer import TaxonomyXbrlWriter

DE_GAAP_CI_NAMESPACE = (
    "http://www.xbrl.de/taxonomies/"
    "de-gaap-ci-2024-04-01"
)

XBRLI_NAMESPACE = "http://www.xbrl.org/2003/instance"

TEST_ENTITY_SCHEME = "http://www.bundesfinanzministerium.de"




def test_xbrl_writer_serializes_instant_context() -> None:
    """Ein Instant-Kontext wird als XBRL-Context serialisiert."""

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.INSTANT,
        start_date=None,
        end_date=date(2025, 12, 31),
    )

    writer = TaxonomyXbrlWriter()

    element = writer.context_element(
        context=context,
        context_id="ctx-2025",
    )

    assert element.tag == f"{{{XBRLI_NAMESPACE}}}context"
    assert element.attrib["id"] == "ctx-2025"

    instant = element.find(
        f".//{{{XBRLI_NAMESPACE}}}instant"
    )

    assert instant is not None
    assert instant.text == "2025-12-31"

    identifier = element.find(
        f".//{{{XBRLI_NAMESPACE}}}identifier"
    )

    assert identifier is not None
    assert identifier.text == "DE123456789"
    assert identifier.attrib["scheme"] == TEST_ENTITY_SCHEME

    xml = ET.tostring(
        element,
        encoding="unicode",
    )

    assert "DE123456789" in xml


def test_xbrl_writer_serializes_duration_context() -> None:
    """Ein Duration-Kontext wird mit Start- und Enddatum serialisiert."""

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    writer = TaxonomyXbrlWriter()

    element = writer.context_element(
        context=context,
        context_id="ctx-2025-duration",
    )

    start_date = element.find(
        f".//{{{XBRLI_NAMESPACE}}}startDate"
    )
    end_date = element.find(
        f".//{{{XBRLI_NAMESPACE}}}endDate"
    )

    assert start_date is not None
    assert start_date.text == "2025-01-01"

    assert end_date is not None
    assert end_date.text == "2025-12-31"

    instant = element.find(
        f".//{{{XBRLI_NAMESPACE}}}instant"
    )

    assert instant is None


def test_xbrl_writer_serializes_euro_unit() -> None:
    """Eine EUR-Einheit wird als XBRL-Unit serialisiert."""

    unit = TaxonomyUnit.eur()

    writer = TaxonomyXbrlWriter()

    element = writer.unit_element(
        unit=unit,
        unit_id="EUR",
    )

    assert element.tag == f"{{{XBRLI_NAMESPACE}}}unit"
    assert element.attrib["id"] == "EUR"

    measure = element.find(
        f"{{{XBRLI_NAMESPACE}}}measure"
    )

    assert measure is not None
    assert measure.text == "iso4217:EUR"


def test_xbrl_writer_serializes_fact() -> None:
    """Ein TaxonomyFact wird als XBRL-Fact serialisiert."""

    
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
        decimals=2,
    )

    writer = TaxonomyXbrlWriter()

    element = writer.fact_element(
        fact=fact,
        context_id="ctx-2025",
        unit_id="EUR",
        namespace=DE_GAAP_CI_NAMESPACE,
    )

    assert element.tag == (
        f"{{{DE_GAAP_CI_NAMESPACE}}}"
        "bs.ass.fixAss"
    )

    assert element.attrib["contextRef"] == "ctx-2025"
    assert element.attrib["unitRef"] == "EUR"
    assert element.text == "125000.00"
    assert element.attrib["decimals"] == "2"


def test_xbrl_writer_builds_instance_document() -> None:
    """Context, Unit und Fact werden zu einer XBRL-Instanz kombiniert."""

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

    fact = TaxonomyFact(
        concept=concept,
        amount=Decimal("125000.00"),
        context=context,
        unit=unit,
    )

    writer = TaxonomyXbrlWriter()

    root = writer.instance_element(
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
    
    assert root.tag == f"{{{XBRLI_NAMESPACE}}}xbrl"
    
    schema_ref = root.find(
        "{http://www.xbrl.org/2003/linkbase}schemaRef"
    )

    assert schema_ref is not None
    assert schema_ref.attrib[
        "{http://www.w3.org/1999/xlink}type"
    ] == "simple"
    assert schema_ref.attrib[
        "{http://www.w3.org/1999/xlink}href"
    ] == (
        "http://www.xbrl.de/taxonomies/"
        "de-gaap-ci-2024-04-01/"
        "de-gaap-ci-2024-04-01-shell-fiscal.xsd"
    )

    contexts = root.findall(
        f"{{{XBRLI_NAMESPACE}}}context"
    )
    units = root.findall(
        f"{{{XBRLI_NAMESPACE}}}unit"
    )

    assert len(contexts) == 1
    assert len(units) == 1

    fact_element = root.find(
        f"{{{DE_GAAP_CI_NAMESPACE}}}"
        "bs.ass.fixAss"
    )

    assert fact_element is not None
    assert fact_element.attrib["contextRef"] == "ctx-2025"
    assert fact_element.attrib["unitRef"] == "EUR"
    assert fact_element.text == "125000.00"

def test_xbrl_writer_serializes_schema_ref() -> None:
    """Ein Taxonomie-Entry-Point wird als schemaRef serialisiert."""

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

    writer = TaxonomyXbrlWriter()

    element = writer.schema_ref_element(
        entry_point=entry_point,
    )

    assert element.tag == (
        "{http://www.xbrl.org/2003/linkbase}"
        "schemaRef"
    )
    assert element.attrib[
        "{http://www.w3.org/1999/xlink}type"
    ] == "simple"
    assert element.attrib[
        "{http://www.w3.org/1999/xlink}href"
    ] == (
        "http://www.xbrl.de/taxonomies/"
        "de-gaap-ci-2024-04-01/"
        "de-gaap-ci-2024-04-01-shell-fiscal.xsd"
    )
   
def test_xbrl_writer_serializes_instance_to_xml_string() -> None:
    """Eine XBRL-Instanz kann als XML-String serialisiert werden."""

    writer = TaxonomyXbrlWriter()

    root = ET.Element(
        f"{{{XBRLI_NAMESPACE}}}xbrl"
    )

    xml = writer.to_xml_string(
        root=root,
    )

    assert xml.startswith("<?xml version=")
    assert "encoding='utf-8'" in xml
    assert "xbrl" in xml
    
def test_xbrl_writer_serializes_required_namespaces() -> None:
    """Die XBRL-Instanz deklariert die benötigten Standard-Namespaces."""

    writer = TaxonomyXbrlWriter()

    root = ET.Element(
        f"{{{XBRLI_NAMESPACE}}}xbrl"
    )

    root.append(
        writer.unit_element(
            unit=TaxonomyUnit.eur(),
            unit_id="EUR",
        )
    )

    xml = writer.to_xml_string(
        root=root,
    )

    assert (
        'xmlns:xbrli="http://www.xbrl.org/2003/instance"'
        in xml
    )
    assert (
        'xmlns:iso4217="http://www.xbrl.org/2003/iso4217"'
        in xml
    )

def test_xbrl_writer_serializes_schema_ref_namespaces() -> None:
    """schemaRef verwendet die XBRL-Linkbase-Namespaces."""

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

    writer = TaxonomyXbrlWriter()

    root = ET.Element(
        f"{{{XBRLI_NAMESPACE}}}xbrl"
    )

    root.append(
        writer.schema_ref_element(
            entry_point=entry_point,
        )
    )

    xml = writer.to_xml_string(
        root=root,
    )

    assert (
        'xmlns:link="http://www.xbrl.org/2003/linkbase"'
        in xml
    )
    assert (
        'xmlns:xlink="http://www.w3.org/1999/xlink"'
        in xml
    )
    assert "<link:schemaRef" in xml
    assert 'xlink:type="simple"' in xml

def test_xbrl_writer_builds_instance_with_multiple_schema_refs() -> None:
    """Eine XBRL-Instanz kann mehrere schemaRefs enthalten."""

    gcd_entry_point = TaxonomyEntryPoint(
        path=Path(
            "de-gcd-2024-04-01-shell-fiscal.xsd"
        ),
        namespace=(
            "http://www.xbrl.de/taxonomies/"
            "de-gcd-2024-04-01/shell-fiscal"
        ),
        schema_imports=(),
    )

    gaap_entry_point = TaxonomyEntryPoint(
        path=Path(
            "de-gaap-ci-2024-04-01-shell-fiscal.xsd"
        ),
        namespace=(
            "http://www.xbrl.de/taxonomies/"
            "de-gaap-ci-2024-04-01/shell-fiscal"
        ),
        schema_imports=(),
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.INSTANT,
        start_date=None,
        end_date=date(2025, 12, 31),
    )

    writer = TaxonomyXbrlWriter()

    root = writer.instance_element(
        contexts={
            "ctx-2025": context,
        },
        units={
            "EUR": TaxonomyUnit.eur(),
        },
        facts=(),
        taxonomy_namespace=DE_GAAP_CI_NAMESPACE,
        entry_points=(
            gcd_entry_point,
            gaap_entry_point,
        ),
    )

    schema_refs = root.findall(
        "{http://www.xbrl.org/2003/linkbase}schemaRef"
    )

    assert len(schema_refs) == 2

    hrefs = {
        schema_ref.attrib[
            "{http://www.w3.org/1999/xlink}href"
        ]
        for schema_ref in schema_refs
    }

    assert hrefs == {
        (
            "http://www.xbrl.de/taxonomies/"
            "de-gcd-2024-04-01/"
            "de-gcd-2024-04-01-shell-fiscal.xsd"
        ),
        (
            "http://www.xbrl.de/taxonomies/"
            "de-gaap-ci-2024-04-01/"
            "de-gaap-ci-2024-04-01-shell-fiscal.xsd"
        ),
    }


def test_xbrl_writer_preserves_schema_ref_order() -> None:
    """schemaRefs werden in der übergebenen Reihenfolge serialisiert."""

    first_entry_point = TaxonomyEntryPoint(
        path=Path(
            "de-gcd-2024-04-01-shell-fiscal.xsd"
        ),
        namespace=(
            "http://www.xbrl.de/taxonomies/"
            "de-gcd-2024-04-01/shell-fiscal"
        ),
        schema_imports=(),
    )

    second_entry_point = TaxonomyEntryPoint(
        path=Path(
            "de-gaap-ci-2024-04-01-shell-fiscal.xsd"
        ),
        namespace=(
            "http://www.xbrl.de/taxonomies/"
            "de-gaap-ci-2024-04-01/shell-fiscal"
        ),
        schema_imports=(),
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.INSTANT,
        start_date=None,
        end_date=date(2025, 12, 31),
    )

    writer = TaxonomyXbrlWriter()

    root = writer.instance_element(
        contexts={
            "ctx-2025": context,
        },
        units={
            "EUR": TaxonomyUnit.eur(),
        },
        facts=(),
        taxonomy_namespace=DE_GAAP_CI_NAMESPACE,
        entry_points=(
            first_entry_point,
            second_entry_point,
        ),
    )

    schema_refs = root.findall(
        "{http://www.xbrl.org/2003/linkbase}schemaRef"
    )

    hrefs = [
        schema_ref.attrib[
            "{http://www.w3.org/1999/xlink}href"
        ]
        for schema_ref in schema_refs
    ]

    assert hrefs == [
        (
            "http://www.xbrl.de/taxonomies/"
            "de-gcd-2024-04-01/"
            "de-gcd-2024-04-01-shell-fiscal.xsd"
        ),
        (
            "http://www.xbrl.de/taxonomies/"
            "de-gaap-ci-2024-04-01/"
            "de-gaap-ci-2024-04-01-shell-fiscal.xsd"
        ),
    ]


def test_xbrl_writer_resolves_context_id() -> None:
    """Ein Fact erhält die ID seines zugehörigen Contexts."""

    first_context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.INSTANT,
        start_date=None,
        end_date=date(2024, 12, 31),
    )

    second_context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.INSTANT,
        start_date=None,
        end_date=date(2025, 12, 31),
    )

    writer = TaxonomyXbrlWriter()

    context_id = writer.context_id_for(
        context=second_context,
        contexts={
            "ctx-2024": first_context,
            "ctx-2025": second_context,
        },
    )

    assert context_id == "ctx-2025"



def test_xbrl_writer_builds_instance_with_multiple_contexts() -> None:
    """Mehrere Contexts werden serialisiert und Facts korrekt zugeordnet."""

    first_context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.INSTANT,
        start_date=None,
        end_date=date(2024, 12, 31),
    )

    second_context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.INSTANT,
        start_date=None,
        end_date=date(2025, 12, 31),
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

    unit = TaxonomyUnit.eur()
    
    fact = TaxonomyFact(
        concept=concept,
        amount=Decimal("125000.00"),
        context=second_context,
        unit=unit,
        decimals=2,
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

    writer = TaxonomyXbrlWriter()

    root = writer.instance_element(
        contexts={
            "ctx-2024": first_context,
            "ctx-2025": second_context,
        },
        units={
            "EUR": unit,
        },
        facts=(fact,),
        taxonomy_namespace=DE_GAAP_CI_NAMESPACE,
        entry_points=(entry_point,),
    )

    contexts = root.findall(
        f"{{{XBRLI_NAMESPACE}}}context"
    )

    assert len(contexts) == 2
    assert [
        context.attrib["id"]
        for context in contexts
    ] == [
        "ctx-2024",
        "ctx-2025",
    ]

    fact_element = root.find(
        f"{{{DE_GAAP_CI_NAMESPACE}}}"
        "bs.ass.fixAss"
    )

    assert fact_element is not None
    assert fact_element.attrib["contextRef"] == "ctx-2025"
    
def test_xbrl_writer_resolves_unit_id() -> None:
    """Ein Fact erhält die ID seiner zugehörigen XBRL-Einheit."""

    euro_unit = TaxonomyUnit.eur()

    pure_unit = TaxonomyUnit(
        measure="xbrli:pure",
    )

    writer = TaxonomyXbrlWriter()

    unit_id = writer.unit_id_for(
        unit=pure_unit,
        units={
            "EUR": euro_unit,
            "pure": pure_unit,
        },
    )

    assert unit_id == "pure"
    
def test_xbrl_writer_builds_instance_with_multiple_units() -> None:
    """Mehrere Units werden serialisiert und Facts korrekt zugeordnet."""

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    euro_unit = TaxonomyUnit.eur()

    pure_unit = TaxonomyUnit(
        measure="xbrli:pure",
    )

    concept = TaxonomyConcept(
        name="nt.particip.listRow.quota.direct",
        concept_id=(
            "de-gaap-ci_nt.particip.listRow.quota.direct"
        ),
        type_name="xbrli:pureItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    fact = TaxonomyFact(
        concept=concept,
        amount=Decimal("0.75"),
        context=context,
        unit=pure_unit,
        decimals=2,
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

    writer = TaxonomyXbrlWriter()

    root = writer.instance_element(
        contexts={
            "ctx-2025": context,
        },
        units={
            "EUR": euro_unit,
            "pure": pure_unit,
        },
        facts=(fact,),
        taxonomy_namespace=DE_GAAP_CI_NAMESPACE,
        entry_points=(entry_point,),
    )

    units = root.findall(
        f"{{{XBRLI_NAMESPACE}}}unit"
    )

    assert len(units) == 2

    assert [
        unit.attrib["id"]
        for unit in units
    ] == [
        "EUR",
        "pure",
    ]

    fact_element = root.find(
        f"{{{DE_GAAP_CI_NAMESPACE}}}"
        "nt.particip.listRow.quota.direct"
    )

    assert fact_element is not None
    assert fact_element.attrib["contextRef"] == "ctx-2025"
    assert fact_element.attrib["unitRef"] == "pure"
def test_xbrl_writer_rejects_unregistered_unit() -> None:
    """Eine fachlich nicht registrierte Unit besitzt keine XBRL-ID."""

    registered_unit = TaxonomyUnit.eur()

    unregistered_unit = TaxonomyUnit(
        measure="xbrli:pure",
    )

    writer = TaxonomyXbrlWriter()

    with pytest.raises(
        ValueError,
        match="unit is not registered",
    ):
        writer.unit_id_for(
            unit=unregistered_unit,
            units={
                "EUR": registered_unit,
            },
        )
  
def test_xbrl_writer_assigns_contexts_and_units_to_multiple_facts() -> None:
    """Mehrere Facts erhalten ihre jeweiligen Context- und Unit-Referenzen."""

    instant_context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.INSTANT,
        start_date=None,
        end_date=date(2025, 12, 31),
    )

    duration_context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    euro_unit = TaxonomyUnit.eur()

    pure_unit = TaxonomyUnit(
        measure="xbrli:pure",
    )

    monetary_concept = TaxonomyConcept(
        name="bs.ass.fixAss",
        concept_id="de-gaap-ci_bs.ass.fixAss",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.INSTANT,
        balance=TaxonomyBalance.DEBIT,
        abstract=False,
        nillable=True,
    )

    pure_concept = TaxonomyConcept(
        name="nt.particip.listRow.quota.direct",
        concept_id=(
            "de-gaap-ci_nt.particip.listRow.quota.direct"
        ),
        type_name="xbrli:pureItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    monetary_fact = TaxonomyFact(
        concept=monetary_concept,
        amount=Decimal("125000.00"),
        context=instant_context,
        unit=euro_unit,
        decimals=2,
    )

    pure_fact = TaxonomyFact(
        concept=pure_concept,
        amount=Decimal("0.75"),
        context=duration_context,
        unit=pure_unit,
        decimals=2,
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

    writer = TaxonomyXbrlWriter()

    root = writer.instance_element(
        contexts={
            "ctx-instant-2025": instant_context,
            "ctx-duration-2025": duration_context,
        },
        units={
            "EUR": euro_unit,
            "pure": pure_unit,
        },
        facts=(
            monetary_fact,
            pure_fact,
        ),
        taxonomy_namespace=DE_GAAP_CI_NAMESPACE,
        entry_points=(entry_point,),
    )

    monetary_element = root.find(
        f"{{{DE_GAAP_CI_NAMESPACE}}}"
        "bs.ass.fixAss"
    )

    pure_element = root.find(
        f"{{{DE_GAAP_CI_NAMESPACE}}}"
        "nt.particip.listRow.quota.direct"
    )

    assert monetary_element is not None
    assert monetary_element.attrib["contextRef"] == "ctx-instant-2025"
    assert monetary_element.attrib["unitRef"] == "EUR"
    assert monetary_element.text == "125000.00"

    assert pure_element is not None
    assert pure_element.attrib["contextRef"] == "ctx-duration-2025"
    assert pure_element.attrib["unitRef"] == "pure"
    assert pure_element.text == "0.75"
    
def test_xbrl_writer_resolves_equivalent_unit() -> None:
    """Fachlich gleiche Units werden derselben XBRL-ID zugeordnet."""

    registered_unit = TaxonomyUnit.eur()
    equivalent_unit = TaxonomyUnit.eur()

    writer = TaxonomyXbrlWriter()

    unit_id = writer.unit_id_for(
        unit=equivalent_unit,
        units={
            "EUR": registered_unit,
        },
    )

    assert unit_id == "EUR"
    
def test_xbrl_writer_distinguishes_equivalent_contexts() -> None:
    """Inhaltlich gleiche Contexts bleiben getrennte XBRL-Contexts."""

    registered_context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.INSTANT,
        start_date=None,
        end_date=date(2025, 12, 31),
    )

    equivalent_context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.INSTANT,
        start_date=None,
        end_date=date(2025, 12, 31),
    )

    writer = TaxonomyXbrlWriter()

    with pytest.raises(
        ValueError,
        match="context is not registered",
    ):
        writer.context_id_for(
            context=equivalent_context,
            contexts={
                "ctx-2025": registered_context,
            },
        )


def test_xbrl_writer_serializes_text_fact() -> None:
    """Ein Text-Fact wird ohne Unit und decimals serialisiert."""

    concept = TaxonomyConcept(
        name="nt.registerAgriculture",
        concept_id="de-gaap-ci_nt.registerAgriculture",
        type_name="xbrli:stringItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    fact = TaxonomyTextFact(
        concept=concept,
        value="Landwirtschaftlicher Betrieb",
        context=context,
    )

    writer = TaxonomyXbrlWriter()

    element = writer.text_fact_element(
        fact=fact,
        context_id="ctx-2025",
        namespace=DE_GAAP_CI_NAMESPACE,
    )

    assert element.tag == (
        f"{{{DE_GAAP_CI_NAMESPACE}}}"
        "nt.registerAgriculture"
    )

    assert element.attrib["contextRef"] == "ctx-2025"
    assert element.text == "Landwirtschaftlicher Betrieb"

    assert "unitRef" not in element.attrib
    assert "decimals" not in element.attrib


def test_xbrl_writer_builds_instance_with_numeric_and_text_facts() -> None:
    """Numerische und Text-Facts werden gemeinsam serialisiert."""

    instant_context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.INSTANT,
        start_date=None,
        end_date=date(2025, 12, 31),
    )

    duration_context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    euro_unit = TaxonomyUnit.eur()

    monetary_concept = TaxonomyConcept(
        name="bs.ass.fixAss",
        concept_id="de-gaap-ci_bs.ass.fixAss",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.INSTANT,
        balance=TaxonomyBalance.DEBIT,
        abstract=False,
        nillable=True,
    )

    text_concept = TaxonomyConcept(
        name="nt.registerAgriculture",
        concept_id="de-gaap-ci_nt.registerAgriculture",
        type_name="xbrli:stringItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    numeric_fact = TaxonomyFact(
        concept=monetary_concept,
        amount=Decimal("125000.00"),
        context=instant_context,
        unit=euro_unit,
        decimals=2,
    )

    text_fact = TaxonomyTextFact(
        concept=text_concept,
        value="Landwirtschaftlicher Betrieb",
        context=duration_context,
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

    writer = TaxonomyXbrlWriter()

    root = writer.instance_element(
        contexts={
            "ctx-instant-2025": instant_context,
            "ctx-duration-2025": duration_context,
        },
        units={
            "EUR": euro_unit,
        },
        facts=(
            numeric_fact,
            text_fact,
        ),
        taxonomy_namespace=DE_GAAP_CI_NAMESPACE,
        entry_points=(entry_point,),
    )

    numeric_element = root.find(
        f"{{{DE_GAAP_CI_NAMESPACE}}}"
        "bs.ass.fixAss"
    )

    text_element = root.find(
        f"{{{DE_GAAP_CI_NAMESPACE}}}"
        "nt.registerAgriculture"
    )

    assert numeric_element is not None
    assert numeric_element.attrib["contextRef"] == "ctx-instant-2025"
    assert numeric_element.attrib["unitRef"] == "EUR"
    assert numeric_element.attrib["decimals"] == "2"
    assert numeric_element.text == "125000.00"

    assert text_element is not None
    assert text_element.attrib["contextRef"] == "ctx-duration-2025"
    assert text_element.text == "Landwirtschaftlicher Betrieb"
    assert "unitRef" not in text_element.attrib
    assert "decimals" not in text_element.attrib
    
def test_xbrl_writer_builds_instance_with_multiple_taxonomy_namespaces() -> None:
    """GCD- und GAAP-CI-Facts erhalten ihre jeweiligen Namespaces."""

    gcd_namespace = (
        "http://www.xbrl.de/taxonomies/"
        "de-gcd-2024-04-01"
    )

    gaap_namespace = (
        "http://www.xbrl.de/taxonomies/"
        "de-gaap-ci-2024-04-01"
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    unit = TaxonomyUnit.eur()

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

    gaap_concept = TaxonomyConcept(
        name="is.netIncome",
        concept_id="de-gaap-ci_is.netIncome",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.CREDIT,
        abstract=False,
        nillable=True,
    )

    gcd_fact = TaxonomyTextFact(
        concept=gcd_concept,
        value="Muster UG (haftungsbeschränkt)",
        context=context,
    )

    gaap_fact = TaxonomyFact(
        concept=gaap_concept,
        amount=Decimal("15000.00"),
        context=context,
        unit=unit,
    )

    gcd_entry_point = TaxonomyEntryPoint(
        path=Path(
            "de-gcd-2024-04-01-shell.xsd"
        ),
        namespace=gcd_namespace,
        schema_imports=(),
    )

    gaap_entry_point = TaxonomyEntryPoint(
        path=Path(
            "de-gaap-ci-2024-04-01-shell-fiscal.xsd"
        ),
        namespace=gaap_namespace,
        schema_imports=(),
    )

    writer = TaxonomyXbrlWriter()

    root = writer.instance_element(
        contexts={
            "ctx-2025": context,
        },
        units={
            "EUR": unit,
        },
        facts=(
            gcd_fact,
            gaap_fact,
        ),
        taxonomy_namespace=gaap_namespace,
        taxonomy_namespaces={
            "de-gcd": gcd_namespace,
            "de-gaap-ci": gaap_namespace,
        },
        entry_points=(
            gcd_entry_point,
            gaap_entry_point,
        ),
    )

    gcd_element = root.find(
        f"{{{gcd_namespace}}}"
        "genInfo.company.id.name"
    )

    gaap_element = root.find(
        f"{{{gaap_namespace}}}"
        "is.netIncome"
    )

    assert gcd_element is not None
    assert gcd_element.text == (
        "Muster UG (haftungsbeschränkt)"
    )

    assert gaap_element is not None
    assert gaap_element.text == "15000.00"


def test_xbrl_writer_serializes_gcd_report_element_tuple() -> None:
    """GCD-Berichtsbestandteile werden innerhalb ihres Tuples serialisiert."""

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

    balance_fact = TaxonomyTextFact(
        concept=balance_concept,
        value="Bilanz",
        context=context,
    )

    income_statement_fact = TaxonomyTextFact(
        concept=income_statement_concept,
        value="GuV",
        context=context,
    )

    report_element = GcdReportElement(
        facts=(
            balance_fact,
            income_statement_fact,
        )
    )

    writer = TaxonomyXbrlWriter()

    element = writer.gcd_report_element_element(
        report_element=report_element,
        context_id="ctx-2025",
        namespace=gcd_namespace,
    )

    assert element.tag == (
        f"{{{gcd_namespace}}}"
        "genInfo.report.id.reportElement"
    )

    children = list(element)

    assert len(children) == 2

    assert children[0].tag == (
        f"{{{gcd_namespace}}}"
        "genInfo.report.id.reportElement."
        "reportElements.B"
    )
    assert children[0].attrib["contextRef"] == "ctx-2025"
    assert children[0].text == "Bilanz"

    assert children[1].tag == (
        f"{{{gcd_namespace}}}"
        "genInfo.report.id.reportElement."
        "reportElements.GuV"
    )
    assert children[1].attrib["contextRef"] == "ctx-2025"
    assert children[1].text == "GuV"

    assert "contextRef" not in element.attrib

def test_xbrl_writer_includes_gcd_report_element_in_instance() -> None:
    """Die XBRL-Instanz enthält das GCD-Report-Element als Tuple."""

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

    writer = TaxonomyXbrlWriter()

    root = writer.instance_element(
        contexts={
            "ctx-2025": context,
        },
        units={},
        facts=(),
        taxonomy_namespace=gcd_namespace,
        taxonomy_namespaces={
            "de-gcd": gcd_namespace,
        },
        entry_points=(),
        report_elements=(
            report_element,
        ),
    )

    report_elements = root.findall(
        f"{{{gcd_namespace}}}"
        "genInfo.report.id.reportElement"
    )

    assert len(report_elements) == 1

    report_element_xml = report_elements[0]

    assert "contextRef" not in report_element_xml.attrib

    children = list(report_element_xml)

    assert len(children) == 2

    assert children[0].tag == (
        f"{{{gcd_namespace}}}"
        "genInfo.report.id.reportElement."
        "reportElements.B"
    )
    assert children[0].attrib["contextRef"] == "ctx-2025"
    assert children[0].text == "Bilanz"

    assert children[1].tag == (
        f"{{{gcd_namespace}}}"
        "genInfo.report.id.reportElement."
        "reportElements.GuV"
    )
    assert children[1].attrib["contextRef"] == "ctx-2025"
    assert children[1].text == "GuV"

def test_xbrl_writer_serializes_gcd_company_id_no_tuple() -> None:
    """Der Writer serialisiert das GCD-idNo-Tuple."""

    namespace = (
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

    concept_names = (
        "genInfo.company.id.idNo.type.companyId.ST13",
        "genInfo.company.id.idNo.type.companyId.STID",
        "genInfo.company.id.idNo.type.companyId.STWID",
        "genInfo.company.id.idNo.type.companyId.BF4",
    )

    values = (
        "1234567890123",
        "12345678901",
        "DE123456789",
        "1234",
    )

    facts = tuple(
        TaxonomyTextFact(
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
        for name, value in zip(
            concept_names,
            values,
            strict=True,
        )
    )

    company_id_no = GcdCompanyIdNo(
        facts=facts
    )

    writer = TaxonomyXbrlWriter()

    element = writer.gcd_company_id_no_element(
        company_id_no=company_id_no,
        context_id="ctx-2025",
        namespace=namespace,
    )

    assert element.tag == (
        f"{{{namespace}}}"
        "genInfo.company.id.idNo"
    )

    assert len(element) == 4

    assert element[0].tag == (
        f"{{{namespace}}}"
        "genInfo.company.id.idNo.type.companyId.ST13"
    )
    assert element[0].text == "1234567890123"

    assert element[1].tag == (
        f"{{{namespace}}}"
        "genInfo.company.id.idNo.type.companyId.STID"
    )
    assert element[1].text == "12345678901"

    assert element[2].tag == (
        f"{{{namespace}}}"
        "genInfo.company.id.idNo.type.companyId.STWID"
    )
    assert element[2].text == "DE123456789"

    assert element[3].tag == (
        f"{{{namespace}}}"
        "genInfo.company.id.idNo.type.companyId.BF4"
    )
    assert element[3].text == "1234"

    for child in element:
        assert child.get("contextRef") == "ctx-2025"


def test_xbrl_writer_includes_gcd_company_id_no_in_instance() -> None:
    """Das idNo-Tuple wird in die XBRL-Instanz aufgenommen."""

    namespace = (
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

    writer = TaxonomyXbrlWriter()

    root = writer.instance_element(
        contexts={
            "ctx-2025": context,
        },
        units={},
        facts=(),
        company_id_nos=(
            company_id_no,
        ),
        taxonomy_namespace=namespace,
        taxonomy_namespaces={
            "de-gcd": namespace,
        },
        entry_points=(),
    )

    tags = {
        element.tag
        for element in root.iter()
    }

    assert (
        f"{{{namespace}}}"
        "genInfo.company.id.idNo"
    ) in tags

    assert (
        f"{{{namespace}}}"
        "genInfo.company.id.idNo.type.companyId.ST13"
    ) in tags
    
def test_xbrl_writer_serializes_gcd_shareholder_tuple() -> None:
    """Der Writer serialisiert ein verschachteltes Gesellschafter-Tuple."""

    namespace = (
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
        first_name=text_fact(
            "genInfo.company.id.shareholder.FirstName",
            "Max",
        ),
        shareholder_id=text_fact(
            "genInfo.company.id.shareholder.id",
            "1",
        ),
        group=text_fact(
            "genInfo.company.id.shareholder.group.limPartner",
            "limPartner",
        ),
        current_number=TaxonomyFact(
            concept=TaxonomyConcept(
                name=(
                    "genInfo.company.id.shareholder.currentnumber"
                ),
                concept_id=(
                    "de-gcd_genInfo.company.id.shareholder.currentnumber"
                ),
                type_name="xbrli:positiveIntegerItemType",
                substitution_group="xbrli:item",
                period_type=TaxonomyPeriodType.DURATION,
                balance=TaxonomyBalance.NONE,
                abstract=False,
                nillable=True,
            ),
            amount=Decimal("1"),
            context=context,
            unit=TaxonomyUnit.pure(),
            decimals="INF",
        ),
        signer_id=None,
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
        special_balance_required=None,
        extension_required=None,
    )

    writer = TaxonomyXbrlWriter()

    element = writer.gcd_shareholder_element(
        shareholder=shareholder,
        context_id="ctx-2025",
        namespace=namespace,
        pure_unit_id="PURE",
    )

    assert element.tag == (
        f"{{{namespace}}}"
        "genInfo.company.id.shareholder"
    )

    group = element.find(
        f"{{{namespace}}}"
        "genInfo.company.id.shareholder.group"
    )

    assert group is not None
    assert len(group) == 1
    assert group[0].tag == (
        f"{{{namespace}}}"
        "genInfo.company.id.shareholder.group.limPartner"
    )

    legal_status = element.find(
        f"{{{namespace}}}"
        "genInfo.company.id.shareholder.legalStatus"
    )

    assert legal_status is not None
    assert len(legal_status) == 1
    assert legal_status[0].tag == (
        f"{{{namespace}}}"
        "genInfo.company.id.shareholder."
        "legalStatus.legalStatus.NPP"
    )

    share_divide_key = element.find(
        f"{{{namespace}}}"
        "genInfo.company.id.shareholder.ShareDivideKey"
    )

    assert share_divide_key is not None
    assert len(share_divide_key) == 2

    assert share_divide_key[0].text == "25"
    assert share_divide_key[1].text == "100"

    for child in element.iter():
        if child is element:
            continue

        if len(child) == 0:
            assert child.get("contextRef") == "ctx-2025"


def test_xbrl_writer_includes_gcd_shareholder_in_instance() -> None:
    """Ein Gesellschafter-Tuple wird in die XBRL-Instanz aufgenommen."""

    namespace = (
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
                "100",
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

    writer = TaxonomyXbrlWriter()

    root = writer.instance_element(
        contexts={
            "ctx-2025": context,
        },
        units={},
        facts=(),
        shareholders=(
            shareholder,
        ),
        taxonomy_namespace=namespace,
        taxonomy_namespaces={
            "de-gcd": namespace,
        },
        entry_points=(),
    )

    tags = {
        element.tag
        for element in root.iter()
    }

    assert (
        f"{{{namespace}}}"
        "genInfo.company.id.shareholder"
    ) in tags

    assert (
        f"{{{namespace}}}"
        "genInfo.company.id.shareholder.legalStatus"
    ) in tags

    assert (
        f"{{{namespace}}}"
        "genInfo.company.id.shareholder.ShareDivideKey"
    ) in tags

def test_xbrl_writer_serializes_shareholder_current_number() -> None:
    """Der Writer serialisiert currentnumber als numerischen XBRL-Fact."""

    namespace = (
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

    concept = TaxonomyConcept(
        name=(
            "genInfo.company.id.shareholder.currentnumber"
        ),
        concept_id=(
            "de-gcd_genInfo.company.id.shareholder.currentnumber"
        ),
        type_name="xbrli:positiveIntegerItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    fact = TaxonomyFact(
        concept=concept,
        amount=Decimal("1"),
        context=context,
        unit=TaxonomyUnit.pure(),
        decimals="INF",
    )

    writer = TaxonomyXbrlWriter()

    element = writer.fact_element(
        fact=fact,
        context_id="ctx-2025",
        unit_id="PURE",
        namespace=namespace,
    )

    assert element.tag == (
        f"{{{namespace}}}"
        "genInfo.company.id.shareholder.currentnumber"
    )
    assert element.text == "1"
    assert element.get("contextRef") == "ctx-2025"
    assert element.get("unitRef") == "PURE"
    assert element.get("decimals") == "INF"
    

def test_xbrl_writer_serializes_gcd_company_classification_tuples() -> None:
    """Der Writer serialisiert beide GCD-Unternehmensklassifikationen."""

    namespace = (
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

    writer = TaxonomyXbrlWriter()

    branch_element = (
        writer.gcd_domestic_branch_of_foreign_company_element(
            branch=GcdDomesticBranchOfForeignCompany(
                fact=branch_fact,
            ),
            context_id="ctx-2025",
            namespace=namespace,
        )
    )

    business_element = (
        writer.gcd_entity_with_taxable_purpose_business_element(
            business=GcdEntityWithTaxablePurposeBusiness(
                fact=business_fact,
            ),
            context_id="ctx-2025",
            namespace=namespace,
        )
    )

    assert branch_element.tag == (
        f"{{{namespace}}}"
        "genInfo.company.id.domesticBranchOfForeignCompany"
    )

    assert len(branch_element) == 1
    assert branch_element[0].tag == (
        f"{{{namespace}}}"
        "genInfo.company.id.domesticBranchOfForeignCompany.HGB"
    )
    assert branch_element[0].attrib["contextRef"] == "ctx-2025"
    assert branch_element[0].text == "HGB"

    assert business_element.tag == (
        f"{{{namespace}}}"
        "genInfo.company.id.entityWithTaxablePurposeBusiness"
    )

    assert len(business_element) == 1
    assert business_element[0].tag == (
        f"{{{namespace}}}"
        "genInfo.company.id.entityWithTaxablePurposeBusiness.normal"
    )
    assert business_element[0].attrib["contextRef"] == "ctx-2025"
    assert business_element[0].text == "normal"
    
    
def test_xbrl_writer_serializes_optional_shareholder_identifiers() -> None:
    """Der Writer serialisiert beWiNr und idNotAssigned."""

    namespace = (
        "http://www.xbrl.de/taxonomies/"
        "de-gcd-2026-04-01"
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
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
        economic_id=text_fact(
            "genInfo.company.id.shareholder.beWiNr",
            "BEWI-1",
        ),
        id_not_assigned=text_fact(
            "genInfo.company.id.shareholder.idNotAssigned",
            "NO-ID",
        ),
    )

    writer = TaxonomyXbrlWriter()

    element = writer.gcd_shareholder_element(
        shareholder=shareholder,
        context_id="ctx-2026",
        namespace=namespace,
    )

    economic_id = element.find(
        f"{{{namespace}}}"
        "genInfo.company.id.shareholder.beWiNr"
    )

    assert economic_id is not None
    assert economic_id.text == "BEWI-1"
    assert economic_id.get("contextRef") == "ctx-2026"

    id_not_assigned = element.find(
        f"{{{namespace}}}"
        "genInfo.company.id.shareholder.idNotAssigned"
    )

    assert id_not_assigned is not None
    assert id_not_assigned.text == "NO-ID"
    assert id_not_assigned.get("contextRef") == "ctx-2026"


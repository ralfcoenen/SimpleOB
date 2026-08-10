"""Tests für die XBRL-Serialisierung."""

from datetime import date
from decimal import Decimal
from xml.etree import ElementTree as ET

from openbilanz.taxonomy.concept import (
    TaxonomyBalance,
    TaxonomyConcept,
    TaxonomyPeriodType,
)
from openbilanz.taxonomy.context import TaxonomyContext
from openbilanz.taxonomy.fact import TaxonomyFact
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

    fact = TaxonomyFact(
        concept=concept,
        amount=Decimal("125000.00"),
        context=context,
        unit=unit,
    )

    writer = TaxonomyXbrlWriter()

    root = writer.instance_element(
        context=context,
        context_id="ctx-2025",
        unit=unit,
        unit_id="EUR",
        facts=(fact,),
        taxonomy_namespace=DE_GAAP_CI_NAMESPACE,
    )

    assert root.tag == f"{{{XBRLI_NAMESPACE}}}xbrl"

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
    
"""Tests für die Serialisierung von XBRL-NIL-Facts."""

from datetime import date

from openbilanz.taxonomy.concept import (
    TaxonomyBalance,
    TaxonomyConcept,
    TaxonomyPeriodType,
)
from openbilanz.taxonomy.context import TaxonomyContext
from openbilanz.taxonomy.nil_fact import TaxonomyNilFact
from openbilanz.taxonomy.unit import TaxonomyUnit
from openbilanz.taxonomy.xbrl_writer import (
    XSI_NAMESPACE,
    TaxonomyXbrlWriter,
)
from openbilanz.exporter.xbrl_export import XbrlExporter



def create_numeric_nil_fact() -> TaxonomyNilFact:
    """Erzeugt einen monetären NIL-Fact für die Tests."""

    concept = TaxonomyConcept(
        name="bs.ass.currAss.cashEquiv.cash",
        concept_id="de-gaap-ci_bs.ass.currAss.cashEquiv.cash",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.INSTANT,
        balance=TaxonomyBalance.DEBIT,
        abstract=False,
        nillable=True,
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme="http://www.rzf-nrw.de/Steuernummer",
        period_type=TaxonomyPeriodType.INSTANT,
        start_date=None,
        end_date=date(2025, 12, 31),
    )

    return TaxonomyNilFact(
        concept=concept,
        context=context,
        unit=TaxonomyUnit.eur(),
    )


def test_xbrl_writer_serializes_numeric_nil_fact() -> None:
    """Ein numerisches NIL-Fact wird ohne Wert und decimals geschrieben."""

    namespace = (
        "http://www.xbrl.de/taxonomies/"
        "de-gaap-ci-2025-04-01"
    )

    fact = create_numeric_nil_fact()

    writer = TaxonomyXbrlWriter()

    element = writer.nil_fact_element(
        fact=fact,
        context_id="ctx-instant-2025",
        unit_id="EUR",
        namespace=namespace,
    )

    assert element.tag == (
        f"{{{namespace}}}"
        "bs.ass.currAss.cashEquiv.cash"
    )

    assert element.get("contextRef") == "ctx-instant-2025"
    assert element.get("unitRef") == "EUR"
    assert element.get(f"{{{XSI_NAMESPACE}}}nil") == "true"

    assert "decimals" not in element.attrib
    assert element.text is None


def test_xbrl_instance_contains_numeric_nil_fact() -> None:
    """Eine vollständige XBRL-Instanz übernimmt numerische NIL-Facts."""

    namespace = (
        "http://www.xbrl.de/taxonomies/"
        "de-gaap-ci-2025-04-01"
    )

    fact = create_numeric_nil_fact()

    writer = TaxonomyXbrlWriter()

    root = writer.instance_element(
        contexts={
            "ctx-instant-2025": fact.context,
        },
        units={
            "EUR": fact.unit,
        },
        facts=(),
        nil_facts=(
            fact,
        ),
        taxonomy_namespace=namespace,
        entry_points=(),
    )

    nil_elements = [
        element
        for element in root
        if element.tag
        == (
            f"{{{namespace}}}"
            "bs.ass.currAss.cashEquiv.cash"
        )
    ]

    assert len(nil_elements) == 1

    element = nil_elements[0]

    assert element.get("contextRef") == "ctx-instant-2025"
    assert element.get("unitRef") == "EUR"
    assert element.get(f"{{{XSI_NAMESPACE}}}nil") == "true"

    assert "decimals" not in element.attrib
    assert element.text is None


def test_xbrl_exporter_passes_numeric_nil_fact_to_writer() -> None:
    """Der Exporter übernimmt numerische NIL-Facts in die XBRL-Instanz."""

    namespace = (
        "http://www.xbrl.de/taxonomies/"
        "de-gaap-ci-2025-04-01"
    )

    fact = create_numeric_nil_fact()

    exporter = XbrlExporter()

    xml = exporter.export(
        contexts={
            "ctx-instant-2025": fact.context,
        },
        units={
            "EUR": fact.unit,
        },
        facts=(),
        nil_facts=(
            fact,
        ),
        taxonomy_namespace=namespace,
        entry_points=(),
    )

    assert "bs.ass.currAss.cashEquiv.cash" in xml
    assert 'contextRef="ctx-instant-2025"' in xml
    assert 'unitRef="EUR"' in xml
    assert 'nil="true"' in xml
    assert "decimals=" not in xml

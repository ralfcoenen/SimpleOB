"""Tests für die ELSTER-Nutzdatenhülle der E-Bilanz."""

from datetime import date
from xml.etree import ElementTree as ET

import pytest

from openbilanz.eric.elster_bilanz_payload import (
    EBILANZ_NAMESPACE,
    XBRL_NAMESPACE,
    ElsterBilanzPayloadBuilder,
    ElsterBilanzPayloadData,
)


def _minimal_xbrl() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<xbrli:xbrl xmlns:xbrli="{XBRL_NAMESPACE}">'
        "</xbrli:xbrl>"
    )


def _payload_data() -> ElsterBilanzPayloadData:
    return ElsterBilanzPayloadData(
        balance_sheet_date=date(2026, 12, 31),
        tax_office_number="5123",
        product_name="SimpleOB",
        product_version="0.44.0",
    )


def test_builds_elster_bilanz_payload() -> None:
    xml = ElsterBilanzPayloadBuilder().build(
        xbrl_xml=_minimal_xbrl(),
        data=_payload_data(),
    )

    root = ET.fromstring(xml)

    assert root.tag == "DatenTeil"

    nutzdatenblock = root.find("Nutzdatenblock")
    assert nutzdatenblock is not None

    header = nutzdatenblock.find("NutzdatenHeader")
    assert header is not None
    assert header.attrib["version"] == "11"

    ticket = header.find("NutzdatenTicket")
    assert ticket is not None
    assert ticket.text == "0001"

    empfaenger = header.find("Empfaenger")
    assert empfaenger is not None
    assert empfaenger.attrib["id"] == "F"
    assert empfaenger.text == "5123"

    hersteller = header.find("Hersteller")
    assert hersteller is not None

    product_name = hersteller.find("ProduktName")
    assert product_name is not None
    assert product_name.text == "SimpleOB"

    product_version = hersteller.find("ProduktVersion")
    assert product_version is not None
    assert product_version.text == "0.44.0"

    nutzdaten = nutzdatenblock.find("Nutzdaten")
    assert nutzdaten is not None

    e_bilanz = nutzdaten.find(
        f"{{{EBILANZ_NAMESPACE}}}EBilanz"
    )
    assert e_bilanz is not None
    assert e_bilanz.attrib["version"] == "000002"

    stichtag = e_bilanz.find(
        f"{{{EBILANZ_NAMESPACE}}}stichtag"
    )
    assert stichtag is not None
    assert stichtag.text == "20261231"

    xbrl = e_bilanz.find(
        f"{{{XBRL_NAMESPACE}}}xbrl"
    )
    assert xbrl is not None


def test_daten_teil_start_tag_contains_no_namespace_declaration() -> None:
    xml = ElsterBilanzPayloadBuilder().build(
        xbrl_xml=_minimal_xbrl(),
        data=_payload_data(),
    )

    daten_teil_start = xml.split("<DatenTeil", maxsplit=1)[1].split(
        ">",
        maxsplit=1,
    )[0]

    assert "xmlns" not in daten_teil_start


def test_preserves_xbrl_namespace_prefixes() -> None:
    xbrl_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<xbrli:xbrl xmlns:xbrli="{XBRL_NAMESPACE}" '
        'xmlns:test="urn:simpleob:test">'
        '<test:fact contextRef="C1">1</test:fact>'
        "</xbrli:xbrl>"
    )

    xml = ElsterBilanzPayloadBuilder().build(
        xbrl_xml=xbrl_xml,
        data=_payload_data(),
    )

    assert '<xbrli:xbrl xmlns:xbrli="' in xml
    assert 'xmlns:test="urn:simpleob:test"' in xml
    assert "<test:fact contextRef=\"C1\">1</test:fact>" in xml


def test_removes_nested_xbrl_xml_declaration() -> None:
    xml = ElsterBilanzPayloadBuilder().build(
        xbrl_xml=_minimal_xbrl(),
        data=_payload_data(),
    )

    assert xml.count("<?xml") == 1


def test_builds_optional_data_supplier() -> None:
    data = ElsterBilanzPayloadData(
        balance_sheet_date=date(2026, 12, 31),
        tax_office_number="5123",
        product_name="SimpleOB",
        product_version="0.44.0",
        data_supplier=(
            "Max Mustermann; Musterstraße; 1;;;; "
            "40210; Düsseldorf; DE;;;"
        ),
    )

    xml = ElsterBilanzPayloadBuilder().build(
        xbrl_xml=_minimal_xbrl(),
        data=data,
    )

    root = ET.fromstring(xml)
    header = root.find(
        "./Nutzdatenblock/NutzdatenHeader"
    )
    assert header is not None

    data_supplier = header.find("DatenLieferant")
    assert data_supplier is not None
    assert data_supplier.text == data.data_supplier


def test_omits_data_supplier_when_not_configured() -> None:
    xml = ElsterBilanzPayloadBuilder().build(
        xbrl_xml=_minimal_xbrl(),
        data=_payload_data(),
    )

    root = ET.fromstring(xml)
    header = root.find(
        "./Nutzdatenblock/NutzdatenHeader"
    )
    assert header is not None

    assert header.find("DatenLieferant") is None


def test_rejects_invalid_tax_office_number() -> None:
    data = ElsterBilanzPayloadData(
        balance_sheet_date=date(2026, 12, 31),
        tax_office_number="123",
        product_name="SimpleOB",
        product_version="0.44.0",
    )

    with pytest.raises(
        ValueError,
        match="Finanzamtsnummer",
    ):
        ElsterBilanzPayloadBuilder().build(
            xbrl_xml=_minimal_xbrl(),
            data=data,
        )


def test_rejects_non_xbrl_document() -> None:
    with pytest.raises(
        ValueError,
        match="xbrli:xbrl",
    ):
        ElsterBilanzPayloadBuilder().build(
            xbrl_xml="<document />",
            data=_payload_data(),
        )


def test_rejects_invalid_xbrl_xml() -> None:
    with pytest.raises(
        ValueError,
        match="kein gültiges XML",
    ):
        ElsterBilanzPayloadBuilder().build(
            xbrl_xml="<xbrli:xbrl",
            data=_payload_data(),
        )

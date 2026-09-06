"""Tests für die ELSTER-Nutzdatenvorbereitung von SimpleOB."""

from datetime import date
from uuid import uuid4
from xml.etree import ElementTree as ET

import openbilanz.eric.elster_bilanz_payload_service as service_module
from openbilanz.domain.company import Company
from openbilanz.domain.company_master_data import CompanyMasterData
from openbilanz.eric.elster_bilanz_payload import XBRL_NAMESPACE
from openbilanz.eric.elster_bilanz_payload_service import (
    ElsterBilanzPayloadService,
)


def _minimal_xbrl() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<xbrli:xbrl xmlns:xbrli="{XBRL_NAMESPACE}">'
        "</xbrli:xbrl>"
    )


def _company_master_data() -> CompanyMasterData:
    return CompanyMasterData(
        company=Company(
            company_id=uuid4(),
            name="SimpleOB Test UG",
        ),
        legal_form="GmbH",
        tax_number="123/4567/8901",
        federal_state="NW",
        street="Musterstraße",
        house_number="1",
        postal_code="40210",
        city="Düsseldorf",
        country="DE",
        business="Softwareentwicklung",
    )


def test_builds_payload_from_company_master_data(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        service_module,
        "get_application_version",
        lambda: "0.44.0",
    )

    xml = ElsterBilanzPayloadService().build(
        xbrl_xml=_minimal_xbrl(),
        master_data=_company_master_data(),
        balance_sheet_date=date(2026, 12, 31),
    )

    root = ET.fromstring(xml)

    assert root.tag == "DatenTeil"

    header = root.find(
        "./Nutzdatenblock/NutzdatenHeader"
    )
    assert header is not None

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


def test_builds_optional_data_supplier(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        service_module,
        "get_application_version",
        lambda: "0.44.0",
    )

    data_supplier = (
        "Max Mustermann; Musterstraße; 1;;;; "
        "40210; Düsseldorf; DE; 0211 123456; max@example.test"
    )

    xml = ElsterBilanzPayloadService().build(
        xbrl_xml=_minimal_xbrl(),
        master_data=_company_master_data(),
        balance_sheet_date=date(2026, 12, 31),
        data_supplier=data_supplier,
    )

    root = ET.fromstring(xml)

    header = root.find(
        "./Nutzdatenblock/NutzdatenHeader"
    )
    assert header is not None

    element = header.find("DatenLieferant")
    assert element is not None
    assert element.text == data_supplier

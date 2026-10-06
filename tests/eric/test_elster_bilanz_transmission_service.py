"""Tests für den ELSTER-Bilanz-Übermittlungsservice."""

from datetime import date
from pathlib import Path
from types import SimpleNamespace

from openbilanz.eric.elster_bilanz_transmission_service import (
    ELSTER_TEST_MARKER,
    ElsterBilanzTransmissionService,
)
from openbilanz.eric.eric_send_adapter import EricSendResult
from openbilanz.eric.eric_validate_adapter import EricValidationResult


class FakePayloadService:
    def __init__(self) -> None:
        self.calls = []

    def build(
        self,
        *,
        xbrl_xml,
        master_data,
        balance_sheet_date,
        data_supplier=None,
    ):
        self.calls.append(
            {
                "xbrl_xml": xbrl_xml,
                "master_data": master_data,
                "balance_sheet_date": balance_sheet_date,
                "data_supplier": data_supplier,
            }
        )
        return "<DatenTeil>test</DatenTeil>"

class FakeCreateThAdapter:
    def __init__(self) -> None:
        self.calls = []

    def create(
        self,
        *,
        data_part_xml,
        manufacturer_id,
        version_client,
        data_supplier=None,
        test_marker=None,
    ):
        self.calls.append(
            {
                "data_part_xml": data_part_xml,
                "manufacturer_id": manufacturer_id,
                "version_client": version_client,
                "data_supplier": data_supplier,
                "test_marker": test_marker,
            }
        )

        if test_marker is None:
            return "<Elster></Elster>"

        return (
            "<Elster>"
            f"<Testmerker>{test_marker}</Testmerker>"
            "</Elster>"
        )

class FakeValidateAdapter:
    def __init__(self) -> None:
        self.calls = []

    def validate(
        self,
        *,
        elster_xml,
        datenart_version,
    ):
        self.calls.append(
            {
                "elster_xml": elster_xml,
                "datenart_version": datenart_version,
            }
        )

        return EricValidationResult(
            response_xml="<Erfolg/>",
        )


class FakeSendAdapter:
    def __init__(self) -> None:
        self.calls = []

    def send(
        self,
        *,
        elster_xml,
        certificate_path,
        certificate_pin,
        datenart_version,
    ):
        self.calls.append(
            {
                "elster_xml": elster_xml,
                "certificate_path": certificate_path,
                "certificate_pin": certificate_pin,
                "datenart_version": datenart_version,
            }
        )

        return EricSendResult(
            response_xml="<Erfolg/>",
            server_response_xml="<Code>0</Code>",
            transfer_ticket="TEST-TRANSFER-TICKET",
        )


def test_test_transmission_uses_validated_test_marker_path() -> None:
    payload_service = FakePayloadService()
    create_th_adapter = FakeCreateThAdapter()
    validate_adapter = FakeValidateAdapter()
    send_adapter = FakeSendAdapter()

    certificate_path = Path(
        "/test/test-softidnr-pse.pfx"
    )

    service = ElsterBilanzTransmissionService(
        payload_service=payload_service,
        create_th_adapter=create_th_adapter,
        validate_adapter=validate_adapter,
        send_adapter=send_adapter,
        manufacturer_id="22924",
    )

    master_data = SimpleNamespace()

    validated = service.validate_test_transmission(
        xbrl_xml="<xbrl/>",
        master_data=master_data,
        balance_sheet_date=date(2026, 12, 31),
        data_supplier="SimpleOB Testdatenlieferant",
    )

    assert validated.data_part_xml == (
        "<DatenTeil>test</DatenTeil>"
    )

    assert create_th_adapter.calls[0]["test_marker"] == (
        ELSTER_TEST_MARKER
    )

    assert create_th_adapter.calls[0]["manufacturer_id"] == (
        "22924"
    )

    assert validate_adapter.calls[0]["elster_xml"] == (
        validated.elster_xml
    )

    result = service.send_test_transmission(
        validated=validated,
        certificate_path=certificate_path,
        certificate_pin="123456",
    )

    assert send_adapter.calls == [
        {
            "elster_xml": validated.elster_xml,
            "certificate_path": certificate_path,
            "certificate_pin": "123456",
            "datenart_version": "Bilanz_6.9",
        }
    ]

    assert result.response_xml == "<Erfolg/>"
    assert result.server_response_xml == "<Code>0</Code>"

def test_production_transmission_uses_path_without_test_marker() -> None:
    payload_service = FakePayloadService()
    create_th_adapter = FakeCreateThAdapter()
    validate_adapter = FakeValidateAdapter()
    send_adapter = FakeSendAdapter()

    certificate_path = Path(
        "/test/test-softidnr-pse.pfx"
    )

    service = ElsterBilanzTransmissionService(
        payload_service=payload_service,
        create_th_adapter=create_th_adapter,
        validate_adapter=validate_adapter,
        send_adapter=send_adapter,
        manufacturer_id="22924",
    )

    master_data = SimpleNamespace()

    validated = service.validate_production_transmission(
        xbrl_xml="<xbrl/>",
        master_data=master_data,
        balance_sheet_date=date(2026, 12, 31),
        data_supplier="SimpleOB Testdatenlieferant",
    )

    assert validated.data_part_xml == (
        "<DatenTeil>test</DatenTeil>"
    )

    assert create_th_adapter.calls[0]["test_marker"] is None

    assert "<Testmerker" not in validated.elster_xml

    assert validate_adapter.calls[0]["elster_xml"] == (
        validated.elster_xml
    )

    result = service.send_production_transmission(
        validated=validated,
        certificate_path=certificate_path,
        certificate_pin="123456",
    )

    assert send_adapter.calls == [
        {
            "elster_xml": validated.elster_xml,
            "certificate_path": certificate_path,
            "certificate_pin": "123456",
            "datenart_version": "Bilanz_6.9",
        }
    ]

    assert result.response_xml == "<Erfolg/>"
    assert result.server_response_xml == "<Code>0</Code>"

def test_production_transmission_rejects_test_marker_before_send() -> None:
    payload_service = FakePayloadService()
    create_th_adapter = FakeCreateThAdapter()
    validate_adapter = FakeValidateAdapter()
    send_adapter = FakeSendAdapter()
    certificate_path = Path(
        "/test/test-softidnr-pse.pfx"
    )

    service = ElsterBilanzTransmissionService(
        payload_service=payload_service,
        create_th_adapter=create_th_adapter,
        validate_adapter=validate_adapter,
        send_adapter=send_adapter,
        manufacturer_id="22924",
    )

    validated = service.validate_production_transmission(
        xbrl_xml="<xbrl/>",
        master_data=SimpleNamespace(),
        balance_sheet_date=date(2026, 12, 31),
        data_supplier="SimpleOB Testdatenlieferant",
    )

    manipulated = type(validated)(
        data_part_xml=validated.data_part_xml,
        elster_xml=(
            "<Elster>"
            "<Testmerker>700000004</Testmerker>"
            "</Elster>"
        ),
        eric_validation=validated.eric_validation,
    )

    try:
        service.send_production_transmission(
            validated=manipulated,
            certificate_path=certificate_path,
            certificate_pin="123456",
        )

    except RuntimeError as exc:
        assert "SICHERHEITSABBRUCH" in str(exc)
    else:
        raise AssertionError(
            "Produktivversand mit Testmerker wurde nicht abgebrochen."
        )

    assert send_adapter.calls == []

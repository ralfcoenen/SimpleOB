"""Produktservice für die ERiC-/ELSTER-Verarbeitung einer E-Bilanz."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from xml.etree import ElementTree as ET

from openbilanz.core.version import get_application_version
from openbilanz.domain.company_master_data import CompanyMasterData
from openbilanz.eric.elster_bilanz_payload_service import (
    ElsterBilanzPayloadService,
)
from openbilanz.eric.eric_create_th_adapter import (
    EricCreateThAdapter,
)
from openbilanz.eric.eric_send_adapter import (
    EricSendAdapter,
    EricSendResult,
)
from openbilanz.eric.eric_validate_adapter import (
    EricValidateAdapter,
    EricValidationResult,
)


ELSTER_TEST_MARKER = "700000004"
DEFAULT_BILANZ_DATENART_VERSION = "Bilanz_6.9"


@dataclass(frozen=True)
class ElsterBilanzValidationResult:
    """Ergebnis der Vorbereitung und lokalen ERiC-Validierung."""

    data_part_xml: str
    elster_xml: str
    eric_validation: EricValidationResult


class ElsterBilanzTransmissionService:
    """Koordiniert die ERiC-/ELSTER-Verarbeitung einer E-Bilanz."""

    def __init__(
        self,
        *,
        payload_service: ElsterBilanzPayloadService,
        create_th_adapter: EricCreateThAdapter,
        validate_adapter: EricValidateAdapter,
        send_adapter: EricSendAdapter,
        manufacturer_id: str,
        data_supplier: str,
        certificate_path: Path,
        certificate_pin: str,
    ) -> None:
        manufacturer_id = manufacturer_id.strip()
        data_supplier = data_supplier.strip()

        if not manufacturer_id:
            raise ValueError(
                "Die ERiC-Hersteller-ID darf nicht leer sein."
            )

        if not data_supplier:
            raise ValueError(
                "Der ELSTER-Datenlieferant darf nicht leer sein."
            )

        if not certificate_pin:
            raise ValueError(
                "Die ELSTER-Zertifikats-PIN darf nicht leer sein."
            )

        self._payload_service = payload_service
        self._create_th_adapter = create_th_adapter
        self._validate_adapter = validate_adapter
        self._send_adapter = send_adapter
        self._manufacturer_id = manufacturer_id
        self._data_supplier = data_supplier
        self._certificate_path = Path(
            certificate_path
        ).expanduser()
        self._certificate_pin = certificate_pin


    def validate_test_transmission(
        self,
        *,
        xbrl_xml: str,
        master_data: CompanyMasterData,
        balance_sheet_date: date,
        datenart_version: str = DEFAULT_BILANZ_DATENART_VERSION,
    ) -> ElsterBilanzValidationResult:
        """Bereitet eine Testsendung vor und validiert sie lokal mit ERiC."""

        data_part_xml = self._payload_service.build(
            xbrl_xml=xbrl_xml,
            master_data=master_data,
            balance_sheet_date=balance_sheet_date,
            data_supplier=self._data_supplier,
        )

        elster_xml = self._create_th_adapter.create(
            data_part_xml=data_part_xml,
            manufacturer_id=self._manufacturer_id,
            version_client=get_application_version(),
            data_supplier=self._data_supplier,
            test_marker=ELSTER_TEST_MARKER,
        )

        self._assert_test_marker(
            elster_xml=elster_xml,
            expected_test_marker=ELSTER_TEST_MARKER,
        )

        validation_result = self._validate_adapter.validate(
            elster_xml=elster_xml,
            datenart_version=datenart_version,
        )

        return ElsterBilanzValidationResult(
            data_part_xml=data_part_xml,
            elster_xml=elster_xml,
            eric_validation=validation_result,
        )

    def validate_production_transmission(
        self,
        *,
        xbrl_xml: str,
        master_data: CompanyMasterData,
        balance_sheet_date: date,
        datenart_version: str = DEFAULT_BILANZ_DATENART_VERSION,
    ) -> ElsterBilanzValidationResult:
        """Bereitet eine Produktivsendung vor und validiert sie lokal mit ERiC."""

        data_part_xml = self._payload_service.build(
            xbrl_xml=xbrl_xml,
            master_data=master_data,
            balance_sheet_date=balance_sheet_date,
            data_supplier=self._data_supplier,
        )

        elster_xml = self._create_th_adapter.create(
            data_part_xml=data_part_xml,
            manufacturer_id=self._manufacturer_id,
            version_client=get_application_version(),
            data_supplier=self._data_supplier,
            test_marker=None,
        )

        self._assert_no_test_marker(
            elster_xml=elster_xml,
        )

        validation_result = self._validate_adapter.validate(
            elster_xml=elster_xml,
            datenart_version=datenart_version,
        )

        return ElsterBilanzValidationResult(
            data_part_xml=data_part_xml,
            elster_xml=elster_xml,
            eric_validation=validation_result,
        )

    def send_test_transmission(
        self,
        *,
        validated: ElsterBilanzValidationResult,
        datenart_version: str = DEFAULT_BILANZ_DATENART_VERSION,
    ) -> EricSendResult:
        """Versendet einen zuvor lokal validierten ELSTER-Testdatensatz."""

        self._assert_test_marker(
            elster_xml=validated.elster_xml,
            expected_test_marker=ELSTER_TEST_MARKER,
        )

        return self._send_adapter.send(
            elster_xml=validated.elster_xml,
            certificate_path=self._certificate_path,
            certificate_pin=self._certificate_pin,
            datenart_version=datenart_version,
        )

    def send_production_transmission(
        self,
        *,
        validated: ElsterBilanzValidationResult,
        datenart_version: str = DEFAULT_BILANZ_DATENART_VERSION,
    ) -> EricSendResult:
        """Versendet einen zuvor lokal validierten ELSTER-Produktivdatensatz."""

        self._assert_no_test_marker(
            elster_xml=validated.elster_xml,
        )

        return self._send_adapter.send(
            elster_xml=validated.elster_xml,
            certificate_path=self._certificate_path,
            certificate_pin=self._certificate_pin,
            datenart_version=datenart_version,
        )

    @staticmethod
    def _assert_test_marker(
        *,
        elster_xml: str,
        expected_test_marker: str,
    ) -> None:
        """Verhindert einen Testversand ohne den erwarteten Testmerker."""

        try:
            root = ET.fromstring(elster_xml)
        except ET.ParseError as exc:
            raise RuntimeError(
                "Das von EricCreateTH erzeugte ElsterXML "
                "konnte nicht geparst werden. "
                "Ein Versand wird nicht durchgeführt."
            ) from exc

        test_markers: list[str] = []

        for element in root.iter():
            local_name = element.tag.rsplit("}", 1)[-1]

            if local_name != "Testmerker":
                continue

            test_markers.append(
                (element.text or "").strip()
            )

        if test_markers != [expected_test_marker]:
            raise RuntimeError(
                "SICHERHEITSABBRUCH: "
                "Das ElsterXML enthält nicht genau den erwarteten "
                f"Testmerker {expected_test_marker!r}. "
                f"Gefunden: {test_markers!r}. "
                "Es werden keine Daten an ELSTER gesendet."
            )

    @staticmethod
    def _assert_no_test_marker(
        *,
        elster_xml: str,
    ) -> None:
        """Verhindert einen Produktivversand mit einem Testmerker."""

        try:
            root = ET.fromstring(elster_xml)
        except ET.ParseError as exc:
            raise RuntimeError(
                "Das von EricCreateTH erzeugte ElsterXML "
                "konnte nicht geparst werden. "
                "Ein Versand wird nicht durchgeführt."
            ) from exc

        test_markers: list[str] = []

        for element in root.iter():
            local_name = element.tag.rsplit("}", 1)[-1]

            if local_name != "Testmerker":
                continue

            test_markers.append(
                (element.text or "").strip()
            )

        if test_markers:
            raise RuntimeError(
                "SICHERHEITSABBRUCH: "
                "Das ElsterXML für eine Produktivübermittlung "
                "enthält mindestens einen Testmerker. "
                f"Gefunden: {test_markers!r}. "
                "Es werden keine Daten an ELSTER gesendet."
            )

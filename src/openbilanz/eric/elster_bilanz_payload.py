"""ELSTER-Nutzdatenhülle für E-Bilanzen."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from xml.etree import ElementTree as ET

EBILANZ_NAMESPACE = "http://rzf.fin-nrw.de/RMS/EBilanz/2016/XMLSchema"
XBRL_NAMESPACE = "http://www.xbrl.org/2003/instance"


@dataclass(frozen=True, slots=True)
class ElsterBilanzPayloadData:
    """Metadaten für die ELSTER-Nutzdatenhülle einer E-Bilanz."""

    balance_sheet_date: date
    tax_office_number: str
    product_name: str
    product_version: str
    data_supplier: str | None = None
    ticket: str = "0001"


class ElsterBilanzPayloadBuilder:
    """Baut den DatenTeil für eine E-Bilanz."""

    def build(
        self,
        *,
        xbrl_xml: str,
        data: ElsterBilanzPayloadData,
    ) -> str:
        self._validate_data(data)

        self._validate_xbrl(xbrl_xml)
        xbrl_body = self._without_xml_declaration(xbrl_xml)

        header_xml = self._build_header(data)

        e_bilanz_xml = (
            f'<ebilanz:EBilanz xmlns:ebilanz="{EBILANZ_NAMESPACE}" '
            'version="000002">'
            "<ebilanz:stichtag>"
            f"{data.balance_sheet_date:%Y%m%d}"
            "</ebilanz:stichtag>"
            f"{xbrl_body}"
            "</ebilanz:EBilanz>"
        )

        return (
            '<?xml version="1.0" encoding="utf-8"?>'
            "<DatenTeil>"
            "<Nutzdatenblock>"
            f"{header_xml}"
            "<Nutzdaten>"
            f"{e_bilanz_xml}"
            "</Nutzdaten>"
            "</Nutzdatenblock>"
            "</DatenTeil>"
        )

    @staticmethod
    def _build_header(data: ElsterBilanzPayloadData) -> str:
        header = ET.Element(
            "NutzdatenHeader",
            {"version": "11"},
        )

        ET.SubElement(
            header,
            "NutzdatenTicket",
        ).text = data.ticket

        empfaenger = ET.SubElement(
            header,
            "Empfaenger",
            {"id": "F"},
        )
        empfaenger.text = data.tax_office_number

        hersteller = ET.SubElement(
            header,
            "Hersteller",
        )
        ET.SubElement(
            hersteller,
            "ProduktName",
        ).text = data.product_name
        ET.SubElement(
            hersteller,
            "ProduktVersion",
        ).text = data.product_version

        if data.data_supplier:
            ET.SubElement(
                header,
                "DatenLieferant",
            ).text = data.data_supplier

        return ET.tostring(
            header,
            encoding="unicode",
            short_empty_elements=True,
        )

    @staticmethod
    def _validate_xbrl(xbrl_xml: str) -> None:
        try:
            root = ET.fromstring(xbrl_xml)
        except ET.ParseError as exc:
            raise ValueError(
                "Das übergebene XBRL-Dokument ist kein gültiges XML."
            ) from exc

        if root.tag != f"{{{XBRL_NAMESPACE}}}xbrl":
            raise ValueError(
                "Das übergebene Dokument besitzt kein xbrli:xbrl-Wurzelelement."
            )

    @staticmethod
    def _without_xml_declaration(xml: str) -> str:
        stripped = xml.lstrip()

        if not stripped.startswith("<?xml"):
            return stripped

        declaration_end = stripped.find("?>")
        if declaration_end < 0:
            raise ValueError(
                "Die XML-Deklaration des XBRL-Dokuments ist unvollständig."
            )

        return stripped[declaration_end + 2 :].lstrip()

    @staticmethod
    def _validate_data(data: ElsterBilanzPayloadData) -> None:
        if (
            len(data.tax_office_number) != 4
            or not data.tax_office_number.isdigit()
        ):
            raise ValueError(
                "Die Finanzamtsnummer muss genau vier Ziffern enthalten."
            )

        if not data.product_name.strip():
            raise ValueError("Der Produktname darf nicht leer sein.")

        if len(data.product_name) > 50:
            raise ValueError(
                "Der Produktname darf höchstens 50 Zeichen enthalten."
            )

        if not data.product_version.strip():
            raise ValueError("Die Produktversion darf nicht leer sein.")

        if len(data.product_version) > 50:
            raise ValueError(
                "Die Produktversion darf höchstens 50 Zeichen enthalten."
            )

        if not data.ticket.strip():
            raise ValueError("Das NutzdatenTicket darf nicht leer sein.")

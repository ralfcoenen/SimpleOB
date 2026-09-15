"""ERiC-Adapter zum Senden eines vollständigen ELSTER-Datensatzes."""

from __future__ import annotations

import importlib
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast
from xml.etree import ElementTree as ET

from openbilanz.eric.eric_create_th_adapter import (
    EricApiProtocol,
    _create_official_eric,
)

ERIC_OK = 0
ERIC_VALIDIERE = 1 << 1
ERIC_SENDE = 1 << 2

ERIC_SEND_FLAGS = ERIC_VALIDIERE | ERIC_SENDE

DEFAULT_BILANZ_DATENART_VERSION = "Bilanz_6.9"


@dataclass(frozen=True)
class EricSendResult:
    """Ergebnis einer erfolgreichen ELSTER-Übermittlung."""

    response_xml: str
    server_response_xml: str
    transfer_ticket: str


class EricSendError(RuntimeError):
    """Fehler bei der ELSTER-Übermittlung mit ERiC."""

    def __init__(
        self,
        message: str,
        *,
        error_code: int | None = None,
        error_text: str | None = None,
        response_xml: str | None = None,
        server_response_xml: str | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.error_text = error_text
        self.response_xml = response_xml
        self.server_response_xml = server_response_xml


class EricCryptoParameterProtocol(Protocol):
    """Benötigte Eigenschaften der offiziellen ERiC-Struktur."""

    version: int
    zertifikatHandle: int
    pin: str | None


class EricSendApiProtocol(EricApiProtocol, Protocol):
    """Benötigter Ausschnitt aus dem offiziellen ERiC-Python-Wrapper."""

    def PyEricGetHandleToCertificate(
        self,
        pathToKeystore,
    ) -> tuple[int, int, int]: ...

    def PyEricCloseHandleToCertificate(
        self,
        hToken,
    ) -> int: ...

    def PyEricBearbeiteVorgang(
        self,
        datenpuffer,
        datenartVersion,
        bearbeitungsFlags,
        druckParameter,
        cryptoParameter,
        rueckgabeXmlPuffer,
        serverantwortXmlPuffer,
    ) -> int: ...


EricFactory = Callable[
    [Path, Path | None],
    EricSendApiProtocol,
]

CryptoParameterFactory = Callable[
    [Path],
    EricCryptoParameterProtocol,
]


class EricSendAdapter:
    """Validiert und sendet ein vollständiges ELSTER-XML mit ERiC."""

    def __init__(
        self,
        *,
        lib_dir: Path,
        log_dir: Path | None = None,
        eric_factory: EricFactory | None = None,
        crypto_parameter_factory: CryptoParameterFactory | None = None,
    ) -> None:
        self._lib_dir = Path(lib_dir).expanduser()
        self._log_dir = Path(log_dir).expanduser() if log_dir else None

        self._eric_factory = eric_factory or cast(
            EricFactory,
            _create_official_eric,
        )
        self._crypto_parameter_factory = (
            crypto_parameter_factory
            or _create_official_crypto_parameter
        )

    def send(
        self,
        *,
        elster_xml: str,
        certificate_path: Path,
        certificate_pin: str,
        datenart_version: str = DEFAULT_BILANZ_DATENART_VERSION,
    ) -> EricSendResult:
        """Validiert und sendet einen vollständigen ELSTER-Datensatz."""
        if not elster_xml.strip():
            raise ValueError(
                "Das zu sendende ELSTER-XML darf nicht leer sein."
            )

        datenart_version = datenart_version.strip()

        if not datenart_version:
            raise ValueError(
                "Die ERiC-DatenartVersion darf nicht leer sein."
            )

        certificate_path = Path(certificate_path).expanduser()

        if not certificate_path.is_file():
            raise ValueError(
                "Die ELSTER-Zertifikatsdatei existiert nicht: "
                f"{certificate_path}"
            )

        if not certificate_pin:
            raise ValueError(
                "Die PIN des ELSTER-Zertifikats darf nicht leer sein."
            )

        eric = self._eric_factory(
            self._lib_dir,
            self._log_dir,
        )

        try:
            return self._send_with_eric(
                eric=eric,
                elster_xml=elster_xml,
                certificate_path=certificate_path,
                certificate_pin=certificate_pin,
                datenart_version=datenart_version,
            )
        finally:
            self._close_eric(eric)

    def _send_with_eric(
        self,
        *,
        eric: EricSendApiProtocol,
        elster_xml: str,
        certificate_path: Path,
        certificate_pin: str,
        datenart_version: str,
    ) -> EricSendResult:
        result_code, certificate_handle, _pin_support = (
            eric.PyEricGetHandleToCertificate(
                str(certificate_path)
            )
        )

        if result_code != ERIC_OK:
            error_text = self._get_error_text(
                eric=eric,
                error_code=result_code,
            )
            raise EricSendError(
                "Das ELSTER-Zertifikat konnte nicht geöffnet werden "
                f"(Fehler {result_code}): {error_text}",
                error_code=result_code,
                error_text=error_text,
            )

        try:
            crypto_parameter = self._crypto_parameter_factory(
                self._lib_dir
            )
            crypto_parameter.version = 3
            crypto_parameter.zertifikatHandle = certificate_handle
            crypto_parameter.pin = certificate_pin

            return self._send_with_certificate(
                eric=eric,
                elster_xml=elster_xml,
                datenart_version=datenart_version,
                crypto_parameter=crypto_parameter,
            )
        finally:
            close_result = eric.PyEricCloseHandleToCertificate(
                certificate_handle
            )

            if close_result != ERIC_OK:
                raise EricSendError(
                    "Das ELSTER-Zertifikat konnte nicht "
                    "ordnungsgemäß geschlossen werden "
                    f"(Fehler {close_result}).",
                    error_code=close_result,
                )

    def _send_with_certificate(
        self,
        *,
        eric: EricSendApiProtocol,
        elster_xml: str,
        datenart_version: str,
        crypto_parameter: EricCryptoParameterProtocol,
    ) -> EricSendResult:
        response_buffer = eric.PyEricRueckgabepufferErzeugen()

        if response_buffer is None:
            raise EricSendError(
                "ERiC konnte keinen Rückgabepuffer für "
                "EricBearbeiteVorgang erzeugen."
            )

        try:
            server_response_buffer = (
                eric.PyEricRueckgabepufferErzeugen()
            )

            if server_response_buffer is None:
                raise EricSendError(
                    "ERiC konnte keinen Puffer für die "
                    "ELSTER-Serverantwort erzeugen."
                )

            try:
                result_code = eric.PyEricBearbeiteVorgang(
                    datenpuffer=elster_xml,
                    datenartVersion=datenart_version,
                    bearbeitungsFlags=ERIC_SEND_FLAGS,
                    druckParameter=None,
                    cryptoParameter=crypto_parameter,
                    rueckgabeXmlPuffer=response_buffer,
                    serverantwortXmlPuffer=server_response_buffer,
                )

                response_xml = self._decode_response(
                    eric.PyEricRueckgabepufferInhalt(
                        response_buffer
                    )
                )
                server_response_xml = self._decode_response(
                    eric.PyEricRueckgabepufferInhalt(
                        server_response_buffer
                    )
                )

                if result_code != ERIC_OK:
                    error_text = self._get_error_text(
                        eric=eric,
                        error_code=result_code,
                    )

                    raise EricSendError(
                        "EricBearbeiteVorgang ist bei der "
                        "ELSTER-Übermittlung fehlgeschlagen "
                        f"(Fehler {result_code}): {error_text}",
                        error_code=result_code,
                        error_text=error_text,
                        response_xml=response_xml,
                        server_response_xml=server_response_xml,
                    )

                transfer_ticket = self._extract_transfer_ticket(
                    response_xml=response_xml,
                    server_response_xml=server_response_xml,
                )

                return EricSendResult(
                    response_xml=response_xml,
                    server_response_xml=server_response_xml,
                    transfer_ticket=transfer_ticket,
                )
            finally:
                eric.PyEricRueckgabepufferFreigeben(
                    server_response_buffer
                )
        finally:
            eric.PyEricRueckgabepufferFreigeben(
                response_buffer
            )

    @staticmethod
    def _extract_transfer_ticket(
        *,
        response_xml: str,
        server_response_xml: str,
    ) -> str:
        """Liest das von ERiC erzeugte ELSTER-Transferticket."""

        transfer_tickets: list[str] = []

        for xml_text in (
            response_xml,
            server_response_xml,
        ):
            if not xml_text.strip():
                continue

            try:
                root = ET.fromstring(xml_text)
            except ET.ParseError:
                continue

            for element in root.iter():
                local_name = element.tag.rsplit("}", 1)[-1]

                if local_name != "TransferTicket":
                    continue

                transfer_ticket = (element.text or "").strip()

                if (
                    transfer_ticket
                    and transfer_ticket not in transfer_tickets
                ):
                    transfer_tickets.append(transfer_ticket)

        if len(transfer_tickets) != 1:
            raise EricSendError(
                "Die ELSTER-Übermittlung war erfolgreich, "
                "aber das von ERiC erzeugte TransferTicket "
                "konnte nicht eindeutig ermittelt werden. "
                f"Gefundene TransferTickets: {transfer_tickets!r}"
            )

        return transfer_tickets[0]

    @staticmethod
    def _decode_response(response_bytes: bytes) -> str:
        if not response_bytes:
            return ""

        return response_bytes.decode(
            "utf-8",
            errors="replace",
        )

    @staticmethod
    def _get_error_text(
        *,
        eric: EricSendApiProtocol,
        error_code: int,
    ) -> str:
        error_buffer = eric.PyEricRueckgabepufferErzeugen()

        if error_buffer is None:
            return "Kein ERiC-Fehlertext verfügbar."

        try:
            text_result_code = eric.PyEricHoleFehlerText(
                error_code,
                error_buffer,
            )

            if text_result_code != ERIC_OK:
                return (
                    "Kein ERiC-Fehlertext verfügbar "
                    f"(EricHoleFehlerText: {text_result_code})."
                )

            error_bytes = eric.PyEricRueckgabepufferInhalt(
                error_buffer
            )

            if not error_bytes:
                return "Kein ERiC-Fehlertext verfügbar."

            return error_bytes.decode(
                "utf-8",
                errors="replace",
            ).strip()
        finally:
            eric.PyEricRueckgabepufferFreigeben(
                error_buffer
            )

    @staticmethod
    def _close_eric(eric: EricSendApiProtocol) -> None:
        result_code = eric.PyEricBeende()

        if result_code == ERIC_OK:
            eric._eric_initialized = False
            return

        raise EricSendError(
            "ERiC konnte nicht ordnungsgemäß beendet werden "
            f"(Fehler {result_code})."
        )


def _create_official_crypto_parameter(
    lib_dir: Path,
) -> EricCryptoParameterProtocol:
    """Erzeugt die Verschlüsselungsparameter des offiziellen ERiC-Wrappers."""
    lib_dir = Path(lib_dir).resolve()

    wrapper_dir = (
        lib_dir.parent
        / "Beispiel"
        / "ericdemo-python"
        / "ericdemo"
    )

    if not wrapper_dir.is_dir():
        raise EricSendError(
            "Der offizielle ERiC-Python-Wrapper wurde nicht gefunden: "
            f"{wrapper_dir}"
        )

    wrapper_path = str(wrapper_dir)
    inserted = False

    if wrapper_path not in sys.path:
        sys.path.insert(0, wrapper_path)
        inserted = True

    try:
        try:
            ericapi = importlib.import_module("ericapi")
        except ImportError as exc:
            raise EricSendError(
                "Der offizielle ERiC-Python-Wrapper konnte "
                "nicht importiert werden."
            ) from exc

        return ericapi.eric_verschluesselungs_parameter_t()
    finally:
        if inserted:
            sys.path.remove(wrapper_path)

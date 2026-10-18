"""ERiC-Adapter zur lokalen Validierung eines ELSTER-Datensatzes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from simpleob.eric.eric_create_th_adapter import (
    EricApiProtocol,
    _create_official_eric,
)

ERIC_OK = 0
ERIC_VALIDIERE = 1 << 1

DEFAULT_BILANZ_DATENART_VERSION = "Bilanz_6.9"


@dataclass(frozen=True)
class EricValidationResult:
    """Ergebnis einer erfolgreichen lokalen ERiC-Validierung."""

    response_xml: str


class EricValidateError(RuntimeError):
    """Fehler bei der lokalen Verarbeitung eines ELSTER-Datensatzes."""

    def __init__(
        self,
        message: str,
        *,
        error_code: int | None = None,
        error_text: str | None = None,
        response_xml: str | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.error_text = error_text
        self.response_xml = response_xml


class EricValidateApiProtocol(EricApiProtocol, Protocol):
    """Benötigter ERiC-Wrapper-Ausschnitt für die lokale Validierung."""

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
    EricValidateApiProtocol,
]


class EricValidateAdapter:
    """Validiert ein vollständiges ELSTER-XML lokal mit ERiC."""

    def __init__(
        self,
        *,
        lib_dir: Path,
        log_dir: Path | None = None,
        eric_factory: EricFactory | None = None,
    ) -> None:
        self._lib_dir = Path(lib_dir).expanduser()
        self._log_dir = Path(log_dir).expanduser() if log_dir else None

        self._eric_factory = eric_factory or cast(
            EricFactory,
            _create_official_eric,
        )

    def validate(
        self,
        *,
        elster_xml: str,
        datenart_version: str = DEFAULT_BILANZ_DATENART_VERSION,
    ) -> EricValidationResult:
        """Validiert einen vollständigen ELSTER-Datensatz lokal."""
        if not elster_xml.strip():
            raise ValueError(
                "Das zu validierende ELSTER-XML darf nicht leer sein."
            )

        datenart_version = datenart_version.strip()

        if not datenart_version:
            raise ValueError(
                "Die ERiC-DatenartVersion darf nicht leer sein."
            )

        eric = self._eric_factory(
            self._lib_dir,
            self._log_dir,
        )

        try:
            return self._validate_with_eric(
                eric=eric,
                elster_xml=elster_xml,
                datenart_version=datenart_version,
            )
        finally:
            self._close_eric(eric)

    def _validate_with_eric(
        self,
        *,
        eric: EricValidateApiProtocol,
        elster_xml: str,
        datenart_version: str,
    ) -> EricValidationResult:
        response_buffer = eric.PyEricRueckgabepufferErzeugen()

        if response_buffer is None:
            raise EricValidateError(
                "ERiC konnte keinen Rückgabepuffer für "
                "EricBearbeiteVorgang erzeugen."
            )

        try:
            result_code = eric.PyEricBearbeiteVorgang(
                datenpuffer=elster_xml,
                datenartVersion=datenart_version,
                bearbeitungsFlags=ERIC_VALIDIERE,
                druckParameter=None,
                cryptoParameter=None,
                rueckgabeXmlPuffer=response_buffer,
                serverantwortXmlPuffer=None,
            )

            response_bytes = eric.PyEricRueckgabepufferInhalt(
                response_buffer
            )

            response_xml = self._decode_response(
                response_bytes
            )

            if result_code != ERIC_OK:
                error_text = self._get_error_text(
                    eric=eric,
                    error_code=result_code,
                )

                raise EricValidateError(
                    "EricBearbeiteVorgang ist bei der lokalen "
                    "Validierung fehlgeschlagen "
                    f"(Fehler {result_code}): {error_text}",
                    error_code=result_code,
                    error_text=error_text,
                    response_xml=response_xml,
                )

            return EricValidationResult(
                response_xml=response_xml,
            )
        finally:
            eric.PyEricRueckgabepufferFreigeben(
                response_buffer
            )

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
        eric: EricValidateApiProtocol,
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
    def _close_eric(
        eric: EricValidateApiProtocol,
    ) -> None:
        result_code = eric.PyEricBeende()

        if result_code == ERIC_OK:
            # Der offizielle PyEric-Wrapper ruft PyEricBeende()
            # zusätzlich in __del__() auf. Nach unserem expliziten
            # Beenden verhindern wir deshalb einen zweiten Aufruf.
            eric._eric_initialized = False
            return

        raise EricValidateError(
            "ERiC konnte nicht ordnungsgemäß beendet werden "
            f"(Fehler {result_code}).",
            error_code=result_code,
        )

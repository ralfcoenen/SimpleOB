"""ERiC-Adapter zum Erzeugen des ELSTER-TransferHeaders."""

from __future__ import annotations

import importlib
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

ERIC_OK = 0

ELSTER_BILANZ_VERFAHREN = "ElsterBilanz"
ELSTER_BILANZ_DATENART = "Bilanz"
ELSTER_BILANZ_VORGANG = "send-Auth"


class EricCreateThError(RuntimeError):
    """Fehler beim Erzeugen des ELSTER-TransferHeaders mit ERiC."""


class EricApiProtocol(Protocol):
    """Benötigter Ausschnitt aus dem offiziellen ERiC-Python-Wrapper."""

    _eric_initialized: bool

    def PyEricRueckgabepufferErzeugen(self): ...

    def PyEricRueckgabepufferFreigeben(self, handle) -> int: ...

    def PyEricRueckgabepufferInhalt(self, handle) -> bytes: ...

    def PyEricCreateTH(
        self,
        xml,
        verfahren,
        datenart,
        vorgang,
        testmerker,
        herstellerId,
        datenLieferant,
        versionClient,
        publicKey,
        xmlRueckgabePuffer,
    ) -> int: ...

    def PyEricHoleFehlerText(
        self,
        fehlerkode,
        rueckgabePuffer,
    ) -> int: ...

    def PyEricBeende(self) -> int: ...


EricFactory = Callable[[Path, Path | None], EricApiProtocol]


class EricCreateThAdapter:
    """Erzeugt mit ERiC aus einem DatenTeil ein vollständiges ELSTER-XML."""

    def __init__(
        self,
        *,
        lib_dir: Path,
        log_dir: Path | None = None,
        eric_factory: EricFactory | None = None,
    ) -> None:
        self._lib_dir = Path(lib_dir).expanduser()
        self._log_dir = Path(log_dir).expanduser() if log_dir else None
        self._eric_factory = eric_factory or _create_official_eric

    def create(
        self,
        *,
        data_part_xml: str,
        manufacturer_id: str,
        version_client: str | None,
        data_supplier: str | None = None,
        test_marker: str | None = None,
    ) -> str:
        """Erzeugt das vollständige ELSTER-XML einschließlich TransferHeader."""
        manufacturer_id = manufacturer_id.strip()

        if not manufacturer_id:
            raise ValueError("Die ERiC-Hersteller-ID darf nicht leer sein.")

        eric = self._eric_factory(
            self._lib_dir,
            self._log_dir,
        )

        try:
            return self._create_with_eric(
                eric=eric,
                data_part_xml=data_part_xml,
                manufacturer_id=manufacturer_id,
                version_client=version_client,
                data_supplier=data_supplier,
                test_marker=test_marker,
            )
        finally:
            self._close_eric(eric)

    def _create_with_eric(
        self,
        *,
        eric: EricApiProtocol,
        data_part_xml: str,
        manufacturer_id: str,
        version_client: str | None,
        data_supplier: str | None,
        test_marker: str | None,
    ) -> str:
        output_buffer = eric.PyEricRueckgabepufferErzeugen()

        if output_buffer is None:
            raise EricCreateThError(
                "ERiC konnte keinen Rückgabepuffer für "
                "EricCreateTH erzeugen."
            )

        try:
            result_code = eric.PyEricCreateTH(
                xml=data_part_xml,
                verfahren=ELSTER_BILANZ_VERFAHREN,
                datenart=ELSTER_BILANZ_DATENART,
                vorgang=ELSTER_BILANZ_VORGANG,
                testmerker=test_marker,
                herstellerId=manufacturer_id,
                datenLieferant=data_supplier or "",
                versionClient=version_client,
                publicKey=None,
                xmlRueckgabePuffer=output_buffer,
            )

            if result_code != ERIC_OK:
                error_text = self._get_error_text(
                    eric=eric,
                    error_code=result_code,
                )
                raise EricCreateThError(
                    "EricCreateTH ist fehlgeschlagen "
                    f"(Fehler {result_code}): {error_text}"
                )

            xml_bytes = eric.PyEricRueckgabepufferInhalt(
                output_buffer
            )

            if not xml_bytes:
                raise EricCreateThError(
                    "EricCreateTH lieferte kein ELSTER-XML zurück."
                )

            try:
                return xml_bytes.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise EricCreateThError(
                    "Das von EricCreateTH erzeugte ELSTER-XML "
                    "ist nicht UTF-8-kodiert."
                ) from exc
        finally:
            eric.PyEricRueckgabepufferFreigeben(
                output_buffer
            )

    @staticmethod
    def _get_error_text(
        *,
        eric: EricApiProtocol,
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
    def _close_eric(eric: EricApiProtocol) -> None:
        result_code = eric.PyEricBeende()

        if result_code == ERIC_OK:
            # Der offizielle PyEric-Wrapper ruft PyEricBeende()
            # zusätzlich in __del__() auf. Nach unserem expliziten
            # Beenden verhindern wir deshalb einen zweiten Aufruf.
            eric._eric_initialized = False
            return

        raise EricCreateThError(
            "ERiC konnte nicht ordnungsgemäß beendet werden "
            f"(Fehler {result_code})."
        )


def _create_official_eric(
    lib_dir: Path,
    log_dir: Path | None,
) -> EricApiProtocol:
    """Lädt den mit dem ERiC-SDK gelieferten Python-Wrapper."""
    lib_dir = lib_dir.resolve()

    if not lib_dir.is_dir():
        raise EricCreateThError(
            f"Das konfigurierte ERiC-lib-Verzeichnis existiert nicht: "
            f"{lib_dir}"
        )

    wrapper_dir = (
        lib_dir.parent
        / "Beispiel"
        / "ericdemo-python"
        / "ericdemo"
    )

    if not wrapper_dir.is_dir():
        raise EricCreateThError(
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
            raise EricCreateThError(
                "Der offizielle ERiC-Python-Wrapper konnte "
                "nicht importiert werden."
            ) from exc

        try:
            return ericapi.PyEric(
                str(lib_dir),
                str(log_dir) if log_dir else None,
            )
        except Exception as exc:
            raise EricCreateThError(
                "ERiC konnte nicht initialisiert werden."
            ) from exc
    finally:
        if inserted:
            sys.path.remove(wrapper_path)

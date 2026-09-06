"""Tests für den ERiC-Adapter zur lokalen Validierung."""

from pathlib import Path

import pytest

from openbilanz.eric.eric_validate_adapter import (
    ERIC_VALIDIERE,
    EricValidateAdapter,
    EricValidateError,
)


class FakeEric:
    def __init__(
        self,
        *,
        validate_result: int = 0,
        response_xml: bytes = b"<EricBearbeiteVorgang />",
        error_text: bytes = b"",
        create_buffer: bool = True,
    ) -> None:
        self._eric_initialized = True

        self.validate_result = validate_result
        self.response_xml = response_xml
        self.error_text = error_text
        self.create_buffer = create_buffer

        self._next_handle = 1
        self._buffers: dict[int, bytes] = {}

        self.validate_call: dict[str, object] | None = None
        self.freed_handles: list[int] = []
        self.beende_calls = 0

    def PyEricRueckgabepufferErzeugen(self):
        if not self.create_buffer:
            return None

        handle = self._next_handle
        self._next_handle += 1
        self._buffers[handle] = b""
        return handle

    def PyEricRueckgabepufferFreigeben(
        self,
        handle,
    ) -> int:
        self.freed_handles.append(handle)
        self._buffers.pop(handle, None)
        return 0

    def PyEricRueckgabepufferInhalt(
        self,
        handle,
    ) -> bytes:
        return self._buffers.get(handle, b"")

    def PyEricBearbeiteVorgang(
        self,
        datenpuffer,
        datenartVersion,
        bearbeitungsFlags,
        druckParameter,
        cryptoParameter,
        rueckgabeXmlPuffer,
        serverantwortXmlPuffer,
    ) -> int:
        self.validate_call = {
            "datenpuffer": datenpuffer,
            "datenartVersion": datenartVersion,
            "bearbeitungsFlags": bearbeitungsFlags,
            "druckParameter": druckParameter,
            "cryptoParameter": cryptoParameter,
            "serverantwortXmlPuffer": serverantwortXmlPuffer,
        }

        self._buffers[rueckgabeXmlPuffer] = (
            self.response_xml
        )

        return self.validate_result

    def PyEricHoleFehlerText(
        self,
        fehlerkode,
        rueckgabePuffer,
    ) -> int:
        self._buffers[rueckgabePuffer] = self.error_text
        return 0

    def PyEricBeende(self) -> int:
        self.beende_calls += 1
        return 0


def test_validates_locally_with_bilanz_6_9_parameters() -> None:
    fake_eric = FakeEric(
        response_xml=b"<EricResponse>OK</EricResponse>",
    )

    def factory(
        lib_dir: Path,
        log_dir: Path | None,
    ) -> FakeEric:
        assert lib_dir == Path("/eric/lib")
        assert log_dir is None
        return fake_eric

    adapter = EricValidateAdapter(
        lib_dir=Path("/eric/lib"),
        eric_factory=factory,
    )

    result = adapter.validate(
        elster_xml="<Elster />",
    )

    assert result.response_xml == (
        "<EricResponse>OK</EricResponse>"
    )

    assert fake_eric.validate_call == {
        "datenpuffer": "<Elster />",
        "datenartVersion": "Bilanz_6.9",
        "bearbeitungsFlags": ERIC_VALIDIERE,
        "druckParameter": None,
        "cryptoParameter": None,
        "serverantwortXmlPuffer": None,
    }

    assert ERIC_VALIDIERE == 2
    assert fake_eric.freed_handles == [1]
    assert fake_eric.beende_calls == 1
    assert fake_eric._eric_initialized is False


def test_reports_eric_error_and_preserves_response_xml() -> None:
    fake_eric = FakeEric(
        validate_result=610001001,
        response_xml=(
            b"<EricResponse>"
            b"<Fehler>Validierungsfehler</Fehler>"
            b"</EricResponse>"
        ),
        error_text=b"Testfehler von ERiC",
    )

    adapter = EricValidateAdapter(
        lib_dir=Path("/eric/lib"),
        eric_factory=lambda _lib_dir, _log_dir: fake_eric,
    )

    with pytest.raises(
        EricValidateError,
        match="610001001.*Testfehler von ERiC",
    ) as exc_info:
        adapter.validate(
            elster_xml="<Elster />",
        )

    assert exc_info.value.error_code == 610001001
    assert exc_info.value.error_text == (
        "Testfehler von ERiC"
    )
    assert exc_info.value.response_xml == (
        "<EricResponse>"
        "<Fehler>Validierungsfehler</Fehler>"
        "</EricResponse>"
    )

    assert fake_eric.freed_handles == [2, 1]
    assert fake_eric.beende_calls == 1
    assert fake_eric._eric_initialized is False


def test_reports_missing_response_buffer_and_closes_eric() -> None:
    fake_eric = FakeEric(
        create_buffer=False,
    )

    adapter = EricValidateAdapter(
        lib_dir=Path("/eric/lib"),
        eric_factory=lambda _lib_dir, _log_dir: fake_eric,
    )

    with pytest.raises(
        EricValidateError,
        match="Rückgabepuffer",
    ):
        adapter.validate(
            elster_xml="<Elster />",
        )

    assert fake_eric.validate_call is None
    assert fake_eric.freed_handles == []
    assert fake_eric.beende_calls == 1
    assert fake_eric._eric_initialized is False

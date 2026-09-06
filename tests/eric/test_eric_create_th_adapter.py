"""Tests für den ERiC-Adapter zu EricCreateTH."""

from pathlib import Path

import pytest

from openbilanz.eric.eric_create_th_adapter import (
    EricCreateThAdapter,
    EricCreateThError,
)


class FakeEric:
    def __init__(
        self,
        *,
        create_th_result: int = 0,
        error_text: bytes = b"",
    ) -> None:
        self._eric_initialized = True
        self.create_th_result = create_th_result
        self.error_text = error_text

        self._next_handle = 1
        self._buffers: dict[int, bytes] = {}

        self.create_th_call: dict[str, object] | None = None
        self.freed_handles: list[int] = []
        self.beende_calls = 0

    def PyEricRueckgabepufferErzeugen(self):
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
    ) -> int:
        self.create_th_call = {
            "xml": xml,
            "verfahren": verfahren,
            "datenart": datenart,
            "vorgang": vorgang,
            "testmerker": testmerker,
            "herstellerId": herstellerId,
            "datenLieferant": datenLieferant,
            "versionClient": versionClient,
            "publicKey": publicKey,
        }

        if self.create_th_result == 0:
            self._buffers[xmlRueckgabePuffer] = (
                b'<?xml version="1.0" encoding="UTF-8"?>'
                b"<Elster><TransferHeader />"
                b"<DatenTeil /></Elster>"
            )

        return self.create_th_result

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


def test_creates_transfer_header_with_bilanz_parameters() -> None:
    fake_eric = FakeEric()

    def factory(
        lib_dir: Path,
        log_dir: Path | None,
    ) -> FakeEric:
        assert lib_dir == Path("/eric/lib")
        assert log_dir is None
        return fake_eric

    adapter = EricCreateThAdapter(
        lib_dir=Path("/eric/lib"),
        eric_factory=factory,
    )

    xml = adapter.create(
        data_part_xml="<DatenTeil />",
        manufacturer_id="12345",
        version_client="0.44.0",
    )

    assert xml.startswith('<?xml version="1.0"')

    assert fake_eric.create_th_call == {
        "xml": "<DatenTeil />",
        "verfahren": "ElsterBilanz",
        "datenart": "Bilanz",
        "vorgang": "send-Auth",
        "testmerker": None,
        "herstellerId": "12345",
        "datenLieferant": "",
        "versionClient": "0.44.0",
        "publicKey": None,
    }

    assert fake_eric.freed_handles == [1]
    assert fake_eric.beende_calls == 1
    assert fake_eric._eric_initialized is False


def test_passes_optional_transfer_header_values() -> None:
    fake_eric = FakeEric()

    adapter = EricCreateThAdapter(
        lib_dir=Path("/eric/lib"),
        eric_factory=lambda _lib_dir, _log_dir: fake_eric,
    )

    adapter.create(
        data_part_xml="<DatenTeil />",
        manufacturer_id="12345",
        version_client="0.44.0",
        data_supplier="Max Mustermann",
        test_marker="700000004",
    )

    assert fake_eric.create_th_call is not None
    assert fake_eric.create_th_call["datenLieferant"] == (
        "Max Mustermann"
    )
    assert fake_eric.create_th_call["testmerker"] == "700000004"


def test_reports_eric_create_th_error_and_frees_buffers() -> None:
    fake_eric = FakeEric(
        create_th_result=610001001,
        error_text=b"Testfehler von ERiC",
    )

    adapter = EricCreateThAdapter(
        lib_dir=Path("/eric/lib"),
        eric_factory=lambda _lib_dir, _log_dir: fake_eric,
    )

    with pytest.raises(
        EricCreateThError,
        match="610001001.*Testfehler von ERiC",
    ):
        adapter.create(
            data_part_xml="<DatenTeil />",
            manufacturer_id="12345",
            version_client="0.44.0",
        )

    assert fake_eric.freed_handles == [2, 1]
    assert fake_eric.beende_calls == 1
    assert fake_eric._eric_initialized is False


def test_rejects_empty_manufacturer_id_before_eric_is_started() -> None:
    factory_called = False

    def factory(
        _lib_dir: Path,
        _log_dir: Path | None,
    ) -> FakeEric:
        nonlocal factory_called
        factory_called = True
        return FakeEric()

    adapter = EricCreateThAdapter(
        lib_dir=Path("/eric/lib"),
        eric_factory=factory,
    )

    with pytest.raises(
        ValueError,
        match="Hersteller-ID",
    ):
        adapter.create(
            data_part_xml="<DatenTeil />",
            manufacturer_id="   ",
            version_client="0.44.0",
        )

    assert factory_called is False

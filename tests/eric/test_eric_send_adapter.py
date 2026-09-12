from pathlib import Path

from openbilanz.eric.eric_send_adapter import (
    ERIC_SEND_FLAGS,
    ERIC_SENDE,
    ERIC_VALIDIERE,
    EricSendAdapter,
)


class FakeCryptoParameter:
    def __init__(self) -> None:
        self.version = 0
        self.zertifikatHandle = 0
        self.pin = None


class FakeEric:
    def __init__(self) -> None:
        self._eric_initialized = True
        self._buffers: dict[int, bytes] = {}
        self._next_buffer = 1

        self.certificate_path = None
        self.closed_certificate_handle = None
        self.send_call = None
        self.beende_called = False

    def PyEricRueckgabepufferErzeugen(self):
        handle = self._next_buffer
        self._next_buffer += 1
        self._buffers[handle] = b""
        return handle

    def PyEricRueckgabepufferFreigeben(self, handle) -> int:
        self._buffers.pop(handle, None)
        return 0

    def PyEricRueckgabepufferInhalt(self, handle) -> bytes:
        return self._buffers.get(handle, b"")

    def PyEricHoleFehlerText(
        self,
        fehlerkode,
        rueckgabePuffer,
    ) -> int:
        self._buffers[rueckgabePuffer] = b"Fake error"
        return 0

    def PyEricGetHandleToCertificate(
        self,
        pathToKeystore,
    ):
        self.certificate_path = pathToKeystore
        return 0, 4711, 0

    def PyEricCloseHandleToCertificate(
        self,
        hToken,
    ) -> int:
        self.closed_certificate_handle = hToken
        return 0

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
        self.send_call = {
            "datenpuffer": datenpuffer,
            "datenartVersion": datenartVersion,
            "bearbeitungsFlags": bearbeitungsFlags,
            "druckParameter": druckParameter,
            "cryptoParameter": cryptoParameter,
            "rueckgabeXmlPuffer": rueckgabeXmlPuffer,
            "serverantwortXmlPuffer": serverantwortXmlPuffer,
        }

        self._buffers[rueckgabeXmlPuffer] = (
            b"<EricBearbeiteVorgang><Erfolg/>"
            b"</EricBearbeiteVorgang>"
        )
        self._buffers[serverantwortXmlPuffer] = (
            b"<Serverantwort>OK</Serverantwort>"
        )

        return 0

    def PyEricBeende(self) -> int:
        self.beende_called = True
        return 0


def test_send_uses_official_send_flags_and_certificate(
    tmp_path: Path,
) -> None:
    certificate_path = tmp_path / "test.pfx"
    certificate_path.write_bytes(b"fake")

    fake_eric = FakeEric()
    crypto_parameter = FakeCryptoParameter()

    adapter = EricSendAdapter(
        lib_dir=tmp_path,
        eric_factory=lambda lib_dir, log_dir: fake_eric,
        crypto_parameter_factory=lambda lib_dir: crypto_parameter,
    )

    result = adapter.send(
        elster_xml="<Elster />",
        certificate_path=certificate_path,
        certificate_pin="123456",
    )

    assert ERIC_VALIDIERE == 2
    assert ERIC_SENDE == 4
    assert ERIC_SEND_FLAGS == 6

    assert fake_eric.certificate_path == str(certificate_path)

    assert crypto_parameter.version == 3
    assert crypto_parameter.zertifikatHandle == 4711
    assert crypto_parameter.pin == "123456"

    assert fake_eric.send_call is not None
    assert fake_eric.send_call["datenpuffer"] == "<Elster />"
    assert (
        fake_eric.send_call["datenartVersion"]
        == "Bilanz_6.9"
    )
    assert fake_eric.send_call["bearbeitungsFlags"] == 6
    assert fake_eric.send_call["druckParameter"] is None
    assert (
        fake_eric.send_call["cryptoParameter"]
        is crypto_parameter
    )
    assert (
        fake_eric.send_call["serverantwortXmlPuffer"]
        is not None
    )

    assert result.response_xml == (
        "<EricBearbeiteVorgang><Erfolg/>"
        "</EricBearbeiteVorgang>"
    )
    assert result.server_response_xml == (
        "<Serverantwort>OK</Serverantwort>"
    )

    assert fake_eric.closed_certificate_handle == 4711
    assert fake_eric.beende_called is True
    assert fake_eric._eric_initialized is False

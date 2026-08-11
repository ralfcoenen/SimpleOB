"""Smoke-Test für die direkte Arelle-Python-API."""

from pathlib import Path

import pytest
from arelle import Cntlr


ENTRY_POINT = Path(
    "/tmp/openbilanz-taxonomy/6.8/"
    "german-gaap-taxonomy-v6.8-2024-04-01/"
    "xbrl/"
    "de-gaap-ci-2024-04-01/"
    "de-gaap-ci-2024-04-01-shell-fiscal.xsd"
)


def test_arelle_loads_taxonomy() -> None:
    """Arelle lädt die deutsche E-Bilanz-Taxonomie 6.8."""

    if not ENTRY_POINT.is_file():
        pytest.skip(
            "German GAAP taxonomy 6.8 is not installed locally"
        )

    controller = Cntlr.Cntlr()

    try:
        model_xbrl = controller.modelManager.load(
            str(ENTRY_POINT)
        )

        assert model_xbrl is not None

        print()
        print("MODEL GELADEN:")
        print(model_xbrl.modelDocument.uri)

        print()
        print("CONCEPTS:")
        print(len(model_xbrl.qnameConcepts))

        print()
        print("NAMESPACES:")

        namespaces = sorted(
            {
                str(qname.namespaceURI)
                for qname in model_xbrl.qnameConcepts
                if qname.namespaceURI
            }
        )

        for namespace in namespaces:
            print(namespace)

        model_xbrl.close()

    finally:
        controller.close()


"""Smoke-Test für die direkte Arelle-Python-API."""


from arelle import Cntlr

from tests.taxonomy_resources import taxonomy_entry_point


def test_arelle_loads_taxonomy() -> None:
    """Arelle lädt die deutsche E-Bilanz-Taxonomie 6.8."""
    ENTRY_POINT = taxonomy_entry_point("6.8", kind="gaap-ci")


    controller = Cntlr.Cntlr()
    controller.webCache.workOffline = True

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


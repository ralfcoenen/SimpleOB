"""Tests für fiskalische GAAP-CI-Anforderungsreferenzen."""

from pathlib import Path

from openbilanz.taxonomy.entry_point import (
    TaxonomyEntryPoint,
)
from openbilanz.taxonomy.fiscal_requirement_reader import (
    FiscalConceptRequirement,
    FiscalRequirement,
    FiscalRequirementReader,
)


def test_reads_corporation_requirements_through_import_chain(
    tmp_path: Path,
) -> None:
    """KSt-Anforderungen werden über die Fiscal-Shell gefunden."""

    fiscal_shell = (
        tmp_path
        / "de-gaap-ci-2025-04-01-shell-fiscal.xsd"
    )

    standard_shell = (
        tmp_path
        / "de-gaap-ci-2025-04-01-shell.xsd"
    )

    base_schema = (
        tmp_path
        / "de-gaap-ci-2025-04-01.xsd"
    )

    reference_linkbase = (
        tmp_path
        / "de-gaap-ci-2025-04-01-reference-fiscal.xml"
    )

    fiscal_shell.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<xs:schema
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    targetNamespace="http://www.xbrl.de/taxonomies/de-gaap-ci-2025-04-01/shell-fiscal">

    <xs:import
        namespace="http://www.xbrl.de/taxonomies/de-gaap-ci-2025-04-01/shell"
        schemaLocation="de-gaap-ci-2025-04-01-shell.xsd"/>

</xs:schema>
""",
        encoding="utf-8",
    )

    standard_shell.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<xs:schema
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    targetNamespace="http://www.xbrl.de/taxonomies/de-gaap-ci-2025-04-01/shell">

    <xs:import
        namespace="http://www.xbrl.de/taxonomies/de-gaap-ci-2025-04-01"
        schemaLocation="de-gaap-ci-2025-04-01.xsd"/>

</xs:schema>
""",
        encoding="utf-8",
    )

    base_schema.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<xs:schema
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:link="http://www.xbrl.org/2003/linkbase"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    targetNamespace="http://www.xbrl.de/taxonomies/de-gaap-ci-2025-04-01">

    <xs:annotation>
        <xs:appinfo>
            <link:linkbaseRef
                xlink:type="simple"
                xlink:href="de-gaap-ci-2025-04-01-reference-fiscal.xml"
                xlink:role="http://www.xbrl.org/2003/role/referenceLinkbaseRef"/>
        </xs:appinfo>
    </xs:annotation>

</xs:schema>
""",
        encoding="utf-8",
    )

    reference_linkbase.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<link:linkbase
    xmlns:hgbref="http://www.xbrl.de/taxonomies/de-ref-2010-02-19"
    xmlns:link="http://www.xbrl.org/2003/linkbase"
    xmlns:xlink="http://www.w3.org/1999/xlink">

    <link:referenceLink
        xlink:type="extended"
        xlink:role="http://www.xbrl.org/2003/role/link">

        <link:loc
            xlink:type="locator"
            xlink:href="de-gaap-ci-2025-04-01.xsd#de-gaap-ci_bs.ass"
            xlink:label="de-gaap-ci_bs.ass"/>

        <link:referenceArc
            xlink:type="arc"
            xlink:arcrole="http://www.xbrl.org/2003/arcrole/concept-reference"
            xlink:from="de-gaap-ci_bs.ass"
            xlink:to="reference_de-gaap-ci_bs.ass"/>

        <link:reference
            xlink:type="resource"
            xlink:label="reference_de-gaap-ci_bs.ass"
            xlink:role="http://www.xbrl.org/2003/role/mandatoryDisclosureRef">

            <hgbref:legalFormKSt>true</hgbref:legalFormKSt>
            <hgbref:fiscalRequirement>Summenmussfeld</hgbref:fiscalRequirement>

        </link:reference>

        <link:loc
            xlink:type="locator"
            xlink:href="de-gaap-ci-2025-04-01.xsd#de-gaap-ci_bs.ass.fixAss.intan.concessionBrands"
            xlink:label="de-gaap-ci_bs.ass.fixAss.intan.concessionBrands"/>

        <link:referenceArc
            xlink:type="arc"
            xlink:arcrole="http://www.xbrl.org/2003/arcrole/concept-reference"
            xlink:from="de-gaap-ci_bs.ass.fixAss.intan.concessionBrands"
            xlink:to="reference_de-gaap-ci_bs.ass.fixAss.intan.concessionBrands"/>

        <link:reference
            xlink:type="resource"
            xlink:label="reference_de-gaap-ci_bs.ass.fixAss.intan.concessionBrands"
            xlink:role="http://www.xbrl.org/2003/role/mandatoryDisclosureRef">

            <hgbref:legalFormEU>true</hgbref:legalFormEU>
            <hgbref:legalFormKSt>true</hgbref:legalFormKSt>
            <hgbref:fiscalRequirement>Mussfeld</hgbref:fiscalRequirement>

        </link:reference>

        <link:loc
            xlink:type="locator"
            xlink:href="de-gaap-ci-2025-04-01.xsd#de-gaap-ci_bs.ass.accountingConvenience"
            xlink:label="de-gaap-ci_bs.ass.accountingConvenience"/>

        <link:referenceArc
            xlink:type="arc"
            xlink:arcrole="http://www.xbrl.org/2003/arcrole/concept-reference"
            xlink:from="de-gaap-ci_bs.ass.accountingConvenience"
            xlink:to="reference_de-gaap-ci_bs.ass.accountingConvenience"/>

        <link:reference
            xlink:type="resource"
            xlink:label="reference_de-gaap-ci_bs.ass.accountingConvenience"
            xlink:role="http://www.xbrl.org/2003/role/mandatoryDisclosureRef">

            <hgbref:legalFormKSt>true</hgbref:legalFormKSt>
            <hgbref:notPermittedFor>steuerlich</hgbref:notPermittedFor>
            <hgbref:fiscalRequirement>Rechnerisch notwendig, soweit vorhanden</hgbref:fiscalRequirement>

        </link:reference>

        <link:loc
            xlink:type="locator"
            xlink:href="de-gaap-ci-2025-04-01.xsd#de-gaap-ci_bs.exampleOnlyEU"
            xlink:label="de-gaap-ci_bs.exampleOnlyEU"/>

        <link:referenceArc
            xlink:type="arc"
            xlink:arcrole="http://www.xbrl.org/2003/arcrole/concept-reference"
            xlink:from="de-gaap-ci_bs.exampleOnlyEU"
            xlink:to="reference_de-gaap-ci_bs.exampleOnlyEU"/>

        <link:reference
            xlink:type="resource"
            xlink:label="reference_de-gaap-ci_bs.exampleOnlyEU"
            xlink:role="http://www.xbrl.org/2003/role/mandatoryDisclosureRef">

            <hgbref:legalFormEU>true</hgbref:legalFormEU>
            <hgbref:fiscalRequirement>Mussfeld</hgbref:fiscalRequirement>

        </link:reference>

    </link:referenceLink>

</link:linkbase>
""",
        encoding="utf-8",
    )

    entry_point = TaxonomyEntryPoint.from_file(
        fiscal_shell
    )

    reader = FiscalRequirementReader(
        entry_point
    )

    assert reader.corporation_requirements() == (
        FiscalConceptRequirement(
            concept_name="bs.ass",
            requirement=FiscalRequirement.SUM_REQUIRED,
            legal_form_kst=True,
        ),
        FiscalConceptRequirement(
            concept_name="bs.ass.accountingConvenience",
            requirement=FiscalRequirement.CALCULATION_IF_PRESENT,
            legal_form_kst=True,
            not_permitted_for="steuerlich",
        ),
        FiscalConceptRequirement(
            concept_name=(
                "bs.ass.fixAss.intan.concessionBrands"
            ),
            requirement=FiscalRequirement.REQUIRED,
            legal_form_kst=True,
        ),
    )

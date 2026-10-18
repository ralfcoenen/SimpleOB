"""Export von Taxonomiedaten als XBRL-Instanz."""

from simpleob.taxonomy.account_balance_tuple import (
    TaxonomyAccountBalance,
)
from simpleob.taxonomy.context import TaxonomyContext
from simpleob.taxonomy.entry_point import TaxonomyEntryPoint
from simpleob.taxonomy.fact import TaxonomyFact
from simpleob.taxonomy.gcd_company_id_no import (
    GcdCompanyIdNo,
)
from simpleob.taxonomy.gcd_domestic_branch_of_foreign_company import (
    GcdDomesticBranchOfForeignCompany,
)
from simpleob.taxonomy.gcd_entity_with_taxable_purpose_business import (
    GcdEntityWithTaxablePurposeBusiness,
)
from simpleob.taxonomy.gcd_report_element import (
    GcdReportElement,
)
from simpleob.taxonomy.gcd_shareholder_tuple import (
    GcdShareholderTuple,
)
from simpleob.taxonomy.nil_fact import TaxonomyNilFact
from simpleob.taxonomy.text_fact import TaxonomyTextFact
from simpleob.taxonomy.unit import TaxonomyUnit
from simpleob.taxonomy.xbrl_writer import TaxonomyXbrlWriter


class XbrlExporter:
    """Erzeugt vollständige XBRL-Instanzen."""

    def __init__(self) -> None:
        self._writer = TaxonomyXbrlWriter()

    def export(
        self,
        *,
        contexts: dict[str, TaxonomyContext],
        units: dict[str, TaxonomyUnit],
        facts: tuple[
            TaxonomyFact | TaxonomyTextFact,
            ...,
        ],
        taxonomy_namespace: str,
        nil_facts: tuple[
            TaxonomyNilFact,
            ...,
        ] = (),
        entry_points: tuple[TaxonomyEntryPoint, ...],
        taxonomy_namespaces: dict[str, str] | None = None,
        report_elements: tuple[GcdReportElement, ...] = (),
        company_id_nos: tuple[GcdCompanyIdNo, ...] = (),
        domestic_branches: tuple[
            GcdDomesticBranchOfForeignCompany,
            ...,
        ] = (),
        taxable_purpose_businesses: tuple[
            GcdEntityWithTaxablePurposeBusiness,
            ...,
        ] = (),
        shareholders: tuple[GcdShareholderTuple, ...] = (),
        account_balances: tuple[
            TaxonomyAccountBalance,
            ...
        ] = (),
    ) -> str:
        """Erzeugt eine XBRL-Instanz als XML-String."""

        root = self._writer.instance_element(
            contexts=contexts,
            units=units,
            facts=facts,
            nil_facts=nil_facts,
            taxonomy_namespace=taxonomy_namespace,
            taxonomy_namespaces=taxonomy_namespaces,
            entry_points=entry_points,
            report_elements=report_elements,
            company_id_nos=company_id_nos,
            shareholders=shareholders,
            domestic_branches=domestic_branches,
            taxable_purpose_businesses=taxable_purpose_businesses,
            account_balances=account_balances,
        )

        return self._writer.to_xml_string(
            root=root
        )

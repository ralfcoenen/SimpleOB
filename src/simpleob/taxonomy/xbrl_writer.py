"""Serialisierung taxonomischer Daten als XBRL."""

from xml.etree import ElementTree as ET

from simpleob.taxonomy.account_balance_tuple import (
    TaxonomyAccountBalance,
)
from simpleob.taxonomy.concept import TaxonomyPeriodType
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

XBRLI_NAMESPACE = "http://www.xbrl.org/2003/instance"
XBRLDI_NAMESPACE = "http://xbrl.org/2006/xbrldi"
ISO4217_NAMESPACE = "http://www.xbrl.org/2003/iso4217"
LINK_NAMESPACE = "http://www.xbrl.org/2003/linkbase"
XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"

class TaxonomyXbrlWriter:
    """Serialisiert Taxonomie-Objekte als XBRL-Elemente."""

    def namespace_for(
        self,
        *,
        concept_id: str,
        taxonomy_namespace: str,
        taxonomy_namespaces: dict[str, str] | None,
    ) -> str:
        """Ermittelt den Namespace eines Taxonomie-Concepts."""

        if taxonomy_namespaces is None:
            return taxonomy_namespace

        taxonomy_prefix = concept_id.split(
            "_",
            1,
        )[0]

        namespace = taxonomy_namespaces.get(
            taxonomy_prefix
        )

        if namespace is None:
            return taxonomy_namespace

        return namespace

    def context_element(
        self,
        context: TaxonomyContext,
        context_id: str,
    ) -> ET.Element:
        """Erzeugt ein XBRL-Context-Element."""

        element = ET.Element(
            f"{{{XBRLI_NAMESPACE}}}context",
            {
                "id": context_id,
            },
        )

        entity = ET.SubElement(
            element,
            f"{{{XBRLI_NAMESPACE}}}entity",
        )

        identifier = ET.SubElement(
            entity,
            f"{{{XBRLI_NAMESPACE}}}identifier",
            {
                "scheme": context.entity_scheme,
            },
        )
        identifier.text = context.entity_identifier

        period = ET.SubElement(
            element,
            f"{{{XBRLI_NAMESPACE}}}period",
        )

        if context.period_type is TaxonomyPeriodType.INSTANT:
            instant = ET.SubElement(
                period,
                f"{{{XBRLI_NAMESPACE}}}instant",
            )
            instant.text = context.end_date.isoformat()

        else:
            start_date = ET.SubElement(
                period,
                f"{{{XBRLI_NAMESPACE}}}startDate",
            )
            start_date.text = context.start_date.isoformat()

            end_date = ET.SubElement(
                period,
                f"{{{XBRLI_NAMESPACE}}}endDate",
            )
            end_date.text = context.end_date.isoformat()

        if context.dimensions:
            scenario = ET.SubElement(
                element,
                f"{{{XBRLI_NAMESPACE}}}scenario",
            )

            for dimension in context.dimensions:
                explicit_member = ET.SubElement(
                    scenario,
                    f"{{{XBRLDI_NAMESPACE}}}explicitMember",
                    {
                        "dimension": dimension.dimension_name,
                    },
                )
                explicit_member.text = dimension.member_name

        return element

    def unit_element(
        self,
        unit: TaxonomyUnit,
        unit_id: str,
    ) -> ET.Element:
        """Erzeugt ein XBRL-Unit-Element."""

        element = ET.Element(
            f"{{{XBRLI_NAMESPACE}}}unit",
            {
                "id": unit_id,
            },
        )

        measure = ET.SubElement(
            element,
            f"{{{XBRLI_NAMESPACE}}}measure",
        )
        measure.text = unit.measure

        return element

    def fact_element(
        self,
        *,
        fact: TaxonomyFact,
        context_id: str,
        unit_id: str,
        namespace: str,
    ) -> ET.Element:
        """Erzeugt ein numerisches XBRL-Fact-Element."""

        if not isinstance(
            fact,
            TaxonomyFact,
        ):
            raise TypeError(
                "fact must be a TaxonomyFact"
            )

        element = ET.Element(
            f"{{{namespace}}}{fact.concept.name}",
            {
                "contextRef": context_id,
                "unitRef": unit_id,
                "decimals": str(fact.decimals),
            },
        )

        element.text = str(fact.amount)

        return element

    def nil_fact_element(
        self,
        *,
        fact: TaxonomyNilFact,
        context_id: str,
        unit_id: str | None,
        namespace: str,
    ) -> ET.Element:
        """Erzeugt ein XBRL-NIL-Fact-Element."""

        if not isinstance(
            fact,
            TaxonomyNilFact,
        ):
            raise TypeError(
                "fact must be a TaxonomyNilFact"
            )

        attributes = {
            "contextRef": context_id,
            f"{{{XSI_NAMESPACE}}}nil": "true",
        }

        if unit_id is not None:
            attributes["unitRef"] = unit_id

        return ET.Element(
            f"{{{namespace}}}{fact.concept.name}",
            attributes,
        )

    def gcd_report_id_tuple_element(
        self,
        *,
        fact: TaxonomyTextFact,
        context_id: str,
        namespace: str,
        tuple_name: str,
    ) -> ET.Element:
        """Erzeugt ein GCD-Report-ID-Tuple mit einem Text-Fact."""

        if not isinstance(
            fact,
            TaxonomyTextFact,
        ):
            raise TypeError(
                "fact must be a TaxonomyTextFact"
            )

        element = ET.Element(
            f"{{{namespace}}}{tuple_name}"
        )

        element.append(
            self.text_fact_element(
                fact=fact,
                context_id=context_id,
                namespace=namespace,
            )
        )

        return element

    def gcd_report_element_element(
        self,
        *,
        report_element: GcdReportElement,
        context_id: str,
        namespace: str,
    ) -> ET.Element:
        """Erzeugt das GCD-Report-Element als XBRL-Tuple."""

        if not isinstance(
            report_element,
            GcdReportElement,
        ):
            raise TypeError(
                "report_element must be a GcdReportElement"
            )

        element = ET.Element(
            f"{{{namespace}}}"
            "genInfo.report.id.reportElement"
        )

        for fact in report_element.facts:
            element.append(
                self.text_fact_element(
                    fact=fact,
                    context_id=context_id,
                    namespace=namespace,
                )
            )

        return element

    def account_balance_element(
        self,
        *,
        account_balance: TaxonomyAccountBalance,
        context_id: str,
        unit_id: str,
        namespace: str,
    ) -> ET.Element:
        """Erzeugt einen GAAP-CI-Kontennachweis als XBRL-Tuple."""

        if not isinstance(
            account_balance,
            TaxonomyAccountBalance,
        ):
            raise TypeError(
                "account_balance must be a "
                "TaxonomyAccountBalance"
            )

        element = ET.Element(
            f"{{{namespace}}}"
            "detailedInformation.accountBalances"
        )

        for fact in (
            account_balance.position_name,
            account_balance.account_number,
            account_balance.account_description,
        ):
            element.append(
                self.text_fact_element(
                    fact=fact,
                    context_id=context_id,
                    namespace=namespace,
                )
            )

        element.append(
            self.fact_element(
                fact=account_balance.amount,
                context_id=context_id,
                unit_id=unit_id,
                namespace=namespace,
            )
        )

        if account_balance.not_possible is not None:
            element.append(
                self.text_fact_element(
                    fact=account_balance.not_possible,
                    context_id=context_id,
                    namespace=namespace,
                )
            )

        return element

    def gcd_company_id_no_element(
        self,
        *,
        company_id_no: GcdCompanyIdNo,
        context_id: str,
        namespace: str,
    ) -> ET.Element:
        """Erzeugt das GCD-idNo-Element als XBRL-Tuple."""

        if not isinstance(
            company_id_no,
            GcdCompanyIdNo,
        ):
            raise TypeError(
                "company_id_no must be a GcdCompanyIdNo"
            )

        element = ET.Element(
            f"{{{namespace}}}"
            "genInfo.company.id.idNo"
        )

        for fact in company_id_no.facts:
            element.append(
                self.text_fact_element(
                    fact=fact,
                    context_id=context_id,
                    namespace=namespace,
                )
            )

        return element

    def gcd_domestic_branch_of_foreign_company_element(
        self,
        *,
        branch: GcdDomesticBranchOfForeignCompany,
        context_id: str,
        namespace: str,
    ) -> ET.Element:
        """Erzeugt das GCD-Tuple für eine inländische Zweigniederlassung."""

        if not isinstance(
            branch,
            GcdDomesticBranchOfForeignCompany,
        ):
            raise TypeError(
                "branch must be a "
                "GcdDomesticBranchOfForeignCompany"
            )

        element = ET.Element(
            f"{{{namespace}}}"
            "genInfo.company.id.domesticBranchOfForeignCompany"
        )

        element.append(
            self.text_fact_element(
                fact=branch.fact,
                context_id=context_id,
                namespace=namespace,
            )
        )

        return element

    def gcd_entity_with_taxable_purpose_business_element(
        self,
        *,
        business: GcdEntityWithTaxablePurposeBusiness,
        context_id: str,
        namespace: str,
    ) -> ET.Element:
        """Erzeugt das GCD-Tuple für den steuerpflichtigen Betrieb."""

        if not isinstance(
            business,
            GcdEntityWithTaxablePurposeBusiness,
        ):
            raise TypeError(
                "business must be a "
                "GcdEntityWithTaxablePurposeBusiness"
            )

        element = ET.Element(
            f"{{{namespace}}}"
            "genInfo.company.id.entityWithTaxablePurposeBusiness"
        )

        element.append(
            self.text_fact_element(
                fact=business.fact,
                context_id=context_id,
                namespace=namespace,
            )
        )

        return element

    def gcd_shareholder_element(
        self,
        *,
        shareholder: GcdShareholderTuple,
        context_id: str,
        namespace: str,
        pure_unit_id: str | None = None,
    ) -> ET.Element:
        """Erzeugt ein verschachteltes GCD-Gesellschafter-Tuple."""

        if not isinstance(
            shareholder,
            GcdShareholderTuple,
        ):
            raise TypeError(
                "shareholder must be a GcdShareholderTuple"
            )

        element = ET.Element(
            f"{{{namespace}}}"
            "genInfo.company.id.shareholder"
        )

        def append_text_fact(
            parent: ET.Element,
            fact: TaxonomyTextFact | TaxonomyNilFact | None,
        ) -> None:
            if fact is None:
                return

            if isinstance(
                fact,
                TaxonomyNilFact,
            ):
                parent.append(
                    self.nil_fact_element(
                        fact=fact,
                        context_id=context_id,
                        unit_id=None,
                        namespace=namespace,
                    )
                )
                return

            parent.append(
                self.text_fact_element(
                    fact=fact,
                    context_id=context_id,
                    namespace=namespace,
                )
            )
        append_text_fact(
            element,
            shareholder.name,
        )
        append_text_fact(
            element,
            shareholder.first_name,
        )
        append_text_fact(
            element,
            shareholder.shareholder_id,
        )

        if shareholder.group is not None:
            group_element = ET.Element(
                f"{{{namespace}}}"
                "genInfo.company.id.shareholder.group"
            )

            append_text_fact(
                group_element,
                shareholder.group,
            )

            element.append(
                group_element
            )

        if shareholder.current_number is not None:
            if pure_unit_id is None:
                raise ValueError(
                    "pure_unit_id is required for current_number"
                )

            element.append(
                self.fact_element(
                    fact=shareholder.current_number,
                    context_id=context_id,
                    unit_id=pure_unit_id,
                    namespace=namespace,
                )
            )

        append_text_fact(
            element,
            shareholder.signer_id,
        )
        append_text_fact(
            element,
            shareholder.tax_number,
        )
        append_text_fact(
            element,
            shareholder.tax_id,
        )
        append_text_fact(
            element,
            shareholder.wid,
        )
        append_text_fact(
            element,
            shareholder.id_not_assigned,
        )
        append_text_fact(
            element,
            shareholder.economic_id,
        )

        legal_status_element = ET.Element(
            f"{{{namespace}}}"
            "genInfo.company.id.shareholder.legalStatus"
        )

        append_text_fact(
            legal_status_element,
            shareholder.legal_status.fact,
        )

        element.append(
            legal_status_element
        )

        share_divide_key_element = ET.Element(
            f"{{{namespace}}}"
            "genInfo.company.id.shareholder.ShareDivideKey"
        )

        append_text_fact(
            share_divide_key_element,
            shareholder.share_divide_key.numerator,
        )
        append_text_fact(
            share_divide_key_element,
            shareholder.share_divide_key.denominator,
        )

        element.append(
            share_divide_key_element
        )

        append_text_fact(
            element,
            shareholder.special_balance_required,
        )
        append_text_fact(
            element,
            shareholder.extension_required,
        )

        return element

    def instance_element(
        self,
        *,
        contexts: dict[str, TaxonomyContext],
        units: dict[str, TaxonomyUnit],
        facts: tuple[
            TaxonomyFact | TaxonomyTextFact,
            ...,
        ],
        taxonomy_namespace: str,
        entry_points: tuple[TaxonomyEntryPoint, ...],
        taxonomy_namespaces: dict[str, str] | None = None,
        nil_facts: tuple[
            TaxonomyNilFact,
            ...,
        ] = (),
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
            ...,
        ] = (),
    ) -> ET.Element:
        """Erzeugt das Root-Element einer XBRL-Instanz."""

        if taxonomy_namespaces is not None:
            for prefix, namespace in taxonomy_namespaces.items():
                ET.register_namespace(
                    prefix,
                    namespace,
                )

        root = ET.Element(
            f"{{{XBRLI_NAMESPACE}}}xbrl"
        )

        for entry_point in entry_points:
            root.append(
                self.schema_ref_element(
                    entry_point=entry_point,
                )
            )

        for context_id, context in contexts.items():
            root.append(
                self.context_element(
                    context=context,
                    context_id=context_id,
                )
            )

        for unit_id, unit in units.items():
            root.append(
                self.unit_element(
                    unit=unit,
                    unit_id=unit_id,
                )
            )

        for fact in facts:
            context_id = self.context_id_for(
                context=fact.context,
                contexts=contexts,
            )

            namespace = self.namespace_for(
                concept_id=fact.concept.concept_id,
                taxonomy_namespace=taxonomy_namespace,
                taxonomy_namespaces=taxonomy_namespaces,
            )

            if isinstance(
                fact,
                TaxonomyNilFact,
            ):
                unit_id = None

                if fact.unit is not None:
                    unit_id = self.unit_id_for(
                        unit=fact.unit,
                        units=units,
                    )

                root.append(
                    self.nil_fact_element(
                        fact=fact,
                        context_id=context_id,
                        unit_id=unit_id,
                        namespace=namespace,
                    )
                )
                continue

            if isinstance(
                fact,
                TaxonomyTextFact,
            ):
                gcd_report_id_tuple_names = (
                    "accountingStandard",
                    "statementType",
                    "reportStatus",
                    "revisionStatus",
                    "incomeStatementFormat",
                    "consolidationRange",
                )

                tuple_created = False

                for tuple_name in gcd_report_id_tuple_names:
                    if fact.concept.name.startswith(
                        f"genInfo.report.id.{tuple_name}."
                        f"{tuple_name}."
                    ):
                        root.append(
                            self.gcd_report_id_tuple_element(
                                fact=fact,
                                context_id=context_id,
                                namespace=namespace,
                                tuple_name=(
                                    f"genInfo.report.id.{tuple_name}"
                                ),
                            )
                        )
                        tuple_created = True
                        break

                if (
                    not tuple_created
                    and fact.concept.name.startswith(
                        "genInfo.report.id."
                        "specialAccountingStandard."
                    )
                ):
                    root.append(
                        self.gcd_report_id_tuple_element(
                            fact=fact,
                            context_id=context_id,
                            namespace=namespace,
                            tuple_name=(
                                "genInfo.report.id."
                                "specialAccountingStandard"
                            ),
                        )
                    )
                    tuple_created = True

                if (
                    not tuple_created
                    and fact.concept.name.startswith(
                        "genInfo.company.id."
                        "incomeClassification."
                    )
                ):
                    root.append(
                        self.gcd_report_id_tuple_element(
                            fact=fact,
                            context_id=context_id,
                            namespace=namespace,
                            tuple_name=(
                                "genInfo.company.id."
                                "incomeClassification"
                            ),
                        )
                    )
                    tuple_created = True

                if (
                    not tuple_created
                    and fact.concept.name.startswith(
                        "genInfo.company.id.legalStatus."
                        "legalStatus."
                    )
                ):
                    root.append(
                        self.gcd_report_id_tuple_element(
                            fact=fact,
                            context_id=context_id,
                            namespace=namespace,
                            tuple_name=(
                                "genInfo.company.id.legalStatus"
                            ),
                        )
                    )
                    tuple_created = True

                if not tuple_created:
                    root.append(
                        self.text_fact_element(
                            fact=fact,
                            context_id=context_id,
                            namespace=namespace,
                        )
                    )

                continue

            root.append(
                self.fact_element(
                    fact=fact,
                    context_id=context_id,
                    unit_id=self.unit_id_for(
                        unit=fact.unit,
                        units=units,
                    ),
                    namespace=namespace,
                )
            )

        for fact in nil_facts:
            context_id = self.context_id_for(
                context=fact.context,
                contexts=contexts,
            )

            namespace = self.namespace_for(
                concept_id=fact.concept.concept_id,
                taxonomy_namespace=taxonomy_namespace,
                taxonomy_namespaces=taxonomy_namespaces,
            )

            unit_id = None

            if fact.unit is not None:
                unit_id = self.unit_id_for(
                    unit=fact.unit,
                    units=units,
                )

            root.append(
                self.nil_fact_element(
                    fact=fact,
                    context_id=context_id,
                    unit_id=unit_id,
                    namespace=namespace,
                )
            )

        for company_id_no in company_id_nos:
            if not company_id_no.facts:
                continue

            first_fact = company_id_no.facts[0]

            context_id = self.context_id_for(
                context=first_fact.context,
                contexts=contexts,
            )

            namespace = self.namespace_for(
                concept_id=first_fact.concept.concept_id,
                taxonomy_namespace=taxonomy_namespace,
                taxonomy_namespaces=taxonomy_namespaces,
            )

            root.append(
                self.gcd_company_id_no_element(
                    company_id_no=company_id_no,
                    context_id=context_id,
                    namespace=namespace,
                )
            )

        for branch in domestic_branches:
            context_id = self.context_id_for(
                context=branch.fact.context,
                contexts=contexts,
            )

            namespace = self.namespace_for(
                concept_id=branch.fact.concept.concept_id,
                taxonomy_namespace=taxonomy_namespace,
                taxonomy_namespaces=taxonomy_namespaces,
            )

            root.append(
                self.gcd_domestic_branch_of_foreign_company_element(
                    branch=branch,
                    context_id=context_id,
                    namespace=namespace,
                )
            )

        for business in taxable_purpose_businesses:
            context_id = self.context_id_for(
                context=business.fact.context,
                contexts=contexts,
            )

            namespace = self.namespace_for(
                concept_id=business.fact.concept.concept_id,
                taxonomy_namespace=taxonomy_namespace,
                taxonomy_namespaces=taxonomy_namespaces,
            )

            root.append(
                self.gcd_entity_with_taxable_purpose_business_element(
                    business=business,
                    context_id=context_id,
                    namespace=namespace,
                )
            )

        for report_element in report_elements:
            if not report_element.facts:
                continue

            first_fact = report_element.facts[0]

            context_id = self.context_id_for(
                context=first_fact.context,
                contexts=contexts,
            )

            namespace = self.namespace_for(
                concept_id=first_fact.concept.concept_id,
                taxonomy_namespace=taxonomy_namespace,
                taxonomy_namespaces=taxonomy_namespaces,
            )

            root.append(
                self.gcd_report_element_element(
                    report_element=report_element,
                    context_id=context_id,
                    namespace=namespace,
                )
            )

        for shareholder in shareholders:
            context_id = self.context_id_for(
                context=shareholder.name.context,
                contexts=contexts,
            )

            namespace = self.namespace_for(
                concept_id=shareholder.name.concept.concept_id,
                taxonomy_namespace=taxonomy_namespace,
                taxonomy_namespaces=taxonomy_namespaces,
            )

            pure_unit_id = None

            if shareholder.current_number is not None:
                pure_unit_id = self.unit_id_for(
                    unit=shareholder.current_number.unit,
                    units=units,
                )

            root.append(
                self.gcd_shareholder_element(
                    shareholder=shareholder,
                    context_id=context_id,
                    namespace=namespace,
                    pure_unit_id=pure_unit_id,
                )
            )

        for account_balance in account_balances:
            context_id = self.context_id_for(
                context=account_balance.position_name.context,
                contexts=contexts,
            )

            namespace = self.namespace_for(
                concept_id=(
                    account_balance.position_name.concept.concept_id
                ),
                taxonomy_namespace=taxonomy_namespace,
                taxonomy_namespaces=taxonomy_namespaces,
            )

            root.append(
                self.account_balance_element(
                    account_balance=account_balance,
                    context_id=context_id,
                    unit_id=self.unit_id_for(
                        unit=account_balance.amount.unit,
                        units=units,
                    ),
                    namespace=namespace,
                )
            )

        return root

    def schema_ref_element(
        self,
        entry_point: TaxonomyEntryPoint,
    ) -> ET.Element:
        """Erzeugt ein XBRL-schemaRef-Element."""

        return ET.Element(
            "{http://www.xbrl.org/2003/linkbase}schemaRef",
            {
                "{http://www.w3.org/1999/xlink}type": "simple",
                "{http://www.w3.org/1999/xlink}href": (
                    entry_point.schema_ref_uri
                ),
            },
        )

    def to_xml_string(
        self,
        root: ET.Element,
    ) -> str:
        """Serialisiert eine XBRL-Instanz als XML-String."""

        ET.register_namespace(
            "xbrli",
            XBRLI_NAMESPACE,
        )
        ET.register_namespace(
            "xbrldi",
            XBRLDI_NAMESPACE,
        )
        ET.register_namespace(
            "link",
            LINK_NAMESPACE,
        )
        ET.register_namespace(
            "xlink",
            XLINK_NAMESPACE,
        )

        root.set(
            "xmlns:iso4217",
            ISO4217_NAMESPACE,
        )

        xml_bytes = ET.tostring(
            root,
            encoding="utf-8",
            xml_declaration=True,
        )

        return xml_bytes.decode("utf-8")

    def context_id_for(
        self,
        context: TaxonomyContext,
        contexts: dict[str, TaxonomyContext],
    ) -> str:
        """Ermittelt die XBRL-ID eines Contexts."""

        for context_id, candidate in contexts.items():
            if candidate is context:
                return context_id

        raise ValueError(
            "context is not registered"
        )

    def unit_id_for(
        self,
        unit: TaxonomyUnit,
        units: dict[str, TaxonomyUnit],
    ) -> str:
        """Ermittelt die XBRL-ID einer Einheit."""

        for unit_id, candidate in units.items():
            if candidate == unit:
                return unit_id

        raise ValueError(
            "unit is not registered"
        )

    def text_fact_element(
        self,
        fact: TaxonomyTextFact,
        context_id: str,
        namespace: str,
    ) -> ET.Element:
        """Erzeugt ein nichtnumerisches XBRL-Text-Fact-Element."""

        element = ET.Element(
            f"{{{namespace}}}{fact.concept.name}",
            {
                "contextRef": context_id,
            },
        )

        element.text = fact.value

        return element

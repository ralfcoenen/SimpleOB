#!/usr/bin/env python3
"""Kontrollierter HGBM-Praxistest des SimpleOB-ERiC-Pfads für Taxonomie 6.9.

Der Test basiert auf dem gesicherten Stage-8-Pfad und ergänzt ausschließlich
einen kontrollierten handelsrechtlich/steuerlichen Abschreibungsunterschied
von 13,26 EUR. Produktcode und SimpleOB-Buchungen werden nicht verändert.

Ablauf:

1. SimpleOB-Datenbank öffnen.
2. Mandant auswählen.
3. Abgeschlossenes Geschäftsjahr auswählen.
4. Mandantenspezifischen Kontenrahmen laden.
5. Buchungen des Geschäftsjahres laden.
6. Pre-Closing-Ledger erzeugen.
7. GuV mit derselben Fachlogik wie die SimpleOB-Oberfläche erzeugen.
8. Bilanz mit derselben Fachlogik wie die SimpleOB-Oberfläche erzeugen.
9. ERiC-relevante GAAP-CI-Bilanzwerte diagnostisch ausgeben.
10. ERiC-relevante GAAP-CI-GuV-Summenwerte berechnen.
11. Taxonomie-6.9-FactPlan mit den bisherigen produktiven Werten auflösen.
12. Neue XBRL-6.9-Instanz erzeugen.
13. ELSTER-DatenTeil erzeugen.
14. TransferHeader mit EricCreateTH erzeugen.
15. Vollständiges ElsterXML lokal mit ERIC_VALIDIERE validieren.

Die diagnostisch ermittelten Bilanzwerte werden in diesem Schritt
bewusst noch nicht an den FactPlanResolver übergeben.

Der Test:

- liest keine alte XBRL-Datei,
- sendet keine Daten an ELSTER,
- verwendet kein Zertifikat,
- erzeugt keinen PDF-Druck,
- verwendet ausschließlich ERIC_VALIDIERE.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from io import StringIO
from pathlib import Path
import xml.etree.ElementTree as ET

from openbilanz.accounting.balance_sheet import BalanceSheet
from openbilanz.accounting.financial_statement_context import (
    create_financial_statement_context,
    create_standard_financial_statement_context,
)
from openbilanz.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.accounting.ledger import Ledger
from openbilanz.core.config import load_config
from openbilanz.core.version import get_application_version
from openbilanz.database.booking_repository import BookingRepository
from openbilanz.database.chart_of_accounts_repository import (
    ChartOfAccountsRepository,
)
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.database.database import Database
from openbilanz.database.fixed_asset_depreciation_repository import (
    FixedAssetDepreciationRepository,
)
from openbilanz.database.fixed_asset_movement_repository import (
    FixedAssetMovementRepository,
)
from openbilanz.database.fixed_asset_repository import FixedAssetRepository
from openbilanz.database.shareholder_repository import (
    ShareholderRepository,
)
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.booking_type import BookingType
from openbilanz.domain.company import Company
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.fiscal_year_status import FiscalYearStatus
from openbilanz.domain.managed_fiscal_year import ManagedFiscalYear
from openbilanz.domain.money import ZERO
from openbilanz.eric.bilanz_generation.fact_plan_resolver import (
    FactPlanResolver,
)
from openbilanz.eric.bilanz_generation.gaap_ci_6_9_account_detail_values import (
    GaapCi69AccountDetailValueBuilder,
)
from openbilanz.eric.bilanz_generation.gaap_ci_6_9_balance_sheet_values import (
    GaapCi69BalanceSheetValueBuilder,
)
from openbilanz.eric.bilanz_generation.gaap_ci_6_9_income_statement_values import (
    GaapCi69IncomeStatementValueBuilder,
)
from openbilanz.eric.bilanz_generation.gaap_ci_6_9_values import (
    GaapCi69ValueCalculator,
)
from openbilanz.eric.bilanz_generation.taxonomy_6_9 import (
    create_profile_6_9,
)
from openbilanz.eric.bilanz_generation.taxonomy_6_9_values import (
    Taxonomy69ValueBuilder,
)
from openbilanz.eric.bilanz_generation.taxonomy_6_9_xbrl_document_builder import (
    Taxonomy69XbrlDocumentBuilder,
)

from openbilanz.eric.elster_bilanz_payload_service import (
    ElsterBilanzPayloadService,
)
from openbilanz.eric.eric_create_th_adapter import (
    EricCreateThAdapter,
)
from openbilanz.eric.eric_validate_adapter import (
    EricValidateAdapter,
    EricValidateError,
)
from openbilanz.services.closing_result import ClosingResult
from openbilanz.services.closing_service import ClosingService
from openbilanz.services.e_bilanz_account_detail_service import (
    EBilanzAccountDetailService,
)
from openbilanz.services.fixed_asset_schedule_service import (
    FixedAssetScheduleService,
)
from openbilanz.services.posting_service import PostingService
from openbilanz.taxonomy.account_balance_builder import (
    AccountBalanceBuilder,
)
from openbilanz.taxonomy.arelle_adapter import ArelleAdapter
from openbilanz.taxonomy.concept import TaxonomyPeriodType
from openbilanz.taxonomy.concept_set import TaxonomyConceptSet
from openbilanz.taxonomy.context import TaxonomyContext
from openbilanz.taxonomy.entry_point import TaxonomyEntryPoint
from openbilanz.taxonomy.gcd_company_data_mapper import (
    GcdCompanyDataMapper,
)
from openbilanz.taxonomy.gcd_fact_builder import GcdFactBuilder
from openbilanz.taxonomy.gcd_shareholder import (
    GcdShareDivideKey,
    GcdShareholder,
    GcdShareholderLegalStatus,
)
from openbilanz.taxonomy.gcd_report_profile import GcdReportProfile
from openbilanz.taxonomy.hgb_gaap_ci_mapping import (
    create_hgb_gaap_ci_mapping,
)
from openbilanz.taxonomy.gaap_ci_mandatory_fact_completer import (
    GaapCiMandatoryFactCompleter,
)
from openbilanz.taxonomy.fact import TaxonomyFact
from openbilanz.taxonomy.fixed_asset_schedule_builder import (
    FixedAssetScheduleBuilder,
)
from openbilanz.taxonomy.fiscal_requirement_reader import (
    FiscalRequirement,
    FiscalRequirementReader,
)
from openbilanz.taxonomy.mapper import TaxonomyMapper
from openbilanz.taxonomy.nil_fact import TaxonomyNilFact
from openbilanz.taxonomy.resolver import TaxonomyResolver
from openbilanz.taxonomy.taxonomy import TaxonomyVersion
from openbilanz.taxonomy.unit import TaxonomyUnit
from openbilanz.accounting.financial_statement_context import (
    create_standard_financial_statement_context,
)
from openbilanz.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from openbilanz.core.context import ApplicationContext
from openbilanz.database.bvv_annual_data_repository import (
    BvvAnnualDataRepository,
)
from openbilanz.database.tax_depreciation_adjustment_repository import (
    TaxDepreciationAdjustmentRepository,
)
from openbilanz.services.closing_accounts import ClosingAccounts
from openbilanz.services.closing_consistency_service import (
    ClosingConsistencyService,
)
from openbilanz.services.depreciation_booking_service import (
    DepreciationBookingService,
)
from openbilanz.services.depreciation_service import (
    DepreciationService,
)
from openbilanz.services.e_bilanz_export_service import (
    EBilanzExportService,
)
from openbilanz.services.e_bilanz_preparation_service import (
    EBilanzPreparationService,
)
from openbilanz.services.e_bilanz_service import EBilanzService
from openbilanz.services.fiscal_year_closing_workflow import (
    FiscalYearClosingWorkflow,
)
from openbilanz.services.fiscal_year_workspace import (
    FiscalYearWorkspace,
)
from openbilanz.services.fixed_asset_depreciation_workflow import (
    FixedAssetDepreciationWorkflow,
)
from openbilanz.services.posting_service import PostingService
from openbilanz.services.reporting_service import ReportingService
from openbilanz.services.taxonomy_management_service import (
    TaxonomyManagementService,
)
from openbilanz.taxonomy.arelle_adapter import ArelleAdapter
from openbilanz.taxonomy.gcd_company_data_mapper import (
    GcdCompanyDataMapper,
)
from openbilanz.taxonomy.resolver import TaxonomyResolver
from openbilanz.taxonomy.taxonomy_catalog import TaxonomyCatalog
from openbilanz.taxonomy.taxonomy_downloader import (
    TaxonomyDownloader,
)
from openbilanz.taxonomy.taxonomy_installation_service import (
    TaxonomyInstallationService,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TAXONOMY_ROOT = (
    PROJECT_ROOT
    / "data"
    / "taxonomy"
)

OUTPUT_XBRL_FILE = (
    PROJECT_ROOT
    / "eric_69_generated_hgbm.xbrl"
)

ENTITY_SCHEME = (
    "http://www.rzf-nrw.de/Steuernummer"
)

BALANCE_SHEET_ROLE = (
    "http://www.xbrl.de/taxonomies/de-gaap-ci/role/balanceSheet"
)

INCOME_STATEMENT_ROLE = (
    "http://www.xbrl.de/taxonomies/de-gaap-ci/role/incomeStatement"
)


HGBM_TEST_CURRENT_DIFFERENCE = Decimal("83.33")
HGBM_TEST_PREVIOUS_DIFFERENCE = Decimal("0.00")
HGBM_TEST_CUMULATIVE_DIFFERENCE = Decimal("83.33")
HGBM_TEST_TAX_DEPRECIATION = Decimal("250.00")
HGBM_TEST_TAX_NET_INCOME = Decimal("3951.68")
HGBM_TEST_BVV_PROFIT_LOSS = Decimal("3951.68")
HGBM_TEST_BVV_ASSETS_CURRENT_YEAR = Decimal("13951.68")

XBRLI_NAMESPACE = "http://www.xbrl.org/2003/instance"
XBRLDI_NAMESPACE = "http://xbrl.org/2006/xbrldi"
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"

# Diese sechs BAL-Konzepte kommen im amtlichen HGBM-Beispiel in
# dim_comBal vor, nicht jedoch in dim_taxBal. Deshalb werden sie
# im kontrollierten Test nicht blind in die Steuerbilanz dupliziert.
HGBM_TAXBAL_SKIP_CONCEPTS = {
    "accDepr.currChanges",
    "accDepr.diff",
    "accDepr.diff.currDiff",
    "accDepr.diff.otherDiff",
    "gross.currChanges",
    "gross.diff",
}

# UG-0002: steuerliche AfA ist in 2025 und 2026 jeweils 83,33 niedriger
# als die handelsrechtliche AfA. Ende 2026 ist die kumulierte steuerliche
# Abschreibung daher 166,66 niedriger und der steuerliche Buchwert 166,66 höher.
HGBM_BAL_DIFFERENCES = {
    "accDepr.beginning": -HGBM_TEST_PREVIOUS_DIFFERENCE,
    "accDepr.DeprPeriod.regular": -HGBM_TEST_CURRENT_DIFFERENCE,
    "accDepr.DeprPeriod": -HGBM_TEST_CURRENT_DIFFERENCE,
    "accDepr": -HGBM_TEST_CUMULATIVE_DIFFERENCE,
    "all": HGBM_TEST_CUMULATIVE_DIFFERENCE,
}



def _local_name(tag: str) -> str:
    """Gibt den lokalen XML-Namen eines QName-Tags zurück."""

    if tag.startswith("{"):
        return tag.split("}", 1)[1]

    return tag


def _namespace_map(xml: str) -> dict[str, str]:
    """Liest die im XBRL verwendeten Namespace-Präfixe."""

    result: dict[str, str] = {}

    for _event, item in ET.iterparse(
        StringIO(xml),
        events=("start-ns",),
    ):
        prefix, namespace = item
        result[prefix or ""] = namespace

    return result


def _register_namespaces(namespaces: dict[str, str]) -> None:
    """Registriert vorhandene Präfixe für die erneute Serialisierung."""

    for prefix, namespace in namespaces.items():
        if prefix in {"xml", "xmlns"}:
            continue

        try:
            ET.register_namespace(prefix, namespace)
        except ValueError:
            # Reservierte automatische Präfixe (ns0 usw.) sind hier
            # für den Test nicht relevant.
            continue


def _restore_root_namespace_declarations(
    xml: str,
    *,
    namespaces: dict[str, str],
) -> str:
    """Stellt Präfixe wieder her, die nur in QName-Textwerten vorkommen.

    xml.etree.ElementTree kennt Namespace-Verwendungen in Element- und
    Attributnamen, aber nicht in Textwerten wie ``iso4217:EUR``. Solche
    Deklarationen können bei der Serialisierung verloren gehen. Für diesen
    Diagnose-Test werden deshalb die ursprünglich am XBRL vorhandenen
    Präfixe wieder am Wurzelelement deklariert.
    """

    root_tag_end = xml.find(">")

    if root_tag_end < 0:
        raise RuntimeError(
            "Serialisiertes XBRL besitzt kein Wurzelelement."
        )

    root_start = xml[:root_tag_end]
    declarations: list[str] = []

    for prefix, namespace in namespaces.items():
        if not prefix or prefix in {"xml", "xmlns"}:
            continue

        marker = f'xmlns:{prefix}='

        if marker in root_start:
            continue

        declarations.append(
            f' xmlns:{prefix}="{namespace}"'
        )

    if not declarations:
        return xml

    return (
        xml[:root_tag_end]
        + "".join(declarations)
        + xml[root_tag_end:]
    )


def _replace_tax_dimension_member(
    context_element: ET.Element,
    *,
    member_name: str,
) -> None:
    """Ersetzt ausschließlich dim_comBal durch die gewünschte Ausprägung."""

    found = False

    for member in context_element.iter(
        f"{{{XBRLDI_NAMESPACE}}}explicitMember"
    ):
        if (
            member.get("dimension")
            == "de-gaap-ci:dim_taxTrans"
            and member.text
            == "de-gaap-ci:dim_comBal"
        ):
            member.text = f"de-gaap-ci:{member_name}"
            found = True

    if not found:
        raise RuntimeError(
            "Im BAL-Kontext wurde dim_comBal nicht gefunden."
        )


def _numeric_text(value: Decimal) -> str:
    """Serialisiert den kontrollierten Testwert mit zwei Nachkommastellen."""

    return f"{value.quantize(Decimal('0.01')):.2f}"


def _clone_bal_contexts(
    root: ET.Element,
) -> tuple[dict[str, str], dict[str, str]]:
    """Erzeugt zu allen BAL-comBal-Kontexten diff- und taxBal-Kontexte."""

    contexts = [
        element
        for element in list(root)
        if element.tag == f"{{{XBRLI_NAMESPACE}}}context"
    ]

    com_context_ids: list[str] = []

    for context in contexts:
        for member in context.iter(
            f"{{{XBRLDI_NAMESPACE}}}explicitMember"
        ):
            if (
                member.get("dimension")
                == "de-gaap-ci:dim_taxTrans"
                and member.text
                == "de-gaap-ci:dim_comBal"
            ):
                context_id = context.get("id")

                if context_id:
                    com_context_ids.append(context_id)

                break

    if not com_context_ids:
        raise RuntimeError(
            "Kein BAL-Kontext mit dim_comBal gefunden."
        )

    diff_ids: dict[str, str] = {}
    tax_ids: dict[str, str] = {}
    new_contexts: list[ET.Element] = []

    for context in contexts:
        source_id = context.get("id")

        if source_id not in com_context_ids:
            continue

        diff_context = deepcopy(context)
        diff_id = f"{source_id}-diffComToTaxBal"
        diff_context.set("id", diff_id)
        _replace_tax_dimension_member(
            diff_context,
            member_name="dim_diffComToTaxBal",
        )
        diff_ids[source_id] = diff_id
        new_contexts.append(diff_context)

        tax_context = deepcopy(context)
        tax_id = f"{source_id}-taxBal"
        tax_context.set("id", tax_id)
        _replace_tax_dimension_member(
            tax_context,
            member_name="dim_taxBal",
        )
        tax_ids[source_id] = tax_id
        new_contexts.append(tax_context)

    # XBRL-Kontexte müssen vor Units/Facts stehen. Deshalb nicht einfach
    # ans Dokumentende anhängen.
    children = list(root)
    last_context_index = max(
        index
        for index, child in enumerate(children)
        if child.tag == f"{{{XBRLI_NAMESPACE}}}context"
    )

    for offset, context in enumerate(new_contexts, start=1):
        root.insert(last_context_index + offset, context)

    return diff_ids, tax_ids


def _clone_bal_facts(
    root: ET.Element,
    *,
    gaap_namespace: str,
    diff_context_ids: dict[str, str],
    tax_context_ids: dict[str, str],
) -> tuple[int, int]:
    """Erzeugt kontrollierte diffComToTaxBal- und taxBal-Facts."""

    source_facts = [
        element
        for element in list(root)
        if (
            element.get("contextRef")
            in diff_context_ids
            and element.tag.startswith(
                f"{{{gaap_namespace}}}"
            )
        )
    ]

    if not source_facts:
        raise RuntimeError(
            "Keine BAL-Facts zu den dim_comBal-Kontexten gefunden."
        )

    diff_facts: list[ET.Element] = []
    tax_facts: list[ET.Element] = []

    for source_fact in source_facts:
        source_context_id = source_fact.get("contextRef")

        if source_context_id is None:
            continue

        concept_name = _local_name(source_fact.tag)
        is_nil = (
            source_fact.get(
                f"{{{XSI_NAMESPACE}}}nil"
            )
            == "true"
        )

        # Differenzspalte:
        # Bestehende NIL-Facts bleiben NIL. Bei vorhandenen numerischen
        # Facts ist die Differenz 0,00, außer beim einzigen Testunterschied.
        diff_fact = deepcopy(source_fact)
        diff_fact.set(
            "contextRef",
            diff_context_ids[source_context_id],
        )

        if not is_nil:
            diff_value = HGBM_BAL_DIFFERENCES.get(
                concept_name,
                Decimal("0.00"),
            )
            diff_fact.text = _numeric_text(diff_value)

        diff_facts.append(diff_fact)

        # Steuerbilanz:
        # Die amtlich beobachteten comBal-only-Konzepte werden nicht
        # künstlich mit dim_taxBal erzeugt.
        if concept_name in HGBM_TAXBAL_SKIP_CONCEPTS:
            continue

        tax_fact = deepcopy(source_fact)
        tax_fact.set(
            "contextRef",
            tax_context_ids[source_context_id],
        )

        if not is_nil:
            if source_fact.text is None:
                raise RuntimeError(
                    "Numerischer BAL-Fact ohne Wert: "
                    f"{concept_name}"
                )

            commercial_value = Decimal(
                source_fact.text.strip()
            )
            tax_value = (
                commercial_value
                + HGBM_BAL_DIFFERENCES.get(
                    concept_name,
                    Decimal("0.00"),
                )
            )
            tax_fact.text = _numeric_text(tax_value)

        tax_facts.append(tax_fact)

    root.extend(diff_facts)
    root.extend(tax_facts)

    return len(diff_facts), len(tax_facts)


def _append_hgbm_transfer(
    root: ET.Element,
    *,
    gaap_namespace: str,
    duration_context_id: str,
) -> None:
    """Erzeugt den kontrollierten UG-0002-HGBM-Testtuple."""

    qname = lambda name: f"{{{gaap_namespace}}}{name}"
    transfer = ET.Element(qname("hbst.transfer"))
    kind = ET.SubElement(transfer, qname("hbst.transfer.kind"))
    kind_value = ET.SubElement(
        kind,
        qname("hbst.transfer.kind.changeValue"),
        {"contextRef": duration_context_id},
    )
    kind_value.text = "true"

    for concept_name in (
        "bs.ass.fixAss.tan.otherEquipm.otherbga",
        "bs.ass.fixAss.tan.otherEquipm",
        "bs.ass.fixAss.tan",
        "bs.ass.fixAss",
        "bs.ass",
    ):
        change = ET.SubElement(transfer, qname("hbst.transfer.bsAss"))
        name = ET.SubElement(
            change, qname("hbst.transfer.bsAss.name"),
            {"contextRef": duration_context_id},
        )
        name.text = "de-gaap-ci:" + concept_name
        actual = ET.SubElement(
            change, qname("hbst.transfer.bsAss.changeValueActualPeriod"),
            {"contextRef": duration_context_id, "unitRef": "EUR", "decimals": "2"},
        )
        actual.text = _numeric_text(HGBM_TEST_CURRENT_DIFFERENCE)
        previous = ET.SubElement(
            change, qname("hbst.transfer.bsAss.changeValuePreviousPeriod"),
            {"contextRef": duration_context_id, "unitRef": "EUR", "decimals": "2"},
        )
        previous.text = _numeric_text(HGBM_TEST_PREVIOUS_DIFFERENCE)

    for concept_name, actual_amount, previous_amount in (
        (
            "bs.eqLiab.equity.netIncome",
            HGBM_TEST_CURRENT_DIFFERENCE,
            Decimal("0.00"),
        ),
        (
            "bs.eqLiab.equity.retainedEarnings",
            Decimal("0.00"),
            HGBM_TEST_PREVIOUS_DIFFERENCE,
        ),
        (
            "bs.eqLiab.equity",
            HGBM_TEST_CURRENT_DIFFERENCE,
            HGBM_TEST_PREVIOUS_DIFFERENCE,
        ),
        (
            "bs.eqLiab",
            HGBM_TEST_CURRENT_DIFFERENCE,
            HGBM_TEST_PREVIOUS_DIFFERENCE,
        ),
    ):
        change = ET.SubElement(transfer, qname("hbst.transfer.bsEqLiab"))
        name = ET.SubElement(
            change, qname("hbst.transfer.bsEqLiab.name"),
            {"contextRef": duration_context_id},
        )
        name.text = "de-gaap-ci:" + concept_name
        actual = ET.SubElement(
            change, qname("hbst.transfer.bsEqLiab.changeValueActualPeriod"),
            {"contextRef": duration_context_id, "unitRef": "EUR", "decimals": "2"},
        )
        actual.text = _numeric_text(actual_amount)
        previous = ET.SubElement(
            change, qname("hbst.transfer.bsEqLiab.changeValuePreviousPeriod"),
            {"contextRef": duration_context_id, "unitRef": "EUR", "decimals": "2"},
        )
        previous.text = _numeric_text(previous_amount)

    for concept_name, amount in (
        ("is.netIncome.regular.operatingTC.deprAmort.fixAss.tan.other", -HGBM_TEST_CURRENT_DIFFERENCE),
        ("is.netIncome.regular.operatingTC.deprAmort.fixAss.tan", -HGBM_TEST_CURRENT_DIFFERENCE),
        ("is.netIncome.regular.operatingTC.deprAmort.fixAss", -HGBM_TEST_CURRENT_DIFFERENCE),
        ("is.netIncome.regular.operatingTC.deprAmort", -HGBM_TEST_CURRENT_DIFFERENCE),
        ("is.netIncome.regular.operatingTC", HGBM_TEST_CURRENT_DIFFERENCE),
        ("is.netIncome.eat", HGBM_TEST_CURRENT_DIFFERENCE),
        ("is.netIncome", HGBM_TEST_CURRENT_DIFFERENCE),
    ):
        change = ET.SubElement(transfer, qname("hbst.transfer.isChangeNetIncome"))
        name = ET.SubElement(
            change, qname("hbst.transfer.isChangeNetIncome.name"),
            {"contextRef": duration_context_id},
        )
        name.text = "de-gaap-ci:" + concept_name
        actual = ET.SubElement(
            change, qname("hbst.transfer.isChangeNetIncome.changeValueActualPeriod"),
            {"contextRef": duration_context_id, "unitRef": "EUR", "decimals": "2"},
        )
        actual.text = _numeric_text(amount)

    root.append(transfer)



def _activate_stu_report_element(
    root: ET.Element,
    *,
    gcd_namespace: str,
) -> None:
    """Aktiviert STU genau dann für diesen HGBM-Test mit Überleitung."""

    report_element_tag = (
        f"{{{gcd_namespace}}}"
        "genInfo.report.id.reportElement"
    )
    stu_tag = (
        f"{{{gcd_namespace}}}"
        "genInfo.report.id.reportElement.reportElements.STU"
    )

    report_element = None

    for element in root.iter():
        if element.tag == report_element_tag:
            report_element = element
            break

    if report_element is None:
        raise RuntimeError(
            "GCD reportElement-Tuple wurde im XBRL nicht gefunden."
        )

    for child in list(report_element):
        if child.tag == stu_tag:
            # Stage8 enthält STU bisher als NIL. Für den HGBM-Test
            # wird genau dieser vorhandene Eintrag aktiviert.
            child.attrib.pop(
                f"{{{XSI_NAMESPACE}}}nil",
                None,
            )
            child.text = "Steuerliche Überleitungsrechnung"
            return

    # Heutiger Taxonomie-6.9-Pfad:
    # Bedingte Report-Elemente ohne Wert werden vollständig weggelassen.
    # Deshalb contextRef aus einem bereits vorhandenen Report-Element-Fact
    # desselben Tuples übernehmen.
    context_ref = None

    for child in list(report_element):
        context_ref = child.attrib.get("contextRef")
        if context_ref:
            break

    if context_ref is None:
        raise RuntimeError(
            "Kein contextRef für reportElements.STU ermittelbar."
        )

    stu_element = ET.SubElement(
        report_element,
        stu_tag,
        {
            "contextRef": context_ref,
        },
    )
    stu_element.text = "Steuerliche Überleitungsrechnung"


def apply_hgbm_test_case(
    *,
    xbrl_xml: str,
    fiscal_year: FiscalYear,
) -> str:
    """Ergänzt das Stage-8-XBRL um den isolierten HGBM-Testfall."""

    namespaces = _namespace_map(
        xbrl_xml
    )
    _register_namespaces(
        namespaces
    )

    gaap_namespace = namespaces.get(
        "de-gaap-ci"
    )
    gcd_namespace = namespaces.get(
        "de-gcd"
    )

    if not gaap_namespace:
        raise RuntimeError(
            "Namespace de-gaap-ci wurde im XBRL nicht gefunden."
        )

    if not gcd_namespace:
        raise RuntimeError(
            "Namespace de-gcd wurde im XBRL nicht gefunden."
        )

    root = ET.fromstring(
        xbrl_xml
    )

    _activate_stu_report_element(
        root,
        gcd_namespace=gcd_namespace,
    )

    diff_context_ids, tax_context_ids = (
        _clone_bal_contexts(
            root
        )
    )

    diff_fact_count, tax_fact_count = (
        _clone_bal_facts(
            root,
            gaap_namespace=gaap_namespace,
            diff_context_ids=diff_context_ids,
            tax_context_ids=tax_context_ids,
        )
    )

    duration_context_id = (
        f"ctx-duration-{fiscal_year.end_date.year}"
    )

    _append_hgbm_transfer(
        root,
        gaap_namespace=gaap_namespace,
        duration_context_id=duration_context_id,
    )

    print()
    print("Kontrollierter HGBM-Testfall ergänzt:")
    print(
        "  zusätzliche steuerliche AfA: "
        f"{HGBM_TEST_CURRENT_DIFFERENCE}"
    )
    print(
        "  steuerliche AfA gesamt: "
        f"{HGBM_TEST_TAX_DEPRECIATION}"
    )
    print(
        "  steuerliches Ergebnis aus Testüberleitung: "
        f"{HGBM_TEST_TAX_NET_INCOME}"
    )
    print(
        "  BVV.profitLoss (ERiC-Abgleich mit is.netIncome): "
        f"{HGBM_TEST_BVV_PROFIT_LOSS}"
    )
    print(
        "  BVV.assetsCurrentYear (ERiC-Abgleich): "
        f"{HGBM_TEST_BVV_ASSETS_CURRENT_YEAR}"
    )
    print("  reportElements.STU: aktiviert")
    print(
        "  undimensionale Bilanz/GuV: "
        "unverändert handelsrechtlich"
    )
    print(
        "  diffComToTaxBal-Kontexte: "
        f"{len(diff_context_ids)}"
    )
    print(
        "  taxBal-Kontexte: "
        f"{len(tax_context_ids)}"
    )
    print(
        "  diffComToTaxBal-Facts: "
        f"{diff_fact_count}"
    )
    print(
        "  taxBal-Facts: "
        f"{tax_fact_count}"
    )
    print("  hbst.transfer: 1")
    print("  bsAss-Überleitungspositionen: 5 (otherbga, otherEquipm, tan, fixAss, ass)")
    print("  bsEqLiab-Überleitungspositionen: 3 (netIncome, equity, eqLiab)")
    print("  GuV-Überleitungspositionen: 7 (tan.other, tan, fixAss, deprAmort, operatingTC, eat, netIncome)")
    print("  Ergebnis-Überleitung ab operatingTC: +83.33")

    serialized_xml = ET.tostring(
        root,
        encoding="unicode",
        xml_declaration=False,
    )

    return _restore_root_namespace_declarations(
        serialized_xml,
        namespaces=namespaces,
    )


def validate_configuration(config) -> None:
    """Prüft die für den lokalen ERiC-Lauf benötigte Konfiguration."""

    if config.eric_lib_dir is None:
        raise RuntimeError(
            "In data/config.toml ist kein "
            "ERiC-lib-Verzeichnis konfiguriert."
        )

    eric_lib_dir = Path(
        config.eric_lib_dir
    ).expanduser()

    if not eric_lib_dir.is_dir():
        raise RuntimeError(
            "Das konfigurierte ERiC-lib-Verzeichnis "
            f"existiert nicht: {eric_lib_dir}"
        )

    manufacturer_id = (
        config.eric_manufacturer_id
    )

    if (
        manufacturer_id is None
        or not manufacturer_id.strip()
    ):
        raise RuntimeError(
            "In data/config.toml ist keine "
            "ERiC-Hersteller-ID konfiguriert."
        )

    taxonomy_69_root = (
        TAXONOMY_ROOT
        / "6.9"
    )

    if not taxonomy_69_root.is_dir():
        raise RuntimeError(
            "Die Taxonomie 6.9 ist lokal nicht installiert: "
            f"{taxonomy_69_root}"
        )


def select_company(
    companies: tuple[Company, ...],
) -> Company:
    """Wählt den Testmandanten aus."""

    if not companies:
        raise RuntimeError(
            "In der SimpleOB-Datenbank ist kein "
            "Unternehmen vorhanden."
        )

    if len(companies) == 1:
        company = companies[0]

        print(
            "Mandant automatisch ausgewählt: "
            f"{company.name}"
        )

        return company

    print()
    print("Vorhandene Mandanten:")

    for index, company in enumerate(
        companies,
        start=1,
    ):
        print(
            f"  {index}: {company.name}"
        )

    while True:
        value = input(
            "Mandant auswählen: "
        ).strip()

        try:
            index = int(value)
        except ValueError:
            print(
                "Bitte eine Nummer eingeben."
            )
            continue

        if 1 <= index <= len(companies):
            return companies[
                index - 1
            ]

        print(
            "Die Auswahl ist ungültig."
        )


def select_fiscal_year(
    fiscal_years: tuple[
        ManagedFiscalYear,
        ...,
    ],
) -> FiscalYear:
    """Wählt ein abgeschlossenes Geschäftsjahr aus."""

    closed_fiscal_years = tuple(
        managed
        for managed in fiscal_years
        if managed.status
        is FiscalYearStatus.CLOSED
    )

    if not closed_fiscal_years:
        raise RuntimeError(
            "Für den ausgewählten Mandanten ist "
            "kein abgeschlossenes Geschäftsjahr vorhanden."
        )

    if len(closed_fiscal_years) == 1:
        fiscal_year = (
            closed_fiscal_years[
                0
            ].fiscal_year
        )

        print(
            "Geschäftsjahr automatisch ausgewählt: "
            f"{fiscal_year.display_name}"
        )

        return fiscal_year

    print()
    print(
        "Abgeschlossene Geschäftsjahre:"
    )

    for index, managed in enumerate(
        closed_fiscal_years,
        start=1,
    ):
        print(
            f"  {index}: "
            f"{managed.fiscal_year.display_name}"
        )

    while True:
        value = input(
            "Geschäftsjahr auswählen: "
        ).strip()

        try:
            index = int(value)
        except ValueError:
            print(
                "Bitte eine Nummer eingeben."
            )
            continue

        if (
            1
            <= index
            <= len(closed_fiscal_years)
        ):
            return closed_fiscal_years[
                index - 1
            ].fiscal_year

        print(
            "Die Auswahl ist ungültig."
        )


def find_previous_fiscal_year(
    *,
    fiscal_year: FiscalYear,
    fiscal_years: tuple[
        ManagedFiscalYear,
        ...,
    ],
) -> FiscalYear | None:
    """Ermittelt das chronologisch vorherige Geschäftsjahr."""

    previous_candidates = tuple(
        managed.fiscal_year
        for managed in fiscal_years
        if managed.fiscal_year.end_date < fiscal_year.start_date
    )

    if not previous_candidates:
        return None

    return max(
        previous_candidates,
        key=lambda candidate: candidate.end_date,
    )


def create_gcd_shareholders(
    shareholders,
) -> tuple[GcdShareholder, ...]:
    """Überführt gespeicherte Gesellschafter in das bestehende GCD-Modell."""

    result: list[GcdShareholder] = []

    for shareholder in shareholders:
        try:
            legal_status = GcdShareholderLegalStatus(
                shareholder.legal_status
            )
        except ValueError as exc:
            raise ValueError(
                "Unbekannte GCD-Rechtsstellung des Gesellschafters "
                f"{shareholder.shareholder_number}: "
                f"{shareholder.legal_status}"
            ) from exc

        result.append(
            GcdShareholder(
                name=shareholder.name,
                first_name=(
                    shareholder.first_name
                    if shareholder.first_name
                    else None
                ),
                shareholder_id=shareholder.shareholder_number,
                tax_number=(
                    shareholder.tax_number
                    if shareholder.tax_number
                    else None
                ),
                tax_id=(
                    shareholder.tax_id
                    if shareholder.tax_id
                    else None
                ),
                wid=(
                    shareholder.wid
                    if shareholder.wid
                    else None
                ),
                legal_status=legal_status,
                share_divide_key=GcdShareDivideKey(
                    numerator=shareholder.share_numerator,
                    denominator=shareholder.share_denominator,
                ),
            )
        )

    return tuple(result)


def create_mandant_financial_statement_context(
    *,
    company: Company,
    chart_of_accounts_repository: (
        ChartOfAccountsRepository
    ),
):
    """Erzeugt den produktiven Abschlusskontext des Mandanten."""

    standard_context = (
        create_standard_financial_statement_context()
    )

    position_provider = (
        HgbFinancialStatementPositionProvider(
            (
                standard_context.assets,
                standard_context.liabilities,
                standard_context.income_statement,
            )
        )
    )

    loaded_chart_of_accounts = (
        chart_of_accounts_repository
        .load_for_company(
            company_id=company.company_id,
            position_provider=position_provider,
        )
    )

    if loaded_chart_of_accounts is None:
        raise RuntimeError(
            "Der Kontenrahmen des Unternehmens "
            "konnte nicht geladen werden."
        )

    (
        chart_of_accounts,
        accounts,
    ) = loaded_chart_of_accounts

    return create_financial_statement_context(
        assets=standard_context.assets,
        liabilities=standard_context.liabilities,
        income_statement=(
            standard_context.income_statement
        ),
        chart_of_accounts=chart_of_accounts,
        accounts=accounts,
    )


def create_pre_closing_ledger(
    *,
    company: Company,
    fiscal_year: FiscalYear,
    booking_repository: BookingRepository,
) -> Ledger:
    """Erzeugt das Hauptbuch ohne Abschlussbuchungen."""

    bookings = (
        booking_repository.list_for_fiscal_year(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
        )
    )

    if not bookings:
        raise RuntimeError(
            "Für das ausgewählte Geschäftsjahr "
            "sind keine Buchungen vorhanden."
        )

    ledger = Ledger()
    posting_service = PostingService()

    booking_count = 0

    for booking in bookings:
        if (
            booking.booking_type
            is BookingType.CLOSING
        ):
            continue

        posting_service.post_booking(
            booking=booking,
            ledger=ledger,
        )

        booking_count += 1

    print(
        "Pre-Closing-Ledger erzeugt."
    )
    print(
        "Berücksichtigte Buchungen: "
        f"{booking_count}"
    )

    return ledger


def create_income_statement(
    *,
    ledger: Ledger,
    financial_statement_context,
) -> IncomeStatement:
    """Erzeugt die GuV mit derselben Fachlogik wie die Oberfläche."""

    income_statement_account_types = (
        AccountType.REVENUE,
        AccountType.EXPENSE,
    )

    balances = tuple(
        balance
        for balance in ledger.balances()
        if (
            financial_statement_context
            .account_types
            .get(
                balance.account_number
            )
            in income_statement_account_types
        )
        and (
            balance.debit_balance > ZERO
            or balance.credit_balance > ZERO
        )
    )

    amounts = (
        financial_statement_context
        .statement_builder
        .build(
            balances=balances,
            root_positions=(
                financial_statement_context
                .income_statement,
            ),
        )
    )

    return IncomeStatement(
        income_statement=(
            financial_statement_context
            .income_statement
        ),
        amounts=amounts,
    )

def create_balance_sheet(
    *,
    ledger: Ledger,
    financial_statement_context,
    net_income,
) -> BalanceSheet:
    """Erzeugt die Bilanz mit derselben Fachlogik wie die Oberfläche."""

    balance_sheet_account_types = (
        AccountType.ASSET,
        AccountType.LIABILITY,
        AccountType.EQUITY,
    )

    balances = tuple(
        balance
        for balance in ledger.balances()
        if (
            financial_statement_context
            .account_types
            .get(
                balance.account_number
            )
            in balance_sheet_account_types
        )
        and (
            balance.debit_balance > ZERO
            or balance.credit_balance > ZERO
        )
    )

    try:
        equity = next(
            position
            for position
            in financial_statement_context.liabilities.children
            if position.code == "HGB.266.PASSIVA.A"
        )
    except StopIteration as exc:
        raise RuntimeError(
            "Die HGB-Eigenkapitalposition "
            "HGB.266.PASSIVA.A wurde nicht gefunden."
        ) from exc

    try:
        result_position = next(
            position
            for position in equity.children
            if position.code == "HGB.266.PASSIVA.A.V"
        )
    except StopIteration as exc:
        raise RuntimeError(
            "Die HGB-Ergebnisposition "
            "HGB.266.PASSIVA.A.V wurde nicht gefunden."
        ) from exc

    amounts = (
        financial_statement_context
        .statement_builder
        .build(
            balances=balances,
            root_positions=(
                financial_statement_context.assets,
                financial_statement_context.liabilities,
            ),
            closing_result=ClosingResult(
                net_income=net_income,
            ),
            result_position=result_position,
        )
    )

    return BalanceSheet(
        assets=financial_statement_context.assets,
        liabilities=(
            financial_statement_context.liabilities
        ),
        amounts=amounts,
    )

def print_balance_sheet_diagnostics(
    *,
    balance_sheet: BalanceSheet,
    financial_statement_context,
) -> None:
    """Gibt die tatsächlich werthaltigen GAAP-CI-Bilanzwerte aus."""

    values = (
        GaapCi69BalanceSheetValueBuilder.build(
            balance_sheet=balance_sheet,
            income_statement=(
                financial_statement_context
                .income_statement
            ),
        )
    )

    print()
    print("SimpleOB-Bilanz:")
    print(
        "  Aktiva: "
        f"{balance_sheet.amount_for(balance_sheet.assets)}"
    )
    print(
        "  Passiva: "
        f"{balance_sheet.amount_for(balance_sheet.liabilities)}"
    )
    print(
        "  Ausgeglichen: "
        f"{balance_sheet.is_balanced()}"
    )

    print()
    print(
        "Tatsächlich werthaltige "
        "GAAP-CI-Bilanzwerte:"
    )

    for path, value in sorted(
        values.items(),
        key=lambda item: item[0],
    ):
        print(
            f"  {'.'.join(path)} = {value}"
        )

    print(
        "Anzahl werthaltiger "
        "GAAP-CI-Bilanzwerte: "
        f"{len(values)}"
    )


def collect_existing_numeric_or_nil_facts(
    resolved_fact_plan,
):
    """Sammelt vorhandene numerische VALUE- und NIL-Facts rekursiv."""

    facts: list[TaxonomyFact | TaxonomyNilFact] = []

    def visit(node) -> None:
        if isinstance(
            node.fact,
            (TaxonomyFact, TaxonomyNilFact),
        ):
            facts.append(node.fact)

        for child in node.children:
            visit(child)

    for node in resolved_fact_plan.nodes:
        visit(node)

    return tuple(facts)


def load_taxonomy_models():
    """Lädt die echten lokalen Taxonomie-6.9-Modelle."""

    resolver = TaxonomyResolver(
        root=TAXONOMY_ROOT
    )

    gcd_entry_point_path = (
        resolver.gcd_entry_point(
            TaxonomyVersion.V6_9
        )
    )

    gaap_ci_entry_point_path = (
        resolver.gaap_ci_fiscal_entry_point(
            TaxonomyVersion.V6_9
        )
    )

    gcd_entry_point = (
        TaxonomyEntryPoint.from_file(
            gcd_entry_point_path
        )
    )

    gaap_ci_entry_point = (
        TaxonomyEntryPoint.from_file(
            gaap_ci_entry_point_path
        )
    )

    adapter = ArelleAdapter()

    try:
        gcd_model = adapter.model(
            gcd_entry_point_path
        )

        gaap_ci_model = adapter.model(
            gaap_ci_entry_point_path
        )

        concepts = TaxonomyConceptSet(
            concepts=(
                gcd_model.concepts.concepts
                + gaap_ci_model.concepts.concepts
            )
        )

        return (
            adapter,
            concepts,
            gcd_model,
            gaap_ci_model,
            gcd_entry_point,
            gaap_ci_entry_point,
        )

    except Exception:
        adapter.close()
        raise


def build_new_xbrl(
    *,
    master_data,
    fiscal_year: FiscalYear,
    previous_fiscal_year: FiscalYear | None,
    shareholders: tuple[GcdShareholder, ...],
    income_statement: IncomeStatement,
    balance_sheet: BalanceSheet,
    account_details,
    fixed_asset_schedule,
    financial_statement_context,
    net_income,
) -> str:
    """Erzeugt die neue Taxonomie-6.9-XBRL-Instanz."""

    company_mapping = (
        GcdCompanyDataMapper().map(
            master_data
        )
    )

    company_data = (
        company_mapping.company_data
    )

    identifiers = (
        company_mapping.identifiers
    )

    gaap_ci_values = (
        GaapCi69ValueCalculator.calculate(
            income_statement=income_statement,
            net_income=net_income,
        )
    )

    print()
    print(
        "ERiC-relevante GuV-Werte:"
    )
    print(
        "  Jahresergebnis: "
        f"{gaap_ci_values.net_income}"
    )
    print(
        "  Ergebnis nach Steuern: "
        f"{gaap_ci_values.earnings_after_taxes}"
    )
    print(
        "  Betriebsergebnis: "
        f"{gaap_ci_values.operating_total_cost}"
    )
    print(
        "  Rohergebnis: "
        f"{gaap_ci_values.gross_trading_profit}"
    )

    profile = create_profile_6_9()

    report_profile = (
        GcdReportProfile.standard()
    )

    bvv_report_element = (
        "genInfo.report.id.reportElement."
        "reportElements.BVV"
    )

    report_profile = replace(
        report_profile,
        report_elements=(
            *report_profile.report_elements,
            bvv_report_element,
        ),
    )

    if account_details:
        report_profile = replace(
            report_profile,
            report_elements=(
                *report_profile.report_elements,
                (
                    "genInfo.report.id.reportElement."
                    "reportElements.KS"
                ),
            ),
        )

    balance_sheet_values = (
        GaapCi69BalanceSheetValueBuilder.build(
            balance_sheet=balance_sheet,
            income_statement=(
                income_statement.income_statement
            ),
        )
    )

    income_statement_values = (
        GaapCi69IncomeStatementValueBuilder.build(
            income_statement=income_statement,
            assets=balance_sheet.assets,
            liabilities=balance_sheet.liabilities,
            fixed_asset_schedule=fixed_asset_schedule,
        )
    )

    account_detail_values = (
        GaapCi69AccountDetailValueBuilder.build(
            account_details=account_details,
            tax_liability_accounts=("1776",),
            general_rate_sales_accounts=("8400",),
            cash_accounts=("1000",),
            bank_accounts=("1200",),
            input_tax_receivable_accounts=("1576",),
        )
    )

    # Kontrollierter Erstjahresfall UG-0002 (2025):
    # Kein Vorjahr und keine vorgetragene Steuerdifferenz. Die 10.000 EUR
    # Stammkapital sind im Erstjahr als Einlage in der BVV zu berücksichtigen.
    hgb_equity_current = balance_sheet_values[("bs.eqLiab.equity",)]
    tax_equity_current = (
        hgb_equity_current + HGBM_TEST_CUMULATIVE_DIFFERENCE
    )
    tax_equity_previous = Decimal("0.00")
    contribution = Decimal("10000.00")
    withdrawal_distrib = Decimal("0.00")
    bvv_profit_loss = (
        tax_equity_current
        - tax_equity_previous
        - contribution
        + withdrawal_distrib
    )

    if bvv_profit_loss != HGBM_TEST_TAX_NET_INCOME:
        raise RuntimeError(
            "BVV-Erstjahresrechnung stimmt nicht mit dem steuerlichen "
            f"Jahresergebnis überein: {bvv_profit_loss} != "
            f"{HGBM_TEST_TAX_NET_INCOME}"
        )

    bvv_values = {
        ("BVV.profitLoss",): bvv_profit_loss,
        ("BVV.profitLoss.assetsCurrentYear",): tax_equity_current,
        ("BVV.profitLoss.assetsPreviousYear",): tax_equity_previous,
        ("BVV.profitLoss.assetsPreviousYear.assets",): tax_equity_previous,
        (
            "BVV.profitLoss.assetsPreviousYear."
            "capAdjustments",
        ): Decimal("0.00"),
        ("BVV.profitLoss.withdrawalDistrib",): withdrawal_distrib,
        ("BVV.profitLoss.contribution",): contribution,
    }

    print()
    print(
        "Kontrollierte BVV-Testwerte:"
    )

    for path, value in sorted(
        bvv_values.items(),
        key=lambda item: item[0],
    ):
        print(
            f"  {'.'.join(path)} = {value}"
        )

    print()
    print(
        "Werthaltige GAAP-CI-Unterpositionen "
        "aus Kontensalden:"
    )

    for path, value in sorted(
        account_detail_values.items(),
        key=lambda item: item[0],
    ):
        print(
            f"  {'.'.join(path)} = {value}"
        )

    print()
    print(
        "Bilanzwerte an FactPlan übergeben: "
        f"{len(balance_sheet_values)}"
    )

    print()
    print(
        "Werthaltige GAAP-CI-GuV-Werte "
        "aus HGB-GuV:"
    )

    for path, value in sorted(
        income_statement_values.items(),
        key=lambda item: item[0],
    ):
        print(
            f"  {'.'.join(path)} = {value}"
        )

    print()
    print(
        "GuV-Werte an FactPlan übergeben: "
        f"{len(income_statement_values)}"
    )

    entity_identifier = (
        identifiers.tax_number_13
    )

    instant_context = TaxonomyContext(
        entity_identifier=entity_identifier,
        entity_scheme=ENTITY_SCHEME,
        period_type=(
            TaxonomyPeriodType.INSTANT
        ),
        start_date=None,
        end_date=fiscal_year.end_date,
    )

    duration_context = TaxonomyContext(
        entity_identifier=entity_identifier,
        entity_scheme=ENTITY_SCHEME,
        period_type=(
            TaxonomyPeriodType.DURATION
        ),
        start_date=fiscal_year.start_date,
        end_date=fiscal_year.end_date,
    )

    contexts_by_period_type = {
        TaxonomyPeriodType.INSTANT:
            instant_context,
        TaxonomyPeriodType.DURATION:
            duration_context,
    }

    (
        adapter,
        concepts,
        gcd_model,
        gaap_ci_model,
        gcd_entry_point,
        gaap_ci_entry_point,
    ) = load_taxonomy_models()

    try:
        gcd_fact_builder = GcdFactBuilder()

        shareholder_tuples = tuple(
            gcd_fact_builder.shareholder(
                shareholder=shareholder,
                taxonomy_model=gcd_model,
                context=duration_context,
            )
            for shareholder in shareholders
        )

        print(
            "GCD-Gesellschafter-Tuples erzeugt: "
            f"{len(shareholder_tuples)}"
        )

        taxonomy_mapper = TaxonomyMapper(
            create_hgb_gaap_ci_mapping(
                assets=(
                    financial_statement_context.assets
                ),
                liabilities=(
                    financial_statement_context.liabilities
                ),
                income_statement=(
                    financial_statement_context.income_statement
                ),
            ),
            gaap_ci_model,
        )

        account_balance_builder = (
            AccountBalanceBuilder(
                taxonomy_model=gaap_ci_model,
                taxonomy_mapper=taxonomy_mapper,
            )
        )

        account_balances = tuple(
            account_balance_builder.build(
                detail=detail,
                context=duration_context,
            )
            for detail in account_details
        )

        print(
            "KS-Kontennachweis-Tuples erzeugt: "
            f"{len(account_balances)}"
        )


        include_fixed_asset_schedule = True

        fixed_asset_schedule_xbrl = None

        if include_fixed_asset_schedule:
            fixed_asset_schedule_xbrl = (
                FixedAssetScheduleBuilder(
                    taxonomy_model=gaap_ci_model,
                    taxonomy_mapper=taxonomy_mapper,
                ).build(
                    positions=fixed_asset_schedule,
                    entity_identifier=entity_identifier,
                    entity_scheme=ENTITY_SCHEME,
                    fiscal_year_start=fiscal_year.start_date,
                    fiscal_year_end=fiscal_year.end_date,
                )
            )

            print(
                "BAL-Anlagenspiegel-Positionen aus SimpleOB: "
                f"{len(fixed_asset_schedule)}"
            )
            print(
                "BAL-Anlagenspiegel-Facts erzeugt: "
                f"{len(fixed_asset_schedule_xbrl.facts)}"
            )
            print(
                "BAL-Anlagenspiegel-NIL-Facts erzeugt: "
                f"{len(fixed_asset_schedule_xbrl.nil_facts)}"
            )

            if fixed_asset_schedule_xbrl.facts:
                report_profile = replace(
                    report_profile,
                    report_elements=(
                        *report_profile.report_elements,
                        (
                            "genInfo.report.id.reportElement."
                            "reportElements.BAL"
                        ),
                    ),
                )
        else:
            print(
                "BAL-Anlagenspiegel ist im HGBM-Test deaktiviert."
            )

        values = Taxonomy69ValueBuilder().build(
            company_data=company_data,
            identifiers=identifiers,
            report_profile=report_profile,
            fiscal_year=fiscal_year,
            previous_fiscal_year=previous_fiscal_year,
            gaap_ci_values=gaap_ci_values,
        )
        values.update(
            balance_sheet_values
        )

        values.update(
            income_statement_values
        )

        values.update(
            account_detail_values
        )

        values.update(
            bvv_values
        )

        resolved_fact_plan = (
            FactPlanResolver().resolve(
                fact_plan=profile.fact_plan,
                concepts=concepts,
                contexts=(
                    contexts_by_period_type
                ),
                values=values,
            )
        )

        existing_numeric_or_nil_facts = (
            collect_existing_numeric_or_nil_facts(
                resolved_fact_plan
            )
        )

        requirements = FiscalRequirementReader(
            gaap_ci_entry_point
        ).requirements()

        mandatory_nil_facts = (
            GaapCiMandatoryFactCompleter(
                taxonomy_model=gaap_ci_model
            ).build_missing_nil_facts(
                requirements=requirements,
                existing_facts=existing_numeric_or_nil_facts,
                instant_context=instant_context,
                duration_context=duration_context,
                unit=TaxonomyUnit.eur(),
                active_report_element_roles=(
                    BALANCE_SHEET_ROLE,
                    INCOME_STATEMENT_ROLE,
                ),
                excluded_concept_prefixes=(
                    "is.netIncome.regular.operatingCOGS",
                ),
            )
        )

        requirement_by_concept = {
            requirement.concept_name: requirement
            for requirement in requirements
        }

        added_required = sum(
            1
            for fact in mandatory_nil_facts
            if requirement_by_concept[
                fact.concept.name
            ].requirement is FiscalRequirement.REQUIRED
        )
        added_sum_required = sum(
            1
            for fact in mandatory_nil_facts
            if requirement_by_concept[
                fact.concept.name
            ].requirement is FiscalRequirement.SUM_REQUIRED
        )

        kst_mandatory_count = sum(
            1
            for requirement in requirements
            if requirement.legal_form_kst
            and requirement.requirement in {
                FiscalRequirement.REQUIRED,
                FiscalRequirement.SUM_REQUIRED,
            }
        )

        print()
        print(
            "KSt-Pflichtfelder Taxonomie 6.9: "
            f"{kst_mandatory_count}"
        )
        print(
            "Bereits vorhandene numerische/NIL-Facts: "
            f"{len(existing_numeric_or_nil_facts)}"
        )
        print(
            "Zusätzlich erzeugte B/GuV-KSt-Pflicht-NIL-Facts: "
            f"{len(mandatory_nil_facts)}"
        )
        print(
            "  davon Mussfelder: "
            f"{added_required}"
        )
        print(
            "  davon Summenmussfelder: "
            f"{added_sum_required}"
        )

        year = fiscal_year.end_date.year

        contexts = {
            f"ctx-instant-{year}": instant_context,
            f"ctx-duration-{year}": duration_context,
        }

        fixed_asset_nil_facts = ()
        fixed_asset_facts = ()

        if fixed_asset_schedule_xbrl is not None:
            contexts.update(
                fixed_asset_schedule_xbrl.contexts
            )
            fixed_asset_nil_facts = (
                fixed_asset_schedule_xbrl.nil_facts
            )
            fixed_asset_facts = (
                fixed_asset_schedule_xbrl.facts
            )

        units = {
            "EUR": TaxonomyUnit.eur(),
            "PURE": TaxonomyUnit.pure(),
        }

        stage8_xbrl = (
            Taxonomy69XbrlDocumentBuilder()
            .build_xml(
                resolved_fact_plan=resolved_fact_plan,
                contexts=contexts,
                units=units,
                entry_points=(
                    gcd_entry_point,
                    gaap_ci_entry_point,
                ),
                shareholders=shareholder_tuples,
                nil_facts=(
                    mandatory_nil_facts
                    + fixed_asset_nil_facts
                ),
                account_balances=account_balances,
                facts=fixed_asset_facts,
            )
        )

        return apply_hgbm_test_case(
            xbrl_xml=stage8_xbrl,
            fiscal_year=fiscal_year,
        )

    finally:
        adapter.close()

def main() -> None:
    """Führt den vollständigen lokalen ERiC-Praxistest aus."""

    config = load_config()

    validate_configuration(
        config
    )

    database = Database(
        config
    )

    database.create_database()

    session = database.create_session()

    try:
        company_repository = (
            CompanyRepository(
                session
            )
        )

        booking_repository = (
            BookingRepository(
                session
            )
        )

        chart_of_accounts_repository = (
            ChartOfAccountsRepository(
                session
            )
        )

        shareholder_repository = (
            ShareholderRepository(
                session
            )
        )

        fixed_asset_repository = FixedAssetRepository(session)
        fixed_asset_movement_repository = (
            FixedAssetMovementRepository(session)
        )
        fixed_asset_depreciation_repository = (
            FixedAssetDepreciationRepository(session)
        )

        tax_depreciation_adjustment_repository = (
            TaxDepreciationAdjustmentRepository(
                session
            )
        )

        bvv_annual_data_repository = (
            BvvAnnualDataRepository(
                session
            )
        )

        company = select_company(
            company_repository
            .list_companies()
        )

        print()
        print(
            "Ausgewählter Mandant: "
            f"{company.name}"
        )

        managed_fiscal_years = (
            company_repository
            .get_managed_fiscal_years(
                company.company_id
            )
        )

        fiscal_year = (
            select_fiscal_year(
                managed_fiscal_years
            )
        )

        previous_fiscal_year = (
            find_previous_fiscal_year(
                fiscal_year=fiscal_year,
                fiscal_years=managed_fiscal_years,
            )
        )

        print(
            "Ausgewähltes Geschäftsjahr: "
            f"{fiscal_year.display_name}"
        )

        if previous_fiscal_year is None:
            print(
                "Vorheriges Geschäftsjahr: "
                "nicht vorhanden"
            )
        else:
            print(
                "Vorheriges Geschäftsjahr: "
                f"{previous_fiscal_year.display_name}"
            )

        master_data = (
            company_repository
            .get_master_data(
                company.company_id
            )
        )

        if master_data is None:
            raise RuntimeError(
                "Die Unternehmensstammdaten "
                "konnten nicht geladen werden."
            )

        print(
            "Mandantenstammdaten "
            "erfolgreich geladen."
        )

        financial_statement_context = (
            create_mandant_financial_statement_context(
                company=company,
                chart_of_accounts_repository=(
                    chart_of_accounts_repository
                ),
            )
        )

        print(
            "Mandantenspezifischer Kontenrahmen "
            "erfolgreich geladen."
        )

        print()
        print(
            "Produktpfad für E-Bilanz wird aufgebaut."
        )

        context = ApplicationContext(
            company=company,
            fiscal_year=fiscal_year,
        )

        control_accounts = (
            chart_of_accounts_repository
            .load_control_accounts(
                company.company_id
            )
        )

        if control_accounts is None:
            raise RuntimeError(
                "Die technischen Konten des Unternehmens "
                "konnten nicht geladen werden."
            )

        posting_service = PostingService()

        closing_accounts = ClosingAccounts(
            income_summary_account=(
                control_accounts.income_summary_account
            ),
            profit_account=(
                control_accounts.profit_account
            ),
            loss_account=(
                control_accounts.loss_account
            ),
        )

        closing_service = ClosingService(
            closing_accounts=closing_accounts,
        )

        closing_workflow = (
            FiscalYearClosingWorkflow(
                session=session,
                booking_repository=booking_repository,
                company_repository=company_repository,
                closing_service=closing_service,
            )
        )

        closing_consistency_service = (
            ClosingConsistencyService()
        )

        reporting_service = ReportingService()

        fixed_asset_schedule_service = (
            FixedAssetScheduleService(
                fixed_asset_repository=(
                    fixed_asset_repository
                ),
                fixed_asset_movement_repository=(
                    fixed_asset_movement_repository
                ),
                fixed_asset_depreciation_repository=(
                    fixed_asset_depreciation_repository
                ),
            )
        )

        depreciation_service = DepreciationService()

        depreciation_booking_service = (
            DepreciationBookingService()
        )

        fixed_asset_depreciation_workflow = (
            FixedAssetDepreciationWorkflow(
                session=session,
                booking_repository=booking_repository,
                depreciation_repository=(
                    fixed_asset_depreciation_repository
                ),
                booking_service=(
                    depreciation_booking_service
                ),
            )
        )

        e_bilanz_preparation_service = (
            EBilanzPreparationService(
                statement_builder=(
                    financial_statement_context
                    .statement_builder
                ),
                closing_service=closing_service,
                account_types=(
                    financial_statement_context
                    .account_types
                ),
                assets=(
                    financial_statement_context
                    .assets
                ),
                liabilities=(
                    financial_statement_context
                    .liabilities
                ),
                income_summary_account_number=(
                    control_accounts
                    .income_summary_account
                ),
            )
        )

        product_account_detail_service = (
            EBilanzAccountDetailService(
                account_mapper=(
                    financial_statement_context
                    .account_mapper
                ),
                accounts=(
                    financial_statement_context
                    .accounts
                ),
            )
        )

        resolver = TaxonomyResolver(
            root=config.taxonomy_dir
        )

        arelle_adapter = ArelleAdapter()

        product_e_bilanz_service = (
            EBilanzService(
                resolver=resolver,
                adapter=arelle_adapter,
                company_data_mapper=(
                    GcdCompanyDataMapper()
                ),
                assets=(
                    financial_statement_context
                    .assets
                ),
                liabilities=(
                    financial_statement_context
                    .liabilities
                ),
                income_statement=(
                    financial_statement_context
                    .income_statement
                ),
            )
        )

        taxonomy_catalog = TaxonomyCatalog(
            root=config.taxonomy_dir
        )

        taxonomy_installation_service = (
            TaxonomyInstallationService(
                target_root=config.taxonomy_dir
            )
        )

        taxonomy_management_service = (
            TaxonomyManagementService(
                catalog=taxonomy_catalog,
                installation_service=(
                    taxonomy_installation_service
                ),
                download=TaxonomyDownloader().download,
            )
        )

        product_workspace = FiscalYearWorkspace(
            context=context,
            booking_repository=booking_repository,
            company_repository=company_repository,
            bvv_annual_data_repository=(
                bvv_annual_data_repository
            ),
            shareholder_repository=(
                shareholder_repository
            ),
            chart_of_accounts_repository=(
                chart_of_accounts_repository
            ),
            posting_service=posting_service,
            reporting_service=reporting_service,
            closing_workflow=closing_workflow,
            closing_consistency_service=(
                closing_consistency_service
            ),
            e_bilanz_preparation_service=(
                e_bilanz_preparation_service
            ),
            e_bilanz_service=(
                product_e_bilanz_service
            ),
            e_bilanz_account_detail_service=(
                product_account_detail_service
            ),
            e_bilanz_export_service=(
                EBilanzExportService()
            ),
            taxonomy_management_service=(
                taxonomy_management_service
            ),
            fixed_asset_repository=(
                fixed_asset_repository
            ),
            fixed_asset_depreciation_repository=(
                fixed_asset_depreciation_repository
            ),
            tax_depreciation_adjustment_repository=(
                tax_depreciation_adjustment_repository
            ),
            depreciation_service=(
                depreciation_service
            ),
            fixed_asset_depreciation_workflow=(
                fixed_asset_depreciation_workflow
            ),
            fixed_asset_movement_repository=(
                fixed_asset_movement_repository
            ),
            fixed_asset_schedule_service=(
                fixed_asset_schedule_service
            ),
        )

        print(
            "FiscalYearWorkspace für Produktpfad "
            "erfolgreich aufgebaut."
        )

        pre_closing_ledger = (
            create_pre_closing_ledger(
                company=company,
                fiscal_year=fiscal_year,
                booking_repository=(
                    booking_repository
                ),
            )
        )
        account_detail_service = (
            EBilanzAccountDetailService(
                account_mapper=(
                    financial_statement_context
                    .account_mapper
                ),
                accounts=(
                    financial_statement_context
                    .accounts
                ),
            )
        )

        account_details = (
            account_detail_service.build(
                ledger=pre_closing_ledger,
            )
        )

        print(
            "E-Bilanz-Kontensalden erzeugt: "
            f"{len(account_details)}"
        )

        print()
        print("E-Bilanz-Kontensalden im Detail:")

        for detail in account_details:
            print(
                "  "
                f"Konto {detail.account_number}: "
                f"{detail.account_description} | "
                f"HGB={detail.position.code} | "
                f"Saldo={detail.balance}"
            )

        income_statement = (
            create_income_statement(
                ledger=pre_closing_ledger,
                financial_statement_context=(
                    financial_statement_context
                ),
            )
        )

        closing_service = (
            ClosingService()
        )

        net_income = (
            closing_service
            .calculate_net_income(
                income_statement=(
                    income_statement
                )
            )
        )

        print(
            "GuV erfolgreich aus "
            "SimpleOB-Buchungsdaten erzeugt."
        )
        print(
            "Jahresergebnis laut SimpleOB: "
            f"{net_income}"
        )

        balance_sheet = (
            create_balance_sheet(
                ledger=pre_closing_ledger,
                financial_statement_context=(
                    financial_statement_context
                ),
                net_income=net_income,
            )
        )

        print_balance_sheet_diagnostics(
            balance_sheet=balance_sheet,
            financial_statement_context=(
                financial_statement_context
            ),
        )

        stored_shareholders = (
            shareholder_repository.list_for_company(
                company.company_id
            )
        )

        gcd_shareholders = create_gcd_shareholders(
            stored_shareholders
        )

        print(
            "Gesellschafter aus SimpleOB geladen: "
            f"{len(gcd_shareholders)}"
        )

        fixed_asset_schedule = (
            FixedAssetScheduleService(
                fixed_asset_repository=fixed_asset_repository,
                fixed_asset_movement_repository=(
                    fixed_asset_movement_repository
                ),
                fixed_asset_depreciation_repository=(
                    fixed_asset_depreciation_repository
                ),
            ).build(
                company_id=company.company_id,
                fiscal_year_start=fiscal_year.start_date,
                fiscal_year_end=fiscal_year.end_date,
            )
        )

        print(
            "Anlagenspiegel aus SimpleOB erzeugt: "
            f"{len(fixed_asset_schedule)} Position(en)"
        )

        print()
        print(
            "E-Bilanz wird jetzt ausschließlich "
            "über den SimpleOB-Produktpfad erzeugt."
        )

        preparation = (
            product_workspace.prepare_e_bilanz(
                income_statement=income_statement,
            )
        )

        print(
            "E-Bilanz-Vorbereitung über "
            "FiscalYearWorkspace erfolgreich."
        )

        product_document = (
            product_workspace.build_e_bilanz(
                preparation=preparation,
                chart_of_accounts=(
                    financial_statement_context
                    .chart_of_accounts
                ),
            )
        )

        xbrl_xml = product_document.xml

        print(
            "XBRL über "
            "FiscalYearWorkspace -> EBilanzService "
            "erfolgreich erzeugt."
        )

        OUTPUT_XBRL_FILE.write_text(
            xbrl_xml,
            encoding="utf-8",
        )

        print()
        print(
            "Neue Taxonomie-6.9-XBRL-Instanz "
            "erfolgreich erzeugt."
        )
        print(
            "XBRL-Datei: "
            f"{OUTPUT_XBRL_FILE}"
        )
        print(
            "XBRL-Länge: "
            f"{len(xbrl_xml)}"
        )

        payload_service = (
            ElsterBilanzPayloadService()
        )

        data_part_xml = (
            payload_service.build(
                xbrl_xml=xbrl_xml,
                master_data=master_data,
                balance_sheet_date=(
                    fiscal_year.end_date
                ),
            )
        )

        print()
        print(
            "SimpleOB-DatenTeil "
            "erfolgreich erzeugt."
        )
        print(
            "Bilanzstichtag: "
            f"{fiscal_year.end_date}"
        )
        print(
            "DatenTeil-Länge: "
            f"{len(data_part_xml)}"
        )

        eric_lib_dir = Path(
            config.eric_lib_dir
        ).expanduser()

        create_th_adapter = (
            EricCreateThAdapter(
                lib_dir=eric_lib_dir
            )
        )

        elster_xml = (
            create_th_adapter.create(
                data_part_xml=(
                    data_part_xml
                ),
                manufacturer_id=(
                    config
                    .eric_manufacturer_id
                ),
                version_client=(
                    get_application_version()
                ),
            )
        )

        print(
            "EricCreateTH erfolgreich."
        )
        print(
            "ElsterXML-Länge: "
            f"{len(elster_xml)}"
        )

        validate_adapter = (
            EricValidateAdapter(
                lib_dir=eric_lib_dir
            )
        )

        try:
            result = (
                validate_adapter.validate(
                    elster_xml=elster_xml,
                    datenart_version=(
                        "Bilanz_6.9"
                    ),
                )
            )

        except EricValidateError as exc:
            print()
            print(
                "ERiC-Validierung "
                "NICHT erfolgreich."
            )
            print(
                "Fehlercode: "
                f"{exc.error_code}"
            )
            print(
                "Fehlertext: "
                f"{exc.error_text}"
            )
            print(
                "Rückgabe-XML vorhanden: "
                f"{bool(exc.response_xml)}"
            )

            if exc.response_xml:
                print(
                    "--- ERiC-Rückgabe ---"
                )
                print(
                    exc.response_xml
                )

            return

        print()
        print(
            "ERiC-Validierung erfolgreich."
        )

        if result.response_xml:
            print(
                "--- ERiC-Rückgabe ---"
            )
            print(
                result.response_xml
            )

    finally:
        session.close()


if __name__ == "__main__":
    main()

"""HGB-Zuordnungen zur GAAP-CI-Taxonomie."""

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.taxonomy.mapping import TaxonomyMappingRule
from openbilanz.taxonomy.mapping_set import TaxonomyMappingSet

_CONCEPT_NAMES_BY_POSITION_CODE = {
    # Bilanz – Aktiva
    "HGB.266.AKTIVA": "bs.ass",
    "HGB.266.AKTIVA.A": "bs.ass.fixAss",
    "HGB.266.AKTIVA.A.I": "bs.ass.fixAss.intan",
    "HGB.266.AKTIVA.A.I.1": "bs.ass.fixAss.intan.selfmade",
    "HGB.266.AKTIVA.A.I.2": (
        "bs.ass.fixAss.intan.concessionBrands"
    ),
    "HGB.266.AKTIVA.A.I.3": (
        "bs.ass.fixAss.intan.goodwill"
    ),
    "HGB.266.AKTIVA.A.I.4": (
        "bs.ass.fixAss.intan.advPaym"
    ),
    "HGB.266.AKTIVA.A.II": "bs.ass.fixAss.tan",
    "HGB.266.AKTIVA.A.II.1": (
        "bs.ass.fixAss.tan.landBuildings"
    ),
    "HGB.266.AKTIVA.A.II.2": (
        "bs.ass.fixAss.tan.machinery"
    ),
    "HGB.266.AKTIVA.A.II.3": (
        "bs.ass.fixAss.tan.otherEquipm"
    ),
    "HGB.266.AKTIVA.A.II.4": (
        "bs.ass.fixAss.tan.inConstrAdvPaym"
    ),
    "HGB.266.AKTIVA.A.III": "bs.ass.fixAss.fin",
    "HGB.266.AKTIVA.A.III.1": (
        "bs.ass.fixAss.fin.sharesInAffil"
    ),
    "HGB.266.AKTIVA.A.III.2": (
        "bs.ass.fixAss.fin.loansToAffil"
    ),
    "HGB.266.AKTIVA.A.III.3": (
        "bs.ass.fixAss.fin.particip"
    ),
    "HGB.266.AKTIVA.A.III.4": (
        "bs.ass.fixAss.fin.loansToParticip"
    ),
    "HGB.266.AKTIVA.A.III.5": (
        "bs.ass.fixAss.fin.securities"
    ),
    "HGB.266.AKTIVA.A.III.6": (
        "bs.ass.fixAss.fin.otherLoans"
    ),
    "HGB.266.AKTIVA.B": "bs.ass.currAss",
    "HGB.266.AKTIVA.B.I": "bs.ass.currAss.inventory",
    "HGB.266.AKTIVA.B.I.1": (
        "bs.ass.currAss.inventory.material"
    ),
    "HGB.266.AKTIVA.B.I.2": (
        "bs.ass.currAss.inventory.inProgress"
    ),
    "HGB.266.AKTIVA.B.I.3": (
        "bs.ass.currAss.inventory.finishedAndMerch"
    ),
    "HGB.266.AKTIVA.B.I.4": (
        "bs.ass.currAss.inventory.advPaymPaid"
    ),
    "HGB.266.AKTIVA.B.II": "bs.ass.currAss.receiv",
    "HGB.266.AKTIVA.B.II.1": (
        "bs.ass.currAss.receiv.trade"
    ),
    "HGB.266.AKTIVA.B.II.2": (
        "bs.ass.currAss.receiv.affil"
    ),
    "HGB.266.AKTIVA.B.II.3": (
        "bs.ass.currAss.receiv.particip"
    ),
    "HGB.266.AKTIVA.B.II.4": (
        "bs.ass.currAss.receiv.other"
    ),
    "HGB.266.AKTIVA.B.III": (
        "bs.ass.currAss.securities"
    ),
    "HGB.266.AKTIVA.B.III.1": (
        "bs.ass.currAss.securities.affil"
    ),
    "HGB.266.AKTIVA.B.III.2": (
        "bs.ass.currAss.securities.other"
    ),
    "HGB.266.AKTIVA.B.IV": "bs.ass.currAss.cashEquiv",
    "HGB.266.AKTIVA.C": "bs.ass.prepaidExp",
    "HGB.266.AKTIVA.D": "bs.ass.defTax",
    "HGB.266.AKTIVA.E": "bs.ass.SurplusFromOffsetting",

    # Bilanz – Passiva
    "HGB.266.PASSIVA": "bs.eqLiab",
    "HGB.266.PASSIVA.A": "bs.eqLiab.equity",
    "HGB.266.PASSIVA.A.I": (
        "bs.eqLiab.equity.subscribed"
    ),
    "HGB.266.PASSIVA.A.II": (
        "bs.eqLiab.equity.capRes"
    ),
    "HGB.266.PASSIVA.A.III": (
        "bs.eqLiab.equity.revenueRes"
    ),
    "HGB.266.PASSIVA.A.III.1": (
        "bs.eqLiab.equity.revenueRes.legal"
    ),
    "HGB.266.PASSIVA.A.III.2": (
        "bs.eqLiab.equity.revenueRes.sharesParentComp"
    ),
    "HGB.266.PASSIVA.A.III.3": (
        "bs.eqLiab.equity.revenueRes.statutory"
    ),
    "HGB.266.PASSIVA.A.III.4": (
        "bs.eqLiab.equity.revenueRes.other"
    ),
    "HGB.266.PASSIVA.A.IV": (
        "bs.eqLiab.equity.retainedEarnings"
    ),
    "HGB.266.PASSIVA.A.V": (
        "bs.eqLiab.equity.netIncome"
    ),
    "HGB.266.PASSIVA.B": "bs.eqLiab.accruals",
    "HGB.266.PASSIVA.B.1": (
        "bs.eqLiab.accruals.pensions"
    ),
    "HGB.266.PASSIVA.B.2": "bs.eqLiab.accruals.tax",
    "HGB.266.PASSIVA.B.3": (
        "bs.eqLiab.accruals.other"
    ),
    "HGB.266.PASSIVA.C": "bs.eqLiab.liab",
    "HGB.266.PASSIVA.C.1": (
        "bs.eqLiab.liab.securities"
    ),
    "HGB.266.PASSIVA.C.2": "bs.eqLiab.liab.bank",
    "HGB.266.PASSIVA.C.3": "bs.eqLiab.liab.advPaym",
    "HGB.266.PASSIVA.C.4": "bs.eqLiab.liab.trade",
    "HGB.266.PASSIVA.C.5": "bs.eqLiab.liab.notes",
    "HGB.266.PASSIVA.C.6": (
        "bs.eqLiab.liab.assocComp"
    ),
    "HGB.266.PASSIVA.C.7": (
        "bs.eqLiab.liab.particip"
    ),
    "HGB.266.PASSIVA.C.8": "bs.eqLiab.liab.other",
    "HGB.266.PASSIVA.D": "bs.eqLiab.defIncome",
    "HGB.266.PASSIVA.E": "bs.eqLiab.defTax",

    # GuV – Gesamtkostenverfahren
    # HGB.275.GKV ist ein reiner Strukturknoten und wird
    # bewusst nicht als XBRL-Fact gemappt.
    "HGB.275.GKV.1": (
        "is.netIncome.regular.operatingTC."
        "grossTradingProfit.totalOutput.netSales"
    ),
    "HGB.275.GKV.2": (
        "is.netIncome.regular.operatingTC."
        "grossTradingProfit.totalOutput.inventoryChange"
    ),
    "HGB.275.GKV.3": (
        "is.netIncome.regular.operatingTC."
        "grossTradingProfit.totalOutput.ownWork"
    ),
    "HGB.275.GKV.4": (
        "is.netIncome.regular.operatingTC.otherOpRevenue"
    ),
    "HGB.275.GKV.5": (
        "is.netIncome.regular.operatingTC."
        "grossTradingProfit.materialServices"
    ),
    "HGB.275.GKV.5.a": (
        "is.netIncome.regular.operatingTC."
        "grossTradingProfit.materialServices.material"
    ),
    "HGB.275.GKV.5.b": (
        "is.netIncome.regular.operatingTC."
        "grossTradingProfit.materialServices.services"
    ),
    "HGB.275.GKV.6": (
        "is.netIncome.regular.operatingTC.staff"
    ),
    "HGB.275.GKV.6.a": (
        "is.netIncome.regular.operatingTC.staff.salaries"
    ),
    "HGB.275.GKV.6.b": (
        "is.netIncome.regular.operatingTC.staff.social"
    ),
    "HGB.275.GKV.7": (
        "is.netIncome.regular.operatingTC.deprAmort"
    ),
    "HGB.275.GKV.7.a": (
        "is.netIncome.regular.operatingTC.deprAmort.fixAss"
    ),
    "HGB.275.GKV.7.b": (
        "is.netIncome.regular.operatingTC.deprAmort.currAss"
    ),
    "HGB.275.GKV.8": (
        "is.netIncome.regular.operatingTC.otherCost"
    ),
    "HGB.275.GKV.9": (
        "is.netIncome.regular.fin.netParticipation.earnings"
    ),
    "HGB.275.GKV.10": (
        "is.netIncome.regular.fin."
        "netParticipation.earningSecurities"
    ),
    "HGB.275.GKV.11": (
        "is.netIncome.regular.fin.netInterest.income"
    ),
    "HGB.275.GKV.12": (
        "is.netIncome.regular.fin."
        "netParticipation.amortFinanc"
    ),
    "HGB.275.GKV.13": (
        "is.netIncome.regular.fin.netInterest.expenses"
    ),
    "HGB.275.GKV.14": "is.netIncome.tax",
    "HGB.275.GKV.15": "is.netIncome.eat",
    "HGB.275.GKV.16": "is.netIncome.otherTaxes",
    "HGB.275.GKV.17": "is.netIncome",
}


def _walk(
    position: FinancialStatementPosition,
) -> tuple[FinancialStatementPosition, ...]:
    """Liefert eine Abschlussposition einschließlich ihrer Kinder."""

    result = [position]

    for child in position.children:
        result.extend(
            _walk(child)
        )

    return tuple(result)


def create_hgb_gaap_ci_mapping(
    *,
    assets: FinancialStatementPosition,
    liabilities: FinancialStatementPosition,
    income_statement: FinancialStatementPosition,
) -> TaxonomyMappingSet:
    """Erzeugt das HGB-zu-GAAP-CI-Mapping."""

    positions = (
        _walk(assets)
        + _walk(liabilities)
        + _walk(income_statement)
    )

    positions_by_code = {
        position.code: position
        for position in positions
    }

    rules = tuple(
        TaxonomyMappingRule(
            position=positions_by_code[position_code],
            concept_name=concept_name,
        )
        for position_code, concept_name
        in _CONCEPT_NAMES_BY_POSITION_CODE.items()
    )

    return TaxonomyMappingSet(
        rules=rules
    )

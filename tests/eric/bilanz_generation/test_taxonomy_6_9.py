"""Tests für das ERiC-E-Bilanz-Profil der Taxonomie 6.9."""

from openbilanz.eric.bilanz_generation.fact_plan import (
    FactPlanState,
)
from openbilanz.eric.bilanz_generation.taxonomy_6_9 import (
    TAXONOMY_VERSION,
    create_profile_6_9,
)

COMPANY_ID_NO = "genInfo.company.id.idNo"
COMPANY_ST13 = (
    "genInfo.company.id.idNo.type.companyId.ST13"
)
COMPANY_STID = (
    "genInfo.company.id.idNo.type.companyId.STID"
)
COMPANY_STWID = (
    "genInfo.company.id.idNo.type.companyId.STWID"
)
COMPANY_BF4 = (
    "genInfo.company.id.idNo.type.companyId.BF4"
)

ACCORDING_TO = "genInfo.report.id.accordingTo"
ACCORDING_TO_ID_NO = "genInfo.report.id.accordingTo.idNo"

BALANCE_SHEET_CONCEPTS = (
    "bs.ass",
    "bs.ass.currAss",
    "bs.ass.currAss.cashEquiv",
    "bs.ass.fixAss",
    "bs.ass.fixAss.tan",
    "bs.ass.fixAss.tan.otherEquipm",
    "bs.eqLiab",
    "bs.eqLiab.equity",
    "bs.eqLiab.equity.netIncome",
    "bs.eqLiab.equity.retainedEarnings",
    "bs.eqLiab.equity.subscribed",
    "bs.eqLiab.liab",
    "bs.eqLiab.liab.other",
    "bs.ass.fixAss.intan.concessionBrands",
    "bs.ass.fixAss.intan.goodwill",
    "bs.ass.fixAss.intan.advPaym",
    (
        "bs.ass.fixAss.tan.landBuildings."
        "landWithoutBuildings"
    ),
    (
        "bs.ass.fixAss.tan.landBuildings."
        "rightEquivalentToLandWithoutBuildings"
    ),
    (
        "bs.ass.fixAss.tan.landBuildings."
        "buildingsOnOwnLand.land"
    ),
    (
        "bs.ass.fixAss.tan.landBuildings."
        "buildingsOnOwnLand.buildings"
    ),
    (
        "bs.ass.fixAss.tan.landBuildings."
        "buildingsOnNonOwnedLand"
    ),
    "bs.ass.fixAss.tan.machinery",
    (
    "bs.ass.fixAss.tan.otherEquipm."
        "passengerCars"
    ),
    "bs.ass.fixAss.tan.inConstrAdvPaym",
    "bs.ass.fixAss.tan.other",
    (
        "bs.ass.fixAss.fin.sharesInAffil."
        "partnerships.commPart.silentAtyp"
    ),
    (
        "bs.ass.fixAss.fin.sharesInAffil."
        "partnerships.commPart.other"
    ),
    (
    "bs.ass.fixAss.fin.sharesInAffil."
        "partnerships.assetManaging"
    ),
    (
        "bs.ass.fixAss.fin.sharesInAffil."
        "corporations"
    ),
    (
        "bs.ass.fixAss.fin.loansToSharehold."
        "gmbh"
    ),
    (
        "bs.ass.fixAss.fin.loansToAffil."
        "partnerships.sharesSilentAtyp"
    ),
    (
        "bs.ass.fixAss.fin.loansToAffil."
        "corporations"
    ),
    (
        "bs.ass.fixAss.fin.particip.partnerships."
        "commPart.silentAtyp"
    ),
    (
        "bs.ass.fixAss.fin.particip.partnerships."
        "commPart.other"
    ),
    (
        "bs.ass.fixAss.fin.particip.partnerships."
        "assetManaging"
    ),
    "bs.ass.fixAss.fin.particip.corporations",
    (
        "bs.ass.fixAss.fin.loansToParticip."
        "partnerships.atypSilent"
    ),
    (
        "bs.ass.fixAss.fin.loansToParticip."
        "partnerships.other"
    ),
    (
        "bs.ass.fixAss.fin.loansToParticip."
        "corporations"
    ),
    "bs.ass.fixAss.fin.securities",
    "bs.ass.fixAss.fin",
    "bs.ass.fixAss.fin.otherLoans",
    "bs.ass.fixAss.fin.otherLoans.partnership.comm",
    (
        "bs.ass.fixAss.fin.otherLoans."
        "partnership.comm.atypSilent"
    ),
    (
        "bs.ass.fixAss.fin.otherLoans."
        "partnership.comm.other"
    ),
    "bs.ass.fixAss.fin.otherLoans.assetManaging",
    "bs.ass.fixAss.fin.otherFinAss.reInsurClaim",
    "bs.ass.currAss.inventory.material",
    "bs.ass.currAss.inventory.inProgress",
    "bs.ass.currAss.inventory.finishedAndMerch",
    "bs.ass.currAss.inventory.advPaymPaid",
    "bs.ass.currAss.receiv",
    "bs.ass.currAss.receiv.shareholders.gmbh",
    "bs.ass.currAss.receiv.affil",
    "bs.ass.currAss.receiv.particip",
    "bs.ass.currAss.receiv.colEntity",
    "bs.ass.currAss.receiv.other",
    "bs.ass.currAss.receiv.other.unpaidCapital",
    "bs.ass.currAss.receiv.other.commPart.atyp",
    "bs.ass.currAss.receiv.other.commPart.other",
    "bs.ass.currAss.receiv.other.assetManaging",
    "bs.ass.currAss.receiv.other.reInsurClaim",
    "bs.ass.currAss.securities.affil",
    "bs.ass.currAss.securities.other",
    "bs.ass.currAss.cashEquiv.cash",
    "bs.ass.prepaidExp",
    "bs.eqLiab.equity.subscribed.corp",
    "bs.eqLiab.equity.capRes",
    "bs.eqLiab.equity.revenueRes.legal",
    "bs.eqLiab.equity.revenueRes.statutory",
    "bs.eqLiab.equity.revenueRes.other",
    (
        "bs.eqLiab.equity.netIncome."
        "taxBalanceGenerally.finalPrev"
    ),
    (
        "bs.eqLiab.equity.netIncome."
        "taxBalanceGenerally.transferDiffTaxAccounts"
    ),
    "bs.eqLiab.equity.profitLoss",
    (
        "bs.eqLiab.otherSpecRes.other."
        "releaseWithdrawalEStG4g"
    ),
    "bs.eqLiab.otherSpecRes.other.EStG6b",
    "bs.eqLiab.otherSpecRes.other.replacement",
    "bs.eqLiab.accruals.pensions.shareholder",
    "bs.eqLiab.accruals.pensions.direct",
    "bs.eqLiab.accruals.pensions.externalFunds",
    "bs.eqLiab.accruals.tax.gewst",
    "bs.eqLiab.accruals.other",
    "bs.eqLiab.liab.securities",
    "bs.eqLiab.liab.bank.silentPartner",
    "bs.eqLiab.liab.advPaym",
    "bs.eqLiab.liab.notes",
    "bs.eqLiab.liab.shareholders.gmbh",
    "bs.eqLiab.liab.shareholders.silentPart",
    "bs.eqLiab.liab.assocComp.SilentPartner",
    "bs.eqLiab.liab.particip.silentPartner",
    "bs.eqLiab.liab.colEntity",
    "bs.eqLiab.defIncome",
    "bs.eqLiab.liab.regulatory",
    "bs.ass.currAss.receiv.trade.shareholders",
    "bs.eqLiab.liab.trade.shareholders",
    "bs.ass.currAss.receiv.other.shareholders",
    "bs.eqLiab.liab.other.shareholders",
    "bs.eqLiab.equity.revenueRes.special",
    "is.netIncome",
    "is.netIncome.eat",
    "is.netIncome.incomeSharing",
    "is.netIncome.regular.fin",
    "is.netIncome.regular.fin.netInterest.expenses",
    "is.netIncome.regular.fin.netInterest.expenses.regularInterest",
    "is.netIncome.regular.fin.netInterest.expenses.regularInterest.PartnersLoans",
    "is.netIncome.regular.fin.netInterest.income",
    "is.netIncome.regular.fin.netInterest.income.deposits",
    "is.netIncome.regular.fin.netInterest.income.securities",
    "is.netIncome.regular.fin.netParticipation.amortFinanc",
    "is.netIncome.regular.fin.netParticipation.amortFinanc.financialsExcept",
    "is.netIncome.regular.fin.netParticipation.earningSecurities",
    "is.netIncome.regular.fin.netParticipation.earningSecurities.interestDividend",
    "is.netIncome.regular.fin.netParticipation.earnings",
    "is.netIncome.regular.operatingTC",
    "is.netIncome.regular.operatingTC.deprAmort",
    "is.netIncome.regular.operatingTC.deprAmort.currAss",
    "is.netIncome.regular.operatingTC.deprAmort.currAss.receiv",
    "is.netIncome.regular.operatingTC.deprAmort.fixAss",
    "is.netIncome.regular.operatingTC.deprAmort.fixAss.specific",
    "is.netIncome.regular.operatingTC.deprAmort.fixAss.specific.except",
    "is.netIncome.regular.operatingTC.deprAmort.fixAss.tan",
    "is.netIncome.regular.operatingTC.grossTradingProfit",
    "is.netIncome.regular.operatingTC.grossTradingProfit.materialServices",
    "is.netIncome.regular.operatingTC.grossTradingProfit.materialServices.material",
    "is.netIncome.regular.operatingTC.grossTradingProfit.materialServices.material.purchased",
    "is.netIncome.regular.operatingTC.grossTradingProfit.materialServices.material.rawMatConsSup",
    "is.netIncome.regular.operatingTC.grossTradingProfit.materialServices.services",
    "is.netIncome.regular.operatingTC.grossTradingProfit.totalOutput",
    "is.netIncome.regular.operatingTC.grossTradingProfit.totalOutput.netSales",
    "is.netIncome.regular.operatingTC.grossTradingProfit.totalOutput.netSales.grossSales",
    "is.netIncome.regular.operatingTC.grossTradingProfit.totalOutput.netSales.grossSales.taxExemptUStG4_8",
    "is.netIncome.regular.operatingTC.grossTradingProfit.totalOutput.netSales.reductionsFromGrossSales",
    "is.netIncome.regular.operatingTC.otherCost",
    "is.netIncome.regular.operatingTC.otherCost.addPreTaxRes",
    "is.netIncome.regular.operatingTC.otherCost.disposFixAss",
    "is.netIncome.regular.operatingTC.otherCost.disposFixAss.bookValue",
    "is.netIncome.regular.operatingTC.otherCost.disposFixAss.sale",
    "is.netIncome.regular.operatingTC.otherCost.leaseFix",
    "is.netIncome.regular.operatingTC.otherCost.leaseMovable",
    "is.netIncome.regular.operatingTC.otherCost.leasingAll",
    "is.netIncome.regular.operatingTC.otherCost.limitedDeductible",
    "is.netIncome.regular.operatingTC.otherCost.limitedDeductible.entertainment",
    "is.netIncome.regular.operatingTC.otherCost.limitedDeductible.gifts",
    "is.netIncome.regular.operatingTC.otherCost.transferValuatonPresentYear",
    "is.netIncome.regular.operatingTC.otherOpRevenue",
    "is.netIncome.regular.operatingTC.otherOpRevenue.disposFixAss",
    "is.netIncome.regular.operatingTC.otherOpRevenue.disposFixAss.bookValue",
    "is.netIncome.regular.operatingTC.otherOpRevenue.disposFixAss.sale",
    "is.netIncome.regular.operatingTC.otherOpRevenue.ownConsumption",
    "is.netIncome.regular.operatingTC.otherOpRevenue.releaseLossProv",
    "is.netIncome.regular.operatingTC.otherOpRevenue.releasePreTaxRes",
    "is.netIncome.regular.operatingTC.staff",
    "is.netIncome.regular.operatingTC.staff.salaries",
    "is.netIncome.regular.operatingTC.staff.social",
    "is.netIncome.regular.operatingTC.staff.social.pensions",
    "is.netIncome.regular.operatingTC.staff.social.socExp",
    "is.netIncome.tax",
)

INCOME_STATEMENT_CONCEPTS = (
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.grossSales.UStG13b",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.grossSales.untaxable",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.grossSales.taxExemptUStG4_1a",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.grossSales.taxExemptUStG4_1b",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.grossSales.taxExemptUStG4_8.UStG4_12",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.grossSales.taxExemptUStG4_2til7",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.grossSales.taxExemptUStG19_1",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.grossSales.taxExemptOther",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.grossSales.0VATrateUStG12_3",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.grossSales.reducedRateVAT",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.grossSales.generalRateVAT",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.grossSales.UStG25_25a",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.grossSales.UStG24",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.grossSales.otherRateVAT",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.reductionsFromGrossSales.untaxed",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.reductionsFromGrossSales.untaxable",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.reductionsFromGrossSales.taxExemptUStG4_1a",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.reductionsFromGrossSales.taxExemptUStG4_1b",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.reductionsFromGrossSales.taxExemptUStG4_8",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.reductionsFromGrossSales.taxExemptUStG4_2til7",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.reductionsFromGrossSales.taxExemptUSt19_1",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.reductionsFromGrossSales.taxExemptOther",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.reductionsFromGrossSales.generalRateVAT",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.reductionsFromGrossSales.reducedRateVAT",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.reductionsFromGrossSales.0VATrateUStG12_3",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.reductionsFromGrossSales.averageRateUStGs24",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.reductionsFromGrossSales.UStGss25and25a",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.reductionsFromGrossSales.otherRateVAT",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.netSales.taxFromGrossSales",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.inventoryChange",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "totalOutput.ownWork",
    "is.netIncome.regular.operatingTC.otherOpRevenue."
    "releasePreTaxRes.EStG6b_3",
    "is.netIncome.regular.operatingTC.otherOpRevenue."
    "releasePreTaxRes.substEStR6_6",
    "is.netIncome.regular.operatingTC.otherOpRevenue."
    "releasePreTaxRes.EStG4g",
    "is.netIncome.regular.operatingTC.otherOpRevenue."
    "releasePreTaxRes.EStG5_7",
    "is.netIncome.regular.operatingTC.otherOpRevenue."
    "disposFixAss.sale.intan",
    "is.netIncome.regular.operatingTC.otherOpRevenue."
    "disposFixAss.sale.tan",
    "is.netIncome.regular.operatingTC.otherOpRevenue."
    "disposFixAss.sale.fin",
    "is.netIncome.regular.operatingTC.otherOpRevenue."
    "disposFixAss.bookValue.intan",
    "is.netIncome.regular.operatingTC.otherOpRevenue."
    "disposFixAss.bookValue.tan",
    "is.netIncome.regular.operatingTC.otherOpRevenue."
    "disposFixAss.bookValue.fin",
    "is.netIncome.regular.operatingTC.otherOpRevenue."
    "revalFixAss",
    "is.netIncome.regular.operatingTC.otherOpRevenue."
    "releaseProv",
    "is.netIncome.regular.operatingTC.otherOpRevenue."
    "revalCurrAss",
    "is.netIncome.regular.operatingTC.otherOpRevenue."
    "releaseLossProv.specificValuation",
    "is.netIncome.regular.fin.netParticipation.earningProfSharing",
    "is.netIncome.regular.fin.commPart",
    "is.netIncome.regular.fin.netParticipation.incomeTaxAlloc",
    "is.netIncome.regular.fin.netParticipation."
    "earningSecurities.corporations",
    "is.netIncome.regular.fin.netParticipation."
    "earningSecurities.partnerships",
    "is.netIncome.regular.fin.netParticipation."
    "earningSecurities.interestDividend.dividend",
    "is.netIncome.regular.fin.netInterest.income.valueDiscount",
    "is.netIncome.regular.fin.netInterest.income.deposits.AO233a",
    "is.netIncome.regular.fin.netInterest.income.discount",
    "is.netIncome.regular.fin.netInterest."
    "income.securities.dividends",
    "is.netIncome.regular.fin.netParticipation."
    "amortFinanc.longTermRecAllowance",
    "is.netIncome.regular.fin.netParticipation."
    "amortFinanc.longTermRecLumSumAllow",
    "is.netIncome.regular.fin.netParticipation."
    "amortFinanc.secCurrAss",
    "is.netIncome.regular.fin.netInterest.expenses.valueDiscount",
    "is.netIncome.regular.fin.netInterest."
    "expenses.regularInterest.AO233a",
    "is.netIncome.regular.fin.netInterest."
    "expenses.regularInterest.PartnersLoans.participationOver25pt",
    "is.netIncome.regular.fin.lossCommPart",
    "is.netIncome.regular.fin.netParticipation."
    "expenseTaxAllocSubsidiary",
    "is.netIncome.extraord.income.merger",
    "is.netIncome.tax.gewst",
    "is.netIncome.regular.operatingTC.otherOpRevenue."
    "releaseLossProv.globalValuation",
    "is.netIncome.regular.operatingTC.otherOpRevenue."
    "releasLiab",
    "is.netIncome.regular.operatingTC.otherOpRevenue."
    "recoveryWriteoffs",
    "is.netIncome.regular.operatingTC.otherOpRevenue."
    "subsidies",
    "is.netIncome.regular.operatingTC.otherOpRevenue."
    "insuranceRefunds",
    "is.netIncome.regular.operatingTC.otherOpRevenue."
    "ownConsumption.otherWithdrawals",
    "is.netIncome.regular.operatingTC.otherOpRevenue."
    "ownConsumption.nonCashBenefitsCompCar",
    "is.netIncome.regular.operatingTC.otherOpRevenue."
    "ownConsumption.nonCashBenefitsOther",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "materialServices.material.rawMatConsSup.generalRateVAT",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "materialServices.material.rawMatConsSup.reducedRateVAT",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "materialServices.material.rawMatConsSup.intraEU",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "materialServices.material.rawMatConsSup.inventoryChange",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "materialServices.material.purchased.generalRateVAT",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "materialServices.material.purchased.reducedRateVAT",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "materialServices.material.purchased.intraEU",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "materialServices.material.purchased.withoutVAT",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "materialServices.material.purchased.inventoryChange",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "materialServices.services.UStG13bDedInputTax",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "materialServices.services.UStG13bNonDedInputTax",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "materialServices.services.OtherDedInputTax",
    "is.netIncome.regular.operatingTC.grossTradingProfit."
    "materialServices.services.OtherNonDedInputTax",
    "is.netIncome.regular.operatingTC.staff."
    "salaries.minijobs",
    "is.netIncome.regular.operatingTC.staff."
    "salaries.managerPartner",
    "is.netIncome.regular.operatingTC.staff."
    "salaries.inKind",
    "is.netIncome.regular.operatingTC.staff."
    "salaries.voluntayBenefits",
    "is.netIncome.regular.fin.netParticipation."
    "earnings.corporations",
    "is.netIncome.regular.fin.netParticipation."
    "earnings.silentPart",
    "is.netIncome.otherTaxes",
    "is.netIncome.incomeSharing.loss",
    "is.netIncome.incomeSharing.gain",
    "is.netIncome.regular.operatingTC.otherCost."
    "disposalCorp",
    "is.netIncome.regular.operatingTC.otherOpRevenue."
    "releasePreTaxRes.KStGs34_6e",
    "is.netIncome.regular.operatingTC.staff.social."
    "socExp.other",
    "is.netIncome.regular.operatingTC.staff.social."
    "pensions.shareholderManager",
    "is.netIncome.regular.operatingTC.staff.social."
    "pensions.other",
    "is.netIncome.regular.operatingTC.staff.social."
    "welfare",
    "is.netIncome.regular.operatingTC.deprAmort."
    "fixAss.goodwill",
    "is.netIncome.regular.operatingTC.deprAmort."
    "fixAss.otherIntan",
    "is.netIncome.regular.operatingTC.deprAmort."
    "fixAss.tan.lowValueAs",
    "is.netIncome.regular.operatingTC.deprAmort."
    "fixAss.tan.lowValueAsCollItem",
    "is.netIncome.regular.operatingTC.deprAmort."
    "fixAss.tan.buildings",
    "is.netIncome.regular.operatingTC.deprAmort."
    "fixAss.specific.except.goodwill",
    "is.netIncome.regular.operatingTC.deprAmort."
    "fixAss.specific.except.otherIntan",
    "is.netIncome.regular.fin.netParticipation."
    "amortFinanc.financialsExcept.participCorp",
    "is.netIncome.regular.operatingTC.deprAmort."
    "fixAss.specific.except.tan",
    "is.netIncome.regular.operatingTC.deprAmort."
    "fixAss.specific.impairment",
    "is.netIncome.regular.operatingTC.deprAmort."
    "currAss.inventory",
    "is.netIncome.regular.operatingTC.deprAmort."
    "currAss.receiv.againstCorpParticip",
    "is.netIncome.regular.operatingTC.deprAmort."
    "currAss.receiv.sharehRelPart",
    "is.netIncome.regular.operatingTC.otherCost."
    "leaseFix.shareholders",
    "is.netIncome.regular.operatingTC.otherCost."
    "leaseFix.other",
    "is.netIncome.regular.operatingTC.otherCost."
    "leasingAll.moveable",
    "is.netIncome.regular.operatingTC.otherCost."
    "leasingAll.immovable",
    "is.netIncome.regular.operatingTC.otherCost."
    "leaseMoveable.shareholders",
    "is.netIncome.regular.operatingTC.otherCost."
    "leaseMoveable.other",
    "is.netIncome.regular.operatingTC.otherCost."
    "energyCost",
    "is.netIncome.regular.operatingTC.otherCost."
    "communication",
    "is.netIncome.regular.operatingTC.otherCost."
    "legalConsulting",
    "is.netIncome.regular.operatingTC.otherCost."
    "training",
    "is.netIncome.regular.operatingTC.otherCost."
    "insurance",
    "is.netIncome.regular.operatingTC.otherCost."
    "vehicles",
    "is.netIncome.regular.operatingTC.otherCost."
    "freight",
    "is.netIncome.regular.operatingTC.otherCost."
    "fees",
    "is.netIncome.regular.operatingTC.otherCost."
    "concessLicenses",
    "is.netIncome.regular.operatingTC.otherCost."
    "marketing",
    "is.netIncome.regular.operatingTC.otherCost."
    "limitedDeductible.gifts.deductible",
    "is.netIncome.regular.operatingTC.otherCost."
    "limitedDeductible.gifts.nondeductible",
    "is.netIncome.regular.operatingTC.otherCost."
    "limitedDeductible.entertainment.deductible",
    "is.netIncome.regular.operatingTC.otherCost."
    "limitedDeductible.entertainment.nonDeductible",
    "is.netIncome.regular.operatingTC.otherCost."
    "limitedDeductible.other",
    "is.netIncome.regular.operatingTC.otherCost."
    "regAllowance",
    "is.netIncome.regular.operatingTC.otherCost."
    "otherTaxes",
    "is.netIncome.regular.operatingTC.otherCost."
    "addPreTaxRes.EStG6b_3",
    "is.netIncome.regular.operatingTC.otherCost."
    "addPreTaxRes.substEStR6_6",
    "is.netIncome.regular.operatingTC.otherCost."
    "addPreTaxRes.EStG4g",
    "is.netIncome.regular.operatingTC.otherCost."
    "addPreTaxRes.EStG5_7",
    "is.netIncome.regular.operatingTC.otherCost."
    "deductValueEStG7g_2",
    "is.netIncome.regular.operatingTC.deprAmort."
    "fixAss.specific.EStG6b_3",
    "is.netIncome.regular.operatingTC.otherCost."
    "transferValuatonPresentYear.specific",
    "is.netIncome.regular.operatingTC.otherCost."
    "transferValuatonPresentYear.global",
    "is.netIncome.regular.operatingTC.otherCost."
    "disposFixAss.sale.intan",
    "is.netIncome.regular.operatingTC.otherCost."
    "disposFixAss.sale.tan",
    "is.netIncome.regular.operatingTC.otherCost."
    "disposFixAss.sale.fin",
    "is.netIncome.regular.operatingTC.otherCost."
    "disposFixAss.bookValue.intan",
    "is.netIncome.regular.operatingTC.otherCost."
    "disposFixAss.bookValue.tan",
    "is.netIncome.regular.operatingTC.otherCost."
    "disposFixAss.bookValue.fin",
    "is.netIncome.regular.operatingTC.otherCost."
    "provisions",
    "is.netIncome.regular.operatingTC.otherCost."
    "merger",
    "is.netIncome.regular.operatingTC.otherCost."
    "miscellaneous",
    "is.netIncome.regular.operatingTC.cooperative."
    "Refunds",

)

def _state_for(concept_name: str) -> FactPlanState:
    profile = create_profile_6_9()
    node = profile.fact_plan.node_for(concept_name)

    assert node is not None

    return node.state


def _state_for_path(
    *concept_names: str,
) -> FactPlanState:
    profile = create_profile_6_9()
    node = profile.fact_plan.node_for_path(
        *concept_names,
    )

    assert node is not None

    return node.state


def test_profile_has_taxonomy_version_6_9() -> None:
    profile = create_profile_6_9()

    assert TAXONOMY_VERSION == "6.9"
    assert profile.taxonomy_version == "6.9"


def test_company_st13_is_required_value() -> None:
    assert (
        _state_for_path(
            COMPANY_ID_NO,
            COMPANY_ST13,
        )
        is FactPlanState.VALUE
    )


def test_company_stid_is_value_or_nil() -> None:
    assert (
        _state_for_path(
            COMPANY_ID_NO,
            COMPANY_STID,
        )
        is FactPlanState.VALUE_OR_NIL
    )


def test_company_stwid_is_value_or_nil() -> None:
    assert (
        _state_for_path(
            COMPANY_ID_NO,
            COMPANY_STWID,
        )
        is FactPlanState.VALUE_OR_NIL
    )


def test_company_bf4_is_conditional() -> None:
    assert (
        _state_for_path(
            COMPANY_ID_NO,
            COMPANY_BF4,
        )
        is FactPlanState.CONDITIONAL
    )


def test_according_to_is_required_nil_tuple() -> None:
    assert (
        _state_for(ACCORDING_TO)
        is FactPlanState.REQUIRED_NIL_TUPLE
    )


def test_according_to_name_is_nil() -> None:
    assert (
        _state_for(
            "genInfo.report.id.accordingTo.name"
        )
        is FactPlanState.NIL
    )


def test_according_to_id_no_is_required_nil_tuple() -> None:
    assert (
        _state_for(ACCORDING_TO_ID_NO)
        is FactPlanState.REQUIRED_NIL_TUPLE
    )


def test_according_to_st13_is_nil() -> None:
    assert (
        _state_for_path(
            ACCORDING_TO,
            ACCORDING_TO_ID_NO,
            COMPANY_ST13,
        )
        is FactPlanState.NIL
    )


def test_according_to_bf4_is_nil() -> None:
    assert (
        _state_for_path(
            ACCORDING_TO,
            ACCORDING_TO_ID_NO,
            COMPANY_BF4,
        )
        is FactPlanState.NIL
    )


def test_according_to_year_end_is_nil() -> None:
    assert (
        _state_for(
            "genInfo.report.id.accordingTo.yearEnd"
        )
        is FactPlanState.NIL
    )


def test_domestic_branch_is_required_nil_tuple() -> None:
    assert (
        _state_for(
            "genInfo.company.id.domesticBranchOfForeignCompany"
        )
        is FactPlanState.REQUIRED_NIL_TUPLE
    )


def test_domestic_branch_other_is_nil() -> None:
    assert (
        _state_for(
            "genInfo.company.id."
            "domesticBranchOfForeignCompany.other"
        )
        is FactPlanState.NIL
    )


def test_taxable_purpose_business_is_required_nil_tuple() -> None:
    assert (
        _state_for(
            "genInfo.company.id.entityWithTaxablePurposeBusiness"
        )
        is FactPlanState.REQUIRED_NIL_TUPLE
    )


def test_merchant_vessels_is_nil() -> None:
    assert (
        _state_for(
            "genInfo.company.id."
            "entityWithTaxablePurposeBusiness."
            "merchantVesselsInInternationalTraffic"
        )
        is FactPlanState.NIL
    )


def test_report_element_b_is_value() -> None:
    assert (
        _state_for(
            "genInfo.report.id.reportElement.reportElements.B"
        )
        is FactPlanState.VALUE
    )


def test_report_element_guv_is_value() -> None:
    assert (
        _state_for(
            "genInfo.report.id.reportElement.reportElements.GuV"
        )
        is FactPlanState.VALUE
    )


def test_report_element_bal_is_conditional() -> None:
    assert (
        _state_for(
            "genInfo.report.id.reportElement.reportElements.BAL"
        )
        is FactPlanState.CONDITIONAL
    )


def test_report_element_ks_is_conditional() -> None:
    assert (
        _state_for(
            "genInfo.report.id.reportElement.reportElements.KS"
        )
        is FactPlanState.CONDITIONAL
    )


def test_unused_report_elements_are_nil() -> None:
    for suffix in (
        "EV",
        "BVV",
        "EB",
        "STU",
    ):
        assert (
            _state_for(
                "genInfo.report.id.reportElement."
                f"reportElements.{suffix}"
            )
            is FactPlanState.NIL
        )

    assert (
        _state_for(
            "genInfo.report.id.reportElement."
            "reportElements.transmissionNotYetPossible"
        )
        is FactPlanState.NIL
    )


def test_net_income_is_value() -> None:
    assert (
        _state_for("is.netIncome")
        is FactPlanState.VALUE
    )


def test_earnings_after_taxes_is_value() -> None:
    assert (
        _state_for("is.netIncome.eat")
        is FactPlanState.VALUE
    )


def test_operating_total_cost_is_value() -> None:
    assert (
        _state_for("is.netIncome.regular.operatingTC")
        is FactPlanState.VALUE
    )


def test_gross_trading_profit_is_value() -> None:
    assert (
        _state_for(
            "is.netIncome.regular.operatingTC."
            "grossTradingProfit"
        )
        is FactPlanState.VALUE
    )


def test_balance_sheet_concepts_are_value_or_nil() -> None:
    for concept_name in BALANCE_SHEET_CONCEPTS:
        assert (
            _state_for(concept_name)
            is FactPlanState.VALUE_OR_NIL
        )


def test_profile_contains_expected_top_level_blocks() -> None:
    profile = create_profile_6_9()

    assert tuple(
        node.concept_name
        for node in profile.fact_plan.nodes
    ) == (
        "genInfo.report.id.reportStatus",
        "genInfo.report.id.revisionStatus",
        "genInfo.report.id.statementType",
        "genInfo.report.id.accountingStandard",
        "genInfo.report.id.specialAccountingStandard",
        "genInfo.report.id.incomeStatementFormat",
        "genInfo.report.id.consolidationRange",
        "genInfo.company.id.incomeClassification",
        "genInfo.company.id.legalStatus",
        "genInfo.report.period.reportPeriodBegin",
        "genInfo.report.period.reportPeriodEnd",
        "genInfo.report.period.fiscalYearBegin",
        "genInfo.report.period.fiscalYearEnd",
        "genInfo.report.period.balSheetClosingDate",
        "genInfo.company.id.name",
        "genInfo.company.id.location.street",
        "genInfo.company.id.location.houseNo",
        "genInfo.company.id.location.zipCode",
        "genInfo.company.id.location.city",
        "genInfo.company.id.location.country",
        "genInfo.company.id.location.country.isoCode",
        "genInfo.company.id.idNo",
        "genInfo.report.id.accordingTo",
        "genInfo.company.id.domesticBranchOfForeignCompany",
        "genInfo.company.id.entityWithTaxablePurposeBusiness",
        "genInfo.report.id.reportElement",
        (
            "genInfo.report.id.reportElement."
            "reportElements.transmissionNotYetPossible"
        ),
        "is.netIncome",
        "is.netIncome.eat",
        "is.netIncome.regular.operatingTC",
        (
            "is.netIncome.regular.operatingTC."
            "grossTradingProfit"
        ),
        *BALANCE_SHEET_CONCEPTS,
        *INCOME_STATEMENT_CONCEPTS,
    )

# Analyse: HGB- und E-Bilanz-Taxonomiezuordnungen des SKR04

**Projektstand:** SimpleOB 0.60.0, Arbeitsbaum `main` bei `d966a817ec9e63f32fe6e134210119f4a37fad58`.

## Umfang und belastbare Grenzen

Geprüft wurden die mitgelieferte SKR04-Konten-CSV, deren Konfigurationsdatei und Taxonomie-Mapping-CSV sowie die Import-, Editor-, Persistenz- und E-Bilanz-Codepfade. Die Projektvorlage enthält 248 Konten und 187 explizite Taxonomiezuordnungen. Alle 187 Kontonummern kommen in der Konten-CSV vor und haben mindestens eine HGB-Zuordnung; die Taxonomie-CSV verweist nicht auf ein fehlendes Konto.

Bei der ersten Bestandsaufnahme war Taxonomie 6.9 weder unter `data/taxonomy` noch im Application-Support-Pfad installiert. Inzwischen wurde das im Projektstamm vorhandene Archiv `german-gaap-taxonomy-v6.9-2025-04-01.zip` geprüft und über den bestehenden ZIP-Installer in `~/Library/Application Support/SimpleOB/taxonomy/6.9` installiert. Es ist 53.607.047 Byte groß, hat SHA-256 `4c2572b438e7c1b04119d2c6363bc9b07605ddb1a14731dec10a3a0900d7bfc9`, besteht den ZIP-Integritätstest und enthält genau einen GAAP-CI-Fiscal- sowie einen GCD-Entry-Point.

Die internen Verzeichnis- und Dateinamen weisen auf die Ausgabe vom 1. April 2025 hin. Das BMF-Schreiben veröffentlicht Taxonomie 6.9 vom 1. April 2025 als amtlich vorgeschriebenen Datensatz. Das vollständige Modell ließ sich offline über die SimpleOB-Schnittstelle laden; daher sind die darunterstehenden SKR04-Zuordnungen jetzt gegen die echte Calculation-Linkbase geprüft. Das Archiv selbst wurde nicht verändert.

## Konto 2900

| Feld | Tatsächlicher Vorlagenwert |
|---|---|
| Konto / Name | 2900 / Gezeichnetes Kapital17) |
| Kontotyp | EQUITY |
| HGB-Soll | leer |
| HGB-Haben | HGB.266.PASSIVA.A.I |
| Taxonomie | bs.eqLiab.equity.subscribed.corp |
| Vorlagenversion | 6.9 |
| HGB-Mappingziel im Code | bs.eqLiab.equity.subscribed |
| Calculation-Pfade zum expliziten Concept | genau 1 |
| Ergebnis der E-Bilanz-Validierungsbedingung | gültig |

Die Daten enthalten sowohl die explizite HGB-Zuordnung als auch das explizite Taxonomie-Concept. Im geladenen GAAP-CI-Modell ist `bs.eqLiab.equity.subscribed.corp` vorhanden. Zwischen `HGB.266.PASSIVA.A.I` (abgebildet auf `bs.eqLiab.equity.subscribed`) und diesem Concept besteht genau ein Calculation-Pfad; die E-Bilanz-Prüfung akzeptiert die Zuordnung. Die frühere Anzeige „Bisherige Zuordnung nicht passend“ entstand im damaligen Zustand mit leerem/nicht verfügbarem Modell: Der Dialog übersetzte eine leere Choice-Liste in diese irreführende Meldung. Sie war kein Nachweis eines fehlerhaften SKR04-Mappings.

## Vollständiges Inventar aller SKR04-Taxonomiezuordnungen

Erfasste Mappingzeilen: 187. Die Statusspalte gibt für jede Zuordnung das Ergebnis der vorhandenen E-Bilanz-Prüfbedingung mit dem geladenen GAAP-CI-6.9-Modell wieder.

| Konto | Bezeichnung | Kontotyp | HGB-Soll | HGB-Haben | Taxonomieposition | Kompatibilitätsprüfung |
|---:|---|---|---|---|---|---|
| 0500 | Andere Anlagen, Betriebs- und Geschäftsausstattung | ASSET | HGB.266.AKTIVA.A.II.3 | — | bs.ass.fixAss.tan.otherEquipm.misc | Genau ein gültiger Calculation-Pfad (1) |
| 0520 | Pkw | ASSET | HGB.266.AKTIVA.A.II.3 | — | bs.ass.fixAss.tan.otherEquipm.passengerCars | Genau ein gültiger Calculation-Pfad (1) |
| 0620 | Werkzeuge | ASSET | HGB.266.AKTIVA.A.II.3 | — | bs.ass.fixAss.tan.otherEquipm.factory | Genau ein gültiger Calculation-Pfad (1) |
| 0630 | Betriebsausstattung | ASSET | HGB.266.AKTIVA.A.II.3 | — | bs.ass.fixAss.tan.otherEquipm.factory | Genau ein gültiger Calculation-Pfad (1) |
| 0635 | Geschäftsausstattung | ASSET | HGB.266.AKTIVA.A.II.3 | — | bs.ass.fixAss.tan.otherEquipm.office | Genau ein gültiger Calculation-Pfad (1) |
| 0650 | Büroeinrichtung | ASSET | HGB.266.AKTIVA.A.II.3 | — | bs.ass.fixAss.tan.otherEquipm.office | Genau ein gültiger Calculation-Pfad (1) |
| 0670 | Geringwertige Wirtschaftsgüter | ASSET | HGB.266.AKTIVA.A.II.3 | — | bs.ass.fixAss.tan.otherEquipm.gwg | Genau ein gültiger Calculation-Pfad (1) |
| 0675 | Wirtschaftsgüter (Sammelposten) | ASSET | HGB.266.AKTIVA.A.II.3 | — | bs.ass.fixAss.tan.otherEquipm.gwgsammelposten | Genau ein gültiger Calculation-Pfad (1) |
| 0690 | Sonstige Betriebs- und Geschäftsausstattung | ASSET | HGB.266.AKTIVA.A.II.3 | — | bs.ass.fixAss.tan.otherEquipm.otherbga | Genau ein gültiger Calculation-Pfad (1) |
| 1200 | Forderungen aus Lieferungen und Leistungen | ASSET | HGB.266.AKTIVA.B.II.1 | — | bs.ass.currAss.receiv.trade.other | Genau ein gültiger Calculation-Pfad (1) |
| 1300 | Sonstige Vermögensgegenstände | ASSET | HGB.266.AKTIVA.B.II.4 | — | bs.ass.currAss.receiv.other.misc | Genau ein gültiger Calculation-Pfad (1) |
| 1340 | Forderungen gegen Personal aus Lohn- und Gehaltsabrechnung | ASSET | HGB.266.AKTIVA.B.II.4 | — | bs.ass.currAss.receiv.other.employees | Genau ein gültiger Calculation-Pfad (1) |
| 1350 | Kautionen | ASSET | HGB.266.AKTIVA.B.II.4 | — | bs.ass.currAss.receiv.other.other | Genau ein gültiger Calculation-Pfad (1) |
| 1360 | Darlehen | ASSET | HGB.266.AKTIVA.B.II.4 | — | bs.ass.currAss.receiv.other.other | Genau ein gültiger Calculation-Pfad (1) |
| 1369 | Forderungen gegenüber Krankenkassen aus Aufwendungsausgleichsgesetz | ASSET | HGB.266.AKTIVA.B.II.4 | — | bs.ass.currAss.receiv.other.socInsur | Genau ein gültiger Calculation-Pfad (1) |
| 1378 | Ansprüche aus Rückdeckungsversicherungen | ASSET | HGB.266.AKTIVA.B.II.4 | — | bs.ass.currAss.receiv.other.reInsurClaim | Genau ein gültiger Calculation-Pfad (1) |
| 1400 | Abziehbare Vorsteuer | ASSET | HGB.266.AKTIVA.B.II.4 | — | bs.ass.currAss.receiv.other.vat | Genau ein gültiger Calculation-Pfad (1) |
| 1410 | Aufzuteilende Vorsteuer | ASSET | HGB.266.AKTIVA.B.II.4 | — | bs.ass.currAss.receiv.other.vat | Genau ein gültiger Calculation-Pfad (1) |
| 1411 | Aufzuteilende Vorsteuer 7 % | ASSET | HGB.266.AKTIVA.B.II.4 | — | bs.ass.currAss.receiv.other.vat | Genau ein gültiger Calculation-Pfad (1) |
| 1416 | Aufzuteilende Vorsteuer 19 % | ASSET | HGB.266.AKTIVA.B.II.4 | — | bs.ass.currAss.receiv.other.vat | Genau ein gültiger Calculation-Pfad (1) |
| 1434 | Vorsteuer in Folgeperiode/ im Folgejahr abziehbar | ASSET | HGB.266.AKTIVA.B.II.4 | — | bs.ass.currAss.receiv.other.vat | Genau ein gültiger Calculation-Pfad (1) |
| 1435 | Forderungen aus Gewerbesteuerüberzahlungen | ASSET | HGB.266.AKTIVA.B.II.4 | — | bs.ass.currAss.receiv.other.tradeTaxOverpayment | Genau ein gültiger Calculation-Pfad (1) |
| 1450 | Körperschaftsteuerrückforderung | ASSET | HGB.266.AKTIVA.B.II.4 | — | bs.ass.currAss.receiv.other.corpTaxOverpayment | Genau ein gültiger Calculation-Pfad (1) |
| 2900 | Gezeichnetes Kapital17) | EQUITY | — | HGB.266.PASSIVA.A.I | bs.eqLiab.equity.subscribed.corp | Genau ein gültiger Calculation-Pfad (1) |
| 3035 | Gewerbesteuerrückstellung nach § 4 Abs. 5b EStG | LIABILITY | — | HGB.266.PASSIVA.B.2 | bs.eqLiab.accruals.tax.gewst | Genau ein gültiger Calculation-Pfad (1) |
| 3040 | Körperschaftsteuerrückstellung | LIABILITY | — | HGB.266.PASSIVA.B.2 | bs.eqLiab.accruals.tax.kst | Genau ein gültiger Calculation-Pfad (1) |
| 3300 | Verbindlichkeiten aus Lieferungen und Leistungen | LIABILITY | — | HGB.266.PASSIVA.C.4 | bs.eqLiab.liab.trade.genOther | Genau ein gültiger Calculation-Pfad (1) |
| 3500 | Sonstige Verbindlichkeiten | LIABILITY | — | HGB.266.PASSIVA.C.8 | bs.eqLiab.liab.other.other | Genau ein gültiger Calculation-Pfad (1) |
| 3550 | Erhaltene Kautionen | LIABILITY | — | HGB.266.PASSIVA.C.8 | bs.eqLiab.liab.other.other | Genau ein gültiger Calculation-Pfad (1) |
| 3560 | Darlehen | LIABILITY | — | HGB.266.PASSIVA.C.8 | bs.eqLiab.liab.other.other | Genau ein gültiger Calculation-Pfad (1) |
| 3700 | Verbindlichkeiten aus Steuern und Abgaben | LIABILITY | — | HGB.266.PASSIVA.C.8 | bs.eqLiab.liab.other.theroffTax | Genau ein gültiger Calculation-Pfad (1) |
| 3759 | Voraussichtliche Beitragsschuld gegenüber den Sozialversicherungsträgern | LIABILITY | — | HGB.266.PASSIVA.C.8 | bs.eqLiab.liab.other.thereoffSocSec | Genau ein gültiger Calculation-Pfad (1) |
| 3820 | Umsatzsteuer-Vorauszahlungen | ASSET | HGB.266.AKTIVA.B.II.4 | — | bs.ass.currAss.receiv.other.vat | Genau ein gültiger Calculation-Pfad (1) |
| 4200 | Erlöse | REVENUE | — | HGB.275.GKV.1 | is.netIncome.regular.operatingTC.grossTradingProfit.totalOutput.netSales.grossSales.unknownVAT | Genau ein gültiger Calculation-Pfad (1) |
| 4290 | Erlöse 0 % USt | REVENUE | — | HGB.275.GKV.1 | is.netIncome.regular.operatingTC.grossTradingProfit.totalOutput.netSales.grossSales.0VATrateUStG12_3 | Genau ein gültiger Calculation-Pfad (1) |
| 4300 | Erlöse 7 % USt | REVENUE | — | HGB.275.GKV.1 | is.netIncome.regular.operatingTC.grossTradingProfit.totalOutput.netSales.grossSales.reducedRateVAT | Genau ein gültiger Calculation-Pfad (1) |
| 4449 | Erlöse aus im Inland steuerpflichtigen elektronischen Dienstleistungen 19 % USt | REVENUE | — | HGB.275.GKV.1 | is.netIncome.regular.operatingTC.grossTradingProfit.totalOutput.netSales.grossSales.generalRateVAT | Genau ein gültiger Calculation-Pfad (1) |
| 4499 | Nebenerlöse (Bezug zu Materialaufwand) | REVENUE | — | HGB.275.GKV.1 | is.netIncome.regular.operatingTC.grossTradingProfit.totalOutput.netSales.grossSales.unknownVAT | Genau ein gültiger Calculation-Pfad (1) |
| 4560 | Provisionsumsätze | REVENUE | — | HGB.275.GKV.1 | is.netIncome.regular.operatingTC.grossTradingProfit.totalOutput.netSales.grossSales.unknownVAT | Genau ein gültiger Calculation-Pfad (1) |
| 4700 | Erlösschmälerungen | REVENUE | HGB.275.GKV.1 | — | is.netIncome.regular.operatingTC.grossTradingProfit.totalOutput.netSales.reductionsFromGrossSales.unknownVAT | Genau ein gültiger Calculation-Pfad (1) |
| 4710 | Erlösschmälerungen 7 % USt | REVENUE | HGB.275.GKV.1 | — | is.netIncome.regular.operatingTC.grossTradingProfit.totalOutput.netSales.reductionsFromGrossSales.reducedRateVAT | Genau ein gültiger Calculation-Pfad (1) |
| 4719 | Erlösschmälerungen 0 % USt | REVENUE | HGB.275.GKV.1 | — | is.netIncome.regular.operatingTC.grossTradingProfit.totalOutput.netSales.reductionsFromGrossSales.0VATrateUStG12_3 | Genau ein gültiger Calculation-Pfad (1) |
| 4720 | Erlösschmälerungen 19 % USt | REVENUE | HGB.275.GKV.1 | — | is.netIncome.regular.operatingTC.grossTradingProfit.totalOutput.netSales.reductionsFromGrossSales.generalRateVAT | Genau ein gültiger Calculation-Pfad (1) |
| 4830 | Sonstige betriebliche Erträge | REVENUE | — | HGB.275.GKV.4 | is.netIncome.regular.operatingTC.otherOpRevenue.miscellaneous | Genau ein gültiger Calculation-Pfad (1) |
| 4833 | Andere Nebenerlöse | REVENUE | — | HGB.275.GKV.1 | is.netIncome.regular.operatingTC.grossTradingProfit.totalOutput.netSales.grossSales.unknownVAT | Genau ein gültiger Calculation-Pfad (1) |
| 4835 | Sonstige Erträge betrieblich und regelmäßig | REVENUE | — | HGB.275.GKV.4 | is.netIncome.regular.operatingTC.otherOpRevenue.miscellaneous | Genau ein gültiger Calculation-Pfad (1) |
| 4836 | Sonstige Erträge betrieblich und regelmäßig 19 % USt | REVENUE | — | HGB.275.GKV.4 | is.netIncome.regular.operatingTC.otherOpRevenue.miscellaneous | Genau ein gültiger Calculation-Pfad (1) |
| 4838 | Erstattete Vorsteuer anderer Länder | REVENUE | — | HGB.275.GKV.4 | is.netIncome.regular.operatingTC.otherOpRevenue.miscellaneous | Genau ein gültiger Calculation-Pfad (1) |
| 4839 | Sonstige Erträge unregelmäßig | REVENUE | — | HGB.275.GKV.4 | is.netIncome.regular.operatingTC.otherOpRevenue.miscellaneous | Genau ein gültiger Calculation-Pfad (1) |
| 4845 | Erlöse aus Verkäufen Sachanlagevermögen 19 % USt (bei Buchgewinn) | REVENUE | — | HGB.275.GKV.4 | is.netIncome.regular.operatingTC.otherOpRevenue.disposFixAss.sale.tan | Genau ein gültiger Calculation-Pfad (1) |
| 4849 | Erlöse aus Verkäufen Sachanlagevermögen (bei Buchgewinn) | REVENUE | — | HGB.275.GKV.4 | is.netIncome.regular.operatingTC.otherOpRevenue.disposFixAss.sale.tan | Genau ein gültiger Calculation-Pfad (1) |
| 4850 | Erlöse aus Verkäufen immaterieller Vermögensgegenstände (bei Buchgewinn) | REVENUE | — | HGB.275.GKV.4 | is.netIncome.regular.operatingTC.otherOpRevenue.disposFixAss.sale.intan | Genau ein gültiger Calculation-Pfad (1) |
| 4856 | Anlagenabgänge immaterielle Vermögensgegenstände (Restbuchwert bei Buchgewinn) | EXPENSE | HGB.275.GKV.4 | — | is.netIncome.regular.operatingTC.otherOpRevenue.disposFixAss.bookValue.intan | Genau ein gültiger Calculation-Pfad (1) |
| 4862 | Erlöse aus Vermietung und Verpachtung 19 % USt | REVENUE | — | HGB.275.GKV.1 | is.netIncome.regular.operatingTC.grossTradingProfit.totalOutput.netSales.grossSales.generalRateVAT | Genau ein gültiger Calculation-Pfad (1) |
| 4930 | Erträge aus der Auflösung von Rückstellungen | REVENUE | — | HGB.275.GKV.4 | is.netIncome.regular.operatingTC.otherOpRevenue.releaseProv | Genau ein gültiger Calculation-Pfad (1) |
| 4970 | Versicherungsentschädigungen und Schadenersatzleistungen | REVENUE | — | HGB.275.GKV.4 | is.netIncome.regular.operatingTC.otherOpRevenue.insuranceRefunds | Genau ein gültiger Calculation-Pfad (1) |
| 4972 | Erstattungen Aufwendungsausgleichsgesetz | REVENUE | — | HGB.275.GKV.4 | is.netIncome.regular.operatingTC.otherOpRevenue.insuranceRefunds | Genau ein gültiger Calculation-Pfad (1) |
| 5100 | Einkauf Roh-, Hilfs- und Betriebsstoffe | EXPENSE | HGB.275.GKV.5.a | — | is.netIncome.regular.operatingTC.grossTradingProfit.materialServices.material.rawMatConsSup.unknownVAT | Genau ein gültiger Calculation-Pfad (1) |
| 5110 | Einkauf Roh-, Hilfs- und Betriebsstoffe 7 % Vorsteuer | EXPENSE | HGB.275.GKV.5.a | — | is.netIncome.regular.operatingTC.grossTradingProfit.materialServices.material.rawMatConsSup.reducedRateVAT | Genau ein gültiger Calculation-Pfad (1) |
| 5129 | Einkauf Roh-, Hilfs- und Betriebsstoffe ohne Vorsteuerabzug | EXPENSE | HGB.275.GKV.5.a | — | is.netIncome.regular.operatingTC.grossTradingProfit.materialServices.material.rawMatConsSup.noDeductVAT | Genau ein gültiger Calculation-Pfad (1) |
| 5130 | Einkauf Roh-, Hilfs- und Betriebsstoffe 19 % Vorsteuer | EXPENSE | HGB.275.GKV.5.a | — | is.netIncome.regular.operatingTC.grossTradingProfit.materialServices.material.rawMatConsSup.generalRateVAT | Genau ein gültiger Calculation-Pfad (1) |
| 5171 | Einkauf Roh-, Hilfs- und Betriebsstoffe 7,8 % Vorsteuer8) | EXPENSE | HGB.275.GKV.5.a | — | is.netIncome.regular.operatingTC.grossTradingProfit.materialServices.material.rawMatConsSup.unknownVAT | Genau ein gültiger Calculation-Pfad (1) |
| 5191 | Energiestoffe (Fertigung) 7 % Vorsteuer | EXPENSE | HGB.275.GKV.5.a | — | is.netIncome.regular.operatingTC.grossTradingProfit.materialServices.material.rawMatConsSup.reducedRateVAT | Genau ein gültiger Calculation-Pfad (1) |
| 5192 | Energiestoffe (Fertigung) 19 % Vorsteuer | EXPENSE | HGB.275.GKV.5.a | — | is.netIncome.regular.operatingTC.grossTradingProfit.materialServices.material.rawMatConsSup.generalRateVAT | Genau ein gültiger Calculation-Pfad (1) |
| 5200 | Wareneingang | EXPENSE | HGB.275.GKV.5.a | — | is.netIncome.regular.operatingTC.grossTradingProfit.materialServices.material.purchased.unknownVAT | Genau ein gültiger Calculation-Pfad (1) |
| 5300 | Wareneingang 7 % Vorsteuer | EXPENSE | HGB.275.GKV.5.a | — | is.netIncome.regular.operatingTC.grossTradingProfit.materialServices.material.purchased.reducedRateVAT | Genau ein gültiger Calculation-Pfad (1) |
| 5349 | Wareneingang ohne Vorsteuerabzug | EXPENSE | HGB.275.GKV.5.a | — | is.netIncome.regular.operatingTC.grossTradingProfit.materialServices.material.purchased.withoutVAT | Genau ein gültiger Calculation-Pfad (1) |
| 5400 | Wareneingang 19 % Vorsteuer | EXPENSE | HGB.275.GKV.5.a | — | is.netIncome.regular.operatingTC.grossTradingProfit.materialServices.material.purchased.generalRateVAT | Genau ein gültiger Calculation-Pfad (1) |
| 5600 | Nicht abziehbare Vorsteuer | EXPENSE | HGB.275.GKV.5.a | — | is.netIncome.regular.operatingTC.grossTradingProfit.materialServices.material.purchased.unknownVAT | Genau ein gültiger Calculation-Pfad (1) |
| 5800 | Bezugsnebenkosten | EXPENSE | HGB.275.GKV.5.a | — | is.netIncome.regular.operatingTC.grossTradingProfit.materialServices.material.purchased.unknownVAT | Genau ein gültiger Calculation-Pfad (1) |
| 5900 | Fremdleistungen | EXPENSE | HGB.275.GKV.5.b | — | is.netIncome.regular.operatingTC.grossTradingProfit.materialServices.services.unknownVAT | Genau ein gültiger Calculation-Pfad (1) |
| 5906 | Fremdleistungen 19 % Vorsteuer | EXPENSE | HGB.275.GKV.5.b | — | is.netIncome.regular.operatingTC.grossTradingProfit.materialServices.services.OtherDedInputTax | Genau ein gültiger Calculation-Pfad (1) |
| 5908 | Fremdleistungen 7 % Vorsteuer | EXPENSE | HGB.275.GKV.5.b | — | is.netIncome.regular.operatingTC.grossTradingProfit.materialServices.services.OtherDedInputTax | Genau ein gültiger Calculation-Pfad (1) |
| 5909 | Fremdleistungen ohne Vorsteuer | EXPENSE | HGB.275.GKV.5.b | — | is.netIncome.regular.operatingTC.grossTradingProfit.materialServices.services.OtherNonDedInputTax | Genau ein gültiger Calculation-Pfad (1) |
| 5970 | Fremdleistungen (Miet- und Pachtzinsen bewegliche Wirtschaftsgüter) | EXPENSE | HGB.275.GKV.5.b | — | is.netIncome.regular.operatingTC.grossTradingProfit.materialServices.services.unknownVAT | Genau ein gültiger Calculation-Pfad (1) |
| 5975 | Fremdleistungen (Miet- und Pachtzinsen unbewegliche Wirtschaftsgüter) | EXPENSE | HGB.275.GKV.5.b | — | is.netIncome.regular.operatingTC.grossTradingProfit.materialServices.services.unknownVAT | Genau ein gültiger Calculation-Pfad (1) |
| 5980 | Fremdleistungen (Entgelte für Rechte und Lizenzen) | EXPENSE | HGB.275.GKV.5.b | — | is.netIncome.regular.operatingTC.grossTradingProfit.materialServices.services.unknownVAT | Genau ein gültiger Calculation-Pfad (1) |
| 6000 | Löhne und Gehälter | EXPENSE | HGB.275.GKV.6.a | — | is.netIncome.regular.operatingTC.staff.salaries.misc | Genau ein gültiger Calculation-Pfad (1) |
| 6010 | Löhne | EXPENSE | HGB.275.GKV.6.a | — | is.netIncome.regular.operatingTC.staff.salaries.misc | Genau ein gültiger Calculation-Pfad (1) |
| 6027 | Geschäftsführergehälter | EXPENSE | HGB.275.GKV.6.a | — | is.netIncome.regular.operatingTC.staff.salaries.misc | Genau ein gültiger Calculation-Pfad (1) |
| 6030 | Aushilfslöhne | EXPENSE | HGB.275.GKV.6.a | — | is.netIncome.regular.operatingTC.staff.salaries.misc | Genau ein gültiger Calculation-Pfad (1) |
| 6035 | Löhne für Minijobs | EXPENSE | HGB.275.GKV.6.a | — | is.netIncome.regular.operatingTC.staff.salaries.minijobs | Genau ein gültiger Calculation-Pfad (1) |
| 6060 | Freiwillige soziale Aufwendungen, lohnsteuerpflichtig | EXPENSE | HGB.275.GKV.6.a | — | is.netIncome.regular.operatingTC.staff.salaries.voluntayBenefits | Genau ein gültiger Calculation-Pfad (1) |
| 6076 | Aufwendungen aus der Veränderung von Urlaubsrückstellungen | EXPENSE | HGB.275.GKV.6.a | — | is.netIncome.regular.operatingTC.staff.salaries.misc | Genau ein gültiger Calculation-Pfad (1) |
| 6079 | Aufwendungen aus der Veränderung von Urlaubsrückstellungen für Minijobber | EXPENSE | HGB.275.GKV.6.a | — | is.netIncome.regular.operatingTC.staff.salaries.minijobs | Genau ein gültiger Calculation-Pfad (1) |
| 6100 | Soziale Abgaben und Aufwendungen für Altersversorgung und für Unterstützung | EXPENSE | HGB.275.GKV.6.b | — | is.netIncome.regular.operatingTC.staff.social.other | Genau ein gültiger Calculation-Pfad (1) |
| 6110 | Gesetzliche soziale Aufwendungen | EXPENSE | HGB.275.GKV.6.b | — | is.netIncome.regular.operatingTC.staff.social.socExp.other | Genau ein gültiger Calculation-Pfad (1) |
| 6120 | Beiträge zur Berufsgenossenschaft | EXPENSE | HGB.275.GKV.6.b | — | is.netIncome.regular.operatingTC.staff.social.socExp.other | Genau ein gültiger Calculation-Pfad (1) |
| 6140 | Aufwendungen für Altersversorgung | EXPENSE | HGB.275.GKV.6.b | — | is.netIncome.regular.operatingTC.staff.social.pensions.other | Genau ein gültiger Calculation-Pfad (1) |
| 6147 | Pauschale Steuer auf sonstige Bezüge (z. B. Direktversicherungen) | EXPENSE | HGB.275.GKV.6.b | — | is.netIncome.regular.operatingTC.staff.social.pensions.other | Genau ein gültiger Calculation-Pfad (1) |
| 6150 | Versorgungskassen | EXPENSE | HGB.275.GKV.6.b | — | is.netIncome.regular.operatingTC.staff.social.pensions.other | Genau ein gültiger Calculation-Pfad (1) |
| 6170 | Sonstige soziale Abgaben | EXPENSE | HGB.275.GKV.6.b | — | is.netIncome.regular.operatingTC.staff.social.socExp.other | Genau ein gültiger Calculation-Pfad (1) |
| 6171 | Soziale Abgaben für Minijobber | EXPENSE | HGB.275.GKV.6.b | — | is.netIncome.regular.operatingTC.staff.social.socExp.other | Genau ein gültiger Calculation-Pfad (1) |
| 6200 | Abschreibungen auf immaterielle Vermögensgegenstände | EXPENSE | HGB.275.GKV.7.a | — | is.netIncome.regular.operatingTC.deprAmort.fixAss.otherIntan | Genau ein gültiger Calculation-Pfad (1) |
| 6201 | Abschreibungen auf selbst geschaffene immaterielle Vermögensgegenstände | EXPENSE | HGB.275.GKV.7.a | — | is.netIncome.regular.operatingTC.deprAmort.fixAss.otherIntan | Genau ein gültiger Calculation-Pfad (1) |
| 6205 | Abschreibungen auf den Geschäfts- oder Firmenwert | EXPENSE | HGB.275.GKV.7.a | — | is.netIncome.regular.operatingTC.deprAmort.fixAss.goodwill | Genau ein gültiger Calculation-Pfad (1) |
| 6220 | Abschreibungen auf Sachanlagen (ohne AfA auf Fahrzeuge und Gebäude) | EXPENSE | HGB.275.GKV.7.a | — | is.netIncome.regular.operatingTC.deprAmort.fixAss.tan.otherMisc | Genau ein gültiger Calculation-Pfad (1) |
| 6222 | Abschreibungen auf Fahrzeuge | EXPENSE | HGB.275.GKV.7.a | — | is.netIncome.regular.operatingTC.deprAmort.fixAss.tan.other | Genau ein gültiger Calculation-Pfad (1) |
| 6232 | Absetzung für außergewöhnliche technische und wirtschaftliche Abnutzung der Fahrzeuge | EXPENSE | HGB.275.GKV.7.a | — | is.netIncome.regular.operatingTC.deprAmort.fixAss.specific.except.tan | Genau ein gültiger Calculation-Pfad (1) |
| 6240 | Abschreibungen auf Sachanlagen auf Grund steuerlicher Sondervorschriften | EXPENSE | HGB.275.GKV.7.a | — | is.netIncome.regular.operatingTC.deprAmort.fixAss.specific.impairment | Genau ein gültiger Calculation-Pfad (1) |
| 6260 | Sofortabschreibung geringwertiger Wirtschaftsgüter | EXPENSE | HGB.275.GKV.7.a | — | is.netIncome.regular.operatingTC.deprAmort.fixAss.tan.lowValueAs | Genau ein gültiger Calculation-Pfad (1) |
| 6262 | Abschreibungen auf aktivierte, geringwertige Wirtschaftsgüter | EXPENSE | HGB.275.GKV.7.a | — | is.netIncome.regular.operatingTC.deprAmort.fixAss.tan.other | Genau ein gültiger Calculation-Pfad (1) |
| 6264 | Abschreibungen auf den Sammelposten Wirtschaftsgüter | EXPENSE | HGB.275.GKV.7.a | — | is.netIncome.regular.operatingTC.deprAmort.fixAss.tan.lowValueAsCollItem | Genau ein gültiger Calculation-Pfad (1) |
| 6270 | Abschreibungen auf sonstige Vermögensgegenstände des Umlaufvermögens (soweit unüblich hoch) | EXPENSE | HGB.275.GKV.7.b | — | is.netIncome.regular.operatingTC.deprAmort.currAss.receiv.other | Genau ein gültiger Calculation-Pfad (1) |
| 6272 | Abschreibungen auf Umlaufvermögen, steuerrechtlich bedingt (soweit unüblich hoch) | EXPENSE | HGB.275.GKV.7.b | — | is.netIncome.regular.operatingTC.deprAmort.currAss.misc | Genau ein gültiger Calculation-Pfad (1) |
| 6278 | Abschreibungen auf Roh-, Hilfs- und Betriebsstoffe/Waren (soweit unüblich hoch) | EXPENSE | HGB.275.GKV.7.b | — | is.netIncome.regular.operatingTC.deprAmort.currAss.inventory | Genau ein gültiger Calculation-Pfad (1) |
| 6279 | Abschreibungen auf fertige und unfertige Erzeugnisse (soweit unüblich hoch) | EXPENSE | HGB.275.GKV.7.b | — | is.netIncome.regular.operatingTC.deprAmort.currAss.inventory | Genau ein gültiger Calculation-Pfad (1) |
| 6281 | Forderungsverluste 7 % USt (soweit unüblich hoch) | EXPENSE | HGB.275.GKV.7.b | — | is.netIncome.regular.operatingTC.deprAmort.currAss.receiv.other | Genau ein gültiger Calculation-Pfad (1) |
| 6286 | Forderungsverluste 19 % USt (soweit unüblich hoch) | EXPENSE | HGB.275.GKV.7.b | — | is.netIncome.regular.operatingTC.deprAmort.currAss.receiv.other | Genau ein gültiger Calculation-Pfad (1) |
| 6300 | Sonstige betriebliche Aufwendungen | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.miscellaneous | Genau ein gültiger Calculation-Pfad (1) |
| 6303 | Fremdleistungen/Fremdarbeiten | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.otherOrdinary | Genau ein gültiger Calculation-Pfad (1) |
| 6305 | Raumkosten | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.otherOrdinary | Genau ein gültiger Calculation-Pfad (1) |
| 6310 | Miete (unbewegliche Wirtschaftsgüter) | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.leaseFix.other | Genau ein gültiger Calculation-Pfad (1) |
| 6316 | Pacht (unbewegliche Wirtschaftsgüter) | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.leasingAll.immovable | Genau ein gültiger Calculation-Pfad (1) |
| 6318 | Aufwendungen für gemietete oder gepachtete unbewegliche Wirtschaftsgüter, die gewerbesteuerlich hinzuzurechnen sind | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.leaseFix.other | Genau ein gültiger Calculation-Pfad (1) |
| 6325 | Gas, Strom, Wasser | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.energyCost | Genau ein gültiger Calculation-Pfad (1) |
| 6330 | Reinigung | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.otherOrdinary | Genau ein gültiger Calculation-Pfad (1) |
| 6335 | Instandhaltung betrieblicher Räume | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.fixingLandBuildings | Genau ein gültiger Calculation-Pfad (1) |
| 6345 | Sonstige Raumkosten | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.otherOrdinary | Genau ein gültiger Calculation-Pfad (1) |
| 6400 | Versicherungen | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.insurance | Genau ein gültiger Calculation-Pfad (1) |
| 6420 | Beiträge | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.insurance | Genau ein gültiger Calculation-Pfad (1) |
| 6436 | Steuerlich abzugsfähige Verspätungszuschläge und Zwangsgelder | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.limitedDeductible.other | Genau ein gültiger Calculation-Pfad (1) |
| 6437 | Steuerlich nicht abzugsfähige Verspätungszuschläge und Zwangsgelder | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.limitedDeductible.other | Genau ein gültiger Calculation-Pfad (1) |
| 6460 | Reparaturen und Instandhaltung von technischen Anlagen und Maschinen | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.fixing | Genau ein gültiger Calculation-Pfad (1) |
| 6470 | Reparaturen und Instandhaltungen von anderen Anlagen und Betriebs- und Geschäftsausstattung | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.fixing | Genau ein gültiger Calculation-Pfad (1) |
| 6475 | Zuführung zu Aufwandsrückstellungen | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.provisions | Genau ein gültiger Calculation-Pfad (1) |
| 6485 | Reparaturen und Instandhaltung von anderen Anlagen | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.fixing | Genau ein gültiger Calculation-Pfad (1) |
| 6490 | Sonstige Reparaturen und Instandhaltungen | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.fixing | Genau ein gültiger Calculation-Pfad (1) |
| 6495 | Wartungskosten für Hard- und Software | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.fixing | Genau ein gültiger Calculation-Pfad (1) |
| 6498 | Mietleasing bewegliche Wirtschaftsgüter für technische Anlagen und Maschinen | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.leasingAll.moveable | Genau ein gültiger Calculation-Pfad (1) |
| 6500 | Fahrzeugkosten18) | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.vehicles | Genau ein gültiger Calculation-Pfad (1) |
| 6520 | Fahrzeug-Versicherungen | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.vehicles | Genau ein gültiger Calculation-Pfad (1) |
| 6530 | Laufende Fahrzeug-Betriebskosten | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.vehicles | Genau ein gültiger Calculation-Pfad (1) |
| 6540 | Fahrzeug-Reparaturen | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.vehicles | Genau ein gültiger Calculation-Pfad (1) |
| 6550 | Garagenmiete | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.vehicles | Genau ein gültiger Calculation-Pfad (1) |
| 6600 | Werbekosten | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.marketing | Genau ein gültiger Calculation-Pfad (1) |
| 6640 | Bewirtungskosten | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.limitedDeductible.entertainment.deductible | Genau ein gültiger Calculation-Pfad (1) |
| 6644 | Nicht abzugsfähige Bewirtungskosten | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.limitedDeductible.entertainment.nonDeductible | Genau ein gültiger Calculation-Pfad (1) |
| 6650 | Reisekosten Arbeitnehmer | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.employee | Genau ein gültiger Calculation-Pfad (1) |
| 6660 | Reisekosten Arbeitnehmer Übernachtungsaufwand | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.employee | Genau ein gültiger Calculation-Pfad (1) |
| 6663 | Reisekosten Arbeitnehmer Fahrtkosten | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.employee | Genau ein gültiger Calculation-Pfad (1) |
| 6664 | Reisekosten Arbeitnehmer Verpflegungsmehraufwand | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.employee | Genau ein gültiger Calculation-Pfad (1) |
| 6668 | Kilometergelderstattung Arbeitnehmer | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.employee | Genau ein gültiger Calculation-Pfad (1) |
| 6700 | Kosten der Warenabgabe | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.freight | Genau ein gültiger Calculation-Pfad (1) |
| 6760 | Transportversicherungen | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.freight | Genau ein gültiger Calculation-Pfad (1) |
| 6790 | Aufwand für Gewährleistungen | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.otherOrdinary | Genau ein gültiger Calculation-Pfad (1) |
| 6800 | Porto | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.communication | Genau ein gültiger Calculation-Pfad (1) |
| 6805 | Telefon | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.communication | Genau ein gültiger Calculation-Pfad (1) |
| 6810 | Internetkosten | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.communication | Genau ein gültiger Calculation-Pfad (1) |
| 6815 | Bürobedarf | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.otherOrdinary | Genau ein gültiger Calculation-Pfad (1) |
| 6820 | Zeitschriften, Bücher, digitale Medien (Fachliteratur) | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.training | Genau ein gültiger Calculation-Pfad (1) |
| 6821 | Fortbildungskosten | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.training | Genau ein gültiger Calculation-Pfad (1) |
| 6822 | Freiwillige Sozialleistungen | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.staffRelated | Genau ein gültiger Calculation-Pfad (1) |
| 6825 | Rechts- und Beratungskosten | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.legalConsulting | Genau ein gültiger Calculation-Pfad (1) |
| 6827 | Abschluss- und Prüfungskosten | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.legalConsulting | Genau ein gültiger Calculation-Pfad (1) |
| 6830 | Buchführungskosten | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.legalConsulting | Genau ein gültiger Calculation-Pfad (1) |
| 6835 | Mieten für Einrichtungen (bewegliche Wirtschaftsgüter) | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.leaseMoveable.other | Genau ein gültiger Calculation-Pfad (1) |
| 6836 | Pacht (bewegliche Wirtschaftsgüter) | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.leaseMoveable.other | Genau ein gültiger Calculation-Pfad (1) |
| 6838 | Aufwendungen für gemietete oder gepachtete bewegliche Wirtschaftsgüter, die gewerbesteuerlich hinzuzurechnen sind | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.leaseMoveable.other | Genau ein gültiger Calculation-Pfad (1) |
| 6840 | Mietleasing bewegliche Wirtschaftsgüter für Betriebs- und Geschäftsausstattung | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.leasingAll.moveable | Genau ein gültiger Calculation-Pfad (1) |
| 6845 | Werkzeuge und Kleingeräte | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.otherOrdinary | Genau ein gültiger Calculation-Pfad (1) |
| 6850 | Sonstiger Betriebsbedarf | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.otherOrdinary | Genau ein gültiger Calculation-Pfad (1) |
| 6855 | Nebenkosten des Geldverkehrs | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.otherOrdinary | Genau ein gültiger Calculation-Pfad (1) |
| 6860 | Nicht abziehbare Vorsteuer | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.otherTaxes | Genau ein gültiger Calculation-Pfad (1) |
| 6885 | Erlöse aus Verkäufen Sachanlagevermögen 19 % USt (bei Buchverlust) | REVENUE | — | HGB.275.GKV.8 | is.netIncome.regular.operatingTC.otherCost.disposFixAss.sale.tan | Genau ein gültiger Calculation-Pfad (1) |
| 6889 | Erlöse aus Verkäufen Sachanlagevermögen (bei Buchverlust) | REVENUE | — | HGB.275.GKV.8 | is.netIncome.regular.operatingTC.otherCost.disposFixAss.sale.tan | Genau ein gültiger Calculation-Pfad (1) |
| 6890 | Erlöse aus Verkäufen immaterieller Vermögensgegenstände (bei Buchverlust) | REVENUE | — | HGB.275.GKV.8 | is.netIncome.regular.operatingTC.otherCost.disposFixAss.sale.intan | Genau ein gültiger Calculation-Pfad (1) |
| 6895 | Anlagenabgänge Sachanlagen (Restbuchwert bei Buchverlust) | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.disposFixAss.bookValue.tan | Genau ein gültiger Calculation-Pfad (1) |
| 6896 | Anlagenabgänge immaterielle Vermögensgegenstände (Restbuchwert bei Buchverlust) | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.disposFixAss.bookValue.intan | Genau ein gültiger Calculation-Pfad (1) |
| 6930 | Forderungsverluste (übliche Höhe) | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.regAllowance | Genau ein gültiger Calculation-Pfad (1) |
| 6931 | Forderungsverluste 7 % USt (übliche Höhe) | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.regAllowance | Genau ein gültiger Calculation-Pfad (1) |
| 6936 | Forderungsverluste 19 % USt (übliche Höhe) | EXPENSE | HGB.275.GKV.8 | — | is.netIncome.regular.operatingTC.otherCost.regAllowance | Genau ein gültiger Calculation-Pfad (1) |
| 7011 | Erträge aus Ausleihungen des Finanzanlagevermögens | REVENUE | — | HGB.275.GKV.10 | is.netIncome.regular.fin.netParticipation.earningSecurities.shareholder | Genau ein gültiger Calculation-Pfad (1) |
| 7100 | Sonstige Zinsen und ähnliche Erträge | REVENUE | — | HGB.275.GKV.11 | is.netIncome.regular.fin.netInterest.income.deposits.otherMisc | Genau ein gültiger Calculation-Pfad (1) |
| 7142 | Zinserträge aus der Abzinsung von Rückstellungen | REVENUE | — | HGB.275.GKV.11 | is.netIncome.regular.fin.netInterest.income.valueDiscount | Genau ein gültiger Calculation-Pfad (1) |
| 7300 | Zinsen und ähnliche Aufwendungen | EXPENSE | HGB.275.GKV.13 | — | is.netIncome.regular.fin.netInterest.expenses.regularInterest.other | Genau ein gültiger Calculation-Pfad (1) |
| 7318 | Zinsen auf Kontokorrentkonten | EXPENSE | HGB.275.GKV.13 | — | is.netIncome.regular.fin.netInterest.expenses.regularInterest.other | Genau ein gültiger Calculation-Pfad (1) |
| 7323 | Abschreibungen auf ein Agio oder Disagio/Damnum zur Finanzierung | EXPENSE | HGB.275.GKV.13 | — | is.netIncome.regular.fin.netInterest.expenses.amortDiscount | Genau ein gültiger Calculation-Pfad (1) |
| 7324 | Abschreibungen auf ein Agio oder Disagio/Damnum zur Finanzierung des Anlagevermögens | EXPENSE | HGB.275.GKV.13 | — | is.netIncome.regular.fin.netInterest.expenses.amortDiscount | Genau ein gültiger Calculation-Pfad (1) |
| 7326 | Zinsen zur Finanzierung des Anlagevermögens | EXPENSE | HGB.275.GKV.13 | — | is.netIncome.regular.fin.netInterest.expenses.regularInterest.misc | Genau ein gültiger Calculation-Pfad (1) |
| 7362 | Zinsaufwendungen aus der Abzinsung von Rückstellungen | EXPENSE | HGB.275.GKV.13 | — | is.netIncome.regular.fin.netInterest.expenses.valueDiscount | Genau ein gültiger Calculation-Pfad (1) |
| 7600 | Körperschaftsteuer | EXPENSE | HGB.275.GKV.14 | — | is.netIncome.tax.kst | Genau ein gültiger Calculation-Pfad (1) |
| 7608 | Solidaritätszuschlag | EXPENSE | HGB.275.GKV.14 | — | is.netIncome.tax.soli | Genau ein gültiger Calculation-Pfad (1) |
| 7610 | Gewerbesteuer | EXPENSE | HGB.275.GKV.14 | — | is.netIncome.tax.gewst | Genau ein gültiger Calculation-Pfad (1) |
| 7643 | Erträge aus der Auflösung von Gewerbesteuerrückstellungen nach § 4 Abs. 5b EStG | REVENUE | — | HGB.275.GKV.14 | is.netIncome.tax.releaseTaxProv | Genau ein gültiger Calculation-Pfad (1) |
| 7646 | Aufwendungen aus der Zuführung zu Steuerrückstellungen für Steuerstundung (BStBK) | EXPENSE | HGB.275.GKV.14 | — | is.netIncome.tax.otherIncomeTaxes | Genau ein gültiger Calculation-Pfad (1) |
| 7648 | Erträge aus der Auflösung von Steuerrückstellungen für Steuerstundung (BStBK) | REVENUE | — | HGB.275.GKV.14 | is.netIncome.tax.releaseTaxProv | Genau ein gültiger Calculation-Pfad (1) |

## Ergebnis der Daten-Vollständigkeitsprüfung

- Konten in SKR04-Datei: 248.
- Taxonomiezuordnungen: 187.
- Taxonomiezeilen ohne Konto in der SKR04-Datei: 0.
- Taxonomiezeilen ohne HGB-Soll- und Haben-Zuordnung: 0.
- Taxonomiezeilen mit zwei unterschiedlichen HGB-Seitenpositionen: 0.
- Kontentypverteilung der explizit gemappten Konten: ASSET 24, EQUITY 1, EXPENSE 123, LIABILITY 8, REVENUE 31.

Zusätzlich wurden die 187 Concepts im tatsächlich geladenen Modell jeweils gegen ihr HGB-Mapping geprüft: **187** haben genau einen Calculation-Pfad; **0** haben keinen Pfad; **0** haben mehrere Pfade; **0** sind im Modell unbekannt; **0** endeten mit einem sonstigen technischen Fehler. Damit gibt es keine abweichenden Konten zu dokumentieren.

## Datenfluss und Validierung

1. **Vorlagenquelle:** `skr04_2026_kapitalgesellschaften.config.json` nennt Taxonomieversion `6.9` und die separate Mappingdatei. Der Bundle-Importer lädt Konten und HGB-Seiten aus der Konten-CSV, Taxonomie-Concept-Namen aus der separaten CSV und prüft, dass jede Taxonomiezeile eine vorhandene Kontonummer hat. Er prüft nicht, ob das Concept im XBRL-Modell existiert oder Calculation-Nachfolger der HGB-Position ist.
2. **Neuanlage:** Der Vorlageneditor hält Änderungen in einem Bundle im Arbeitsspeicher. Bei der Mandantenanlage werden `bundle.taxonomy_mappings` und `bundle.taxonomy_version` an `ChartOfAccountsInitializationService` übergeben.
3. **Speicherung:** Die Tabelle `konten_taxonomie_zuordnungen` speichert `mandant_id`, Kontonummer, Taxonomieversion und Concept-Name. HGB-Zuordnungen liegen getrennt als Soll-/Haben-Codes an der Kontozeile.
4. **Laden:** `FiscalYearWorkspace.load_account_taxonomy_concepts()` fragt fest die Version `6.9` ab. Der Hauptfenster-Kontentab zeigt diese gespeicherte Zuordnung separat an. Beim Öffnen des Kontobearbeitungsdialogs im Template-Modus wird derselbe Concept-Name als bestehende Auswahl übergeben.
5. **Choice-Ermittlung:** Die HGB-Position wird auf ein GAAP-CI-Parent-Concept abgebildet. Die Choice-Liste enthält alle Concept-Namen, die über Calculation-Beziehungen von diesem Parent erreichbar sind.
6. **Warnung:** Im Template-Kontodialog wird die vorhandene Concept-Zeichenfolge mit den Namen dieser Choice-Liste verglichen. Ist sie nicht enthalten, erscheint „Bisherige Zuordnung nicht passend“. Dieser Zweig wird auch dann betreten, wenn ein vorheriger Providerfehler die Choice-Liste leer gelassen hat.
7. **Speichern:** Im Template-Editor ist ein als `unavailable` markiertes bestehendes Concept nicht speicherbar; `_save()` verlangt eine neue gültige Auswahl oder die ausdrückliche Auswahl „Keine explizite Zuordnung“. Die ursprüngliche Taxonomiezuordnung bleibt bei Abbruch des Dialogs erhalten. Der Vorlagen-Übernahmedialog selbst prüft keine XBRL-Calculation-Beziehung.

## Vergleich der Editoren und Verhalten bei Änderungen

| Oberfläche | HGB-/Taxonomieverhalten |
|---|---|
| Vorlageneditor bei Neuanlage | Verwendet den Bundle-Import samt Mappingdatei. Kontotyp ändert die verfügbaren HGB-Positionen; Änderungen an HGB-Soll/Haben lösen im Template-Modus eine neue Taxonomie-Choice-Ermittlung aus. Ein bestehendes Concept außerhalb der Choices wird als nicht verfügbar angezeigt und blockiert unverändertes Speichern dieses Kontodialogs. Eine ausdrückliche Auswahl „Keine explizite Zuordnung“ entfernt die Zuordnung aus dem Bundle. |
| Mandantenspezifischer Konto-Editor | Der normale `AccountEditorDialog` läuft ohne `template_mode`: Er bearbeitet Kontotyp, HGB-Zuordnung und Aktivstatus, aber keine Taxonomiezuordnung. Eine HGB-Änderung schreibt daher die Taxonomiezeile nicht um und validiert sie dort nicht erneut. |
| Dialog „E-Bilanz-Zuordnung“ | Ruft die Choice-Liste für die aktuelle HGB-Zuordnung ab. Sind gar keine Choices verfügbar, wird der Dialog nicht geöffnet. Wenn eine bestehende Zuordnung nicht in einer ansonsten nichtleeren Choice-Liste enthalten ist, bleibt die ComboBox nicht auf dem bisherigen Wert; „Speichern“ kann dann den ersten Choice-Wert speichern. „Zuordnung entfernen“ löscht nur die Zuordnung der Version 6.9. Der Aufrufer fängt `ValueError` und Datenbanksperren, aber nicht `OSError`/`FileNotFoundError` des Taxonomie-Resolvers ab. |
| E-Bilanz-Anzeige im Kontentab | Zeigt das Label der Taxonomiezuordnung, wenn es in der Choice-Liste vorkommt; ansonsten fällt die Anzeige auf den rohen Concept-Namen zurück. |

Der Editor und die Erzeugung verwenden beide dieselbe Taxonomie-Calculation-Struktur, aber nicht dieselbe Strenge: Der Editor bietet alle erreichbaren Nachfolger über `descendants_of()` an. Die E-Bilanz-Erzeugung verlangt für eine explizite Zuordnung genau einen Pfad (`paths_between()` muss genau ein Ergebnis liefern). Ein Concept mit mehreren Calculation-Pfaden kann daher im Editor auswählbar sein und beim Erzeugen dennoch abgelehnt werden. Ein Concept ohne Pfad wird sowohl aus der Choice-Liste ausgeschlossen als auch bei der Erzeugung abgewiesen. Für `bs.eqLiab.equity.subscribed.corp` wurde der Pfad jetzt bestätigt; es gibt genau einen.

Die Kontotyp-/HGB-Reaktion im Template-Dialog ist ereignisgesteuert: Kontotypwechsel füllt die HGB-Comboboxen neu; ihre Textänderungen aktualisieren im Template-Modus die Taxonomieauswahl. Eine bestehende Taxonomiezuordnung wird nicht automatisch umgeschrieben. Im normalen Mandanten-Konto-Editor kann eine HGB-Änderung dagegen eine zuvor gespeicherte Taxonomiezuordnung unangetastet lassen.

Beim mandantenspezifischen Konten-Tab wird auch die Statusanzeige der Taxonomiezuordnung erneut gegen die Choice-Liste abgefragt. Sie fängt `ValueError` ab, aber nicht `OSError`; bei fehlendem lokalen Taxonomie-Entry-Point ist deshalb auch dieser normale Anzeige-/Zuordnungsweg nicht robust abgesichert.

## Persistenz und Taxonomieversionierung

Die Unique-Constraint der Datenbank lautet `(mandant_id, account_number, taxonomy_version)`. Das erlaubt **parallele Zuordnungen eines Kontos für unterschiedliche Taxonomieversionen**. Es ist keine Versionshistorie: Für dieselbe Kombination aus Mandant, Konto und Version gibt es nur den aktuellen Wert.

- `save_single_account_taxonomy_concept()` fügt hinzu, ersetzt oder löscht nur den Eintrag für die übergebene Version.
- `save_account_taxonomy_concepts()` ersetzt alle Zuordnungen dieser Version beim Mandanten; Zeilen anderer Versionen bleiben bestehen.
- `load_all_account_taxonomy_concepts()` liefert alle Versionsgruppen. Im aktuellen Arbeitsbaum wird es zusätzlich von der uncommitteten Löschfunktion verwendet, damit das Löschen eines Kontos keine Zuordnungsversion verwaist.
- Kontoanzeige, Mappingdialog und E-Bilanz-Aufbau laden in der vorhandenen Produktlogik aber fest Version `6.9`. Andere gespeicherte Versionen werden von diesen Abläufen nicht angezeigt oder an die E-Bilanz-Erzeugung übergeben.
- Der Mandantenexport kann alle Zuordnungsgruppen serialisieren; beim Import werden sie gruppiert nach Versionswert gespeichert.

Die Vorlagen-Mappingdatei hat keine integrierte Historie. Ihre Version steht in der benachbarten JSON-Konfiguration. Die Datenbankversion ist jeweils ein Versionsschlüssel, nicht ein Änderungszeitpunkt.

## E-Bilanz-Verarbeitung

`FiscalYearWorkspace.build_e_bilanz()` lädt nur die 6.9-Zuordnungen und reicht sie an `EBilanzService.build()` weiter. Der Service ermittelt das Taxonomie-Entry-Point aus dem Geschäftsjahr und unterstützt im Erzeugungspfad derzeit ausschließlich 6.9. Für jedes Konto mit explizitem Taxonomieeintrag prüft er, dass das Concept im Modell existiert und genau ein Calculation-Pfad von der HGB-Mappingposition zum Concept besteht. Kein Pfad oder mehrere Pfade führen zu `ValueError`, bevor ein Dokument fertiggestellt wird.

Damit wird eine beanstandete Zuordnung bei fehlender oder mehrdeutiger Calculation-Beziehung nicht still als Fact ausgegeben; der Build scheitert. Wenn das Concept gültig ist, werden sein Wert sowie die aus dem eindeutigen Calculation-Pfad ermittelten Aggregations-Vorfahren in den Fact-Plan aufgenommen. Fehlt für ein Konto eine explizite Taxonomiezuordnung, gibt es keine allgemeine automatische Ableitung eines Konten-Detail-Concepts. Einige explizite Sonderregeln für Bank/Kasse, Vorsteuer, bestimmte andere Verbindlichkeiten, BGA und Standardumsatzkonten liefern unabhängig davon Facts und enden mit `continue`; bei genau diesen Sonderfällen wird ein gespeichertes explizites Detailmapping nicht anschließend zusätzlich verwendet.

Die Taxonomieversion wird an anderer Stelle nach Geschäftsjahresbeginn ausgewählt: 2025 → 6.8, 2026 → 6.9, ab 2027 → 6.10. Die aktuelle Konten-Mapping- und E-Bilanz-UI-/Build-Integration liest jedoch nur 6.9; `EBilanzService` verweigert die Versionen 6.8 und 6.10. Das ist eine bestehende Versionierungsgrenze, keine Aussage zur fachlichen Richtigkeit einzelner SKR04-Mappings.

## Einordnung

| Stufe | Befund | Bewertung |
|---|---|---|
| A – kritisch | Ein fehlender oder mehrdeutiger Pfad würde den Build abbrechen. Im aktuellen 187er-SKR04-Bestand trat das nicht auf. | Keine bestätigte Mappingursache für einen Abbruch. |
| B – fachlich relevant | Alle 187 SKR04-Zuordnungen haben im Modell einen eindeutigen Pfad; fehlende Konten-/HGB-Referenzen wurden ebenfalls nicht gefunden. | Kein bestätigter B-Befund. |
| C – Bedienung | Wenn Taxonomie 6.9 fehlt oder der Provider fehlschlägt, kann der Template-Kontodialog den Providerfehler mit „passt nicht zur aktuellen HGB-Zuordnung“ überschreiben. Bei einem tatsächlich nicht auswählbaren gespeicherten Concept kann der separate Mappingdialog bei nichtleerer Liste auf den ersten Eintrag zurückfallen. Mit dem jetzt installierten Modell enthält die Choice-Liste für Konto 2900 42 Optionen, darunter das gespeicherte Concept; die frühere Warnung tritt für diesen Fall nicht mehr auf. | Fehlerbehandlung bei fehlendem Modell bleibt ein UI-Befund; Mapping 2900 aktuell korrekt angeboten. |
| D – unklar | Die geprüfte Mappingdatei ist eindeutig auf 6.9 datiert; ihre XBRL-Concepts und Pfade wurden vollständig geladen und geprüft. Eine unabhängige bytegenaue Gegenprüfung des gelieferten ZIPs gegen den offiziellen Webserver erfolgte nicht. | Für die Modellprüfung kein offener Befund; Dateiprovenienz anhand der enthaltenen Begleitunterlagen. |

## Kleinstmöglicher Korrekturvorschlag

1. Keine SKR04-Mappingänderung und keine Sonderbehandlung für 2900 vornehmen: Die geprüften 187 Zuordnungen bestehen den vorhandenen Calculation-Pfad-Check.
2. Die Editorprüfung sollte Provider-/Versions-/HGB-Eingabefehler von „Concept ist im erfolgreich geladenen Modell nicht genau einmal als Calculation-Nachfolger erreichbar“ getrennt anzeigen; der gegenwärtige Code überschreibt den ursprünglichen Providerfehler.
3. Für bereits gespeicherte Concepts sollte die Validierung bei erfolgreicher Taxonomieladung dieselbe Eindeutigkeitsbedingung wie die Erzeugung verwenden. Ein unverändertes Edit darf ein bestehendes Concept nicht als ungültig ausgeben, nur weil es aus einem nicht geladenen Modell nicht in Choices auftaucht.
4. Der mandantenspezifische Mappingdialog sollte einen nicht auswählbaren aktuellen Wert sichtbar erhalten und nicht ohne bewusste Benutzerwahl den ersten anderen Wert als Speichern-Ergebnis verwenden.

## Vorhandene Prüfungen

Ausgeführt wurden ausschließlich bestehende einschlägige Tests:

- `tests/services/test_e_bilanz_service.py -k 'account_taxonomy_choices or wrong_parent'`: 2 bestanden. Deckt Calculation-Nachfolgerliste und Build-Ablehnung eines falschen Elternpfads ab; testet keine der 187 realen SKR04-Concepts.
- `tests/ui/test_chart_of_accounts_template_editor_dialog.py -k 'account_editor'`: 6 bestanden. Deckt Editieren, Entfernen, Auswahlwechsel und Speichern mit Test-Choices ab, nicht das offizielle 6.9-Paket.
- `tests/taxonomy/test_hgb_gaap_ci_mapping.py`: im damaligen Lauf 1 bestanden, 4 übersprungen, weil die Taxonomieversionen damals noch nicht installiert waren. Der bestandene Test prüft das statische HGB-GAAP-CI-Mapping, keine SKR04-Concept-Abstammung. In der aktuellen Prüfung wurden keine Tests erneut ausgeführt; stattdessen wurde das Modell direkt über den vorhandenen Adapter geladen und die bestehende Build-Prüfbedingung auf alle 187 Zuordnungen angewendet.

Keine neue Testsuite wurde angelegt. Es wurden keine Datenbank oder Mandantendaten geändert und keine E-Bilanz/ERiC-Übermittlung durchgeführt. Die Taxonomiedateien wurden für die aktuelle Prüfung verwendet, aber nicht inhaltlich geändert.

## Archiv, Installation, Lizenz und Paketierung

- Geprüftes Archiv: `german-gaap-taxonomy-v6.9-2025-04-01.zip`; 53.607.047 Byte; SHA-256 `4c2572b438e7c1b04119d2c6363bc9b07605ddb1a14731dec10a3a0900d7bfc9`. Die Kopie unter `~/Downloads` hat dieselbe Prüfsumme. Der ZIP-Integritätstest ist erfolgreich; 367 Einträge umfassen 27 XSDs und 254 XML-Dateien. Es gibt keine absoluten, über `..` ausbrechenden oder als Symlink markierten ZIP-Einträge.
- Der ZIP-Stammordner und XSD-Verzeichnisse sind auf `2025-04-01` datiert. `META-INF/taxonomyPackage.xml` nennt Publisher XBRL Deutschland e.V., Version `6.9`, Publication Date `2025-04-01` und den Disclaimer. Es gibt genau einen `de-gaap-ci-2025-04-01-shell-fiscal.xsd`- und einen `de-gcd-2025-04-01-shell.xsd`-Entry-Point. Das Archiv enthält 27 XSDs, 254 XML-Dateien, darunter 40 Calculation-, 71 Presentation-, 37 Definition-, 38 Label- und 10 Reference-XML-Dateien. Das BMF veröffentlicht die Taxonomie 6.9 vom 1. April 2025 als amtlich vorgeschriebenen Datensatz ([BMF-Schreiben vom 10. Juni 2025](https://www.bundesfinanzministerium.de/Content/DE/Downloads/BMF_Schreiben/Steuerarten/Einkommensteuer/2025-06-10-ebilanz-taxonomien-6-9.html)).
- Der Disclaimer im Archiv benennt XBRL Deutschland e.V. als Rechteinhaber und gestattet die freie gewerbliche und nicht gewerbliche Verwendung sowie Kopieren und Weitergabe, sofern jede Kopie den Copyright-Vermerk aus dem Original enthält. Das unveränderte ZIP enthält den Disclaimer und Copyright-Vermerke in den Taxonomie-Dateien. Die Lizenzbedingung ist damit für dieses unveränderte Archiv nachvollziehbar.
- Der vorhandene `TaxonomyInstallationService.install_from_zip()` wurde unverändert mit dem lokalen Archiv verwendet. Es installierte nach `~/Library/Application Support/SimpleOB/taxonomy/6.9`; das Originalarchiv blieb bytegleich. Resolver, GAAP-CI- und GCD-Entry-Points funktionieren.
- Die macOS-PyInstaller-Spezifikation packt Arelle-Ressourcen, Kontenrahmenvorlagen und Mappingdateien ein, aber nicht die vollständigen Taxonomiedateien. Laufzeit-Taxonomien liegen im beschreibbaren Application-Support-Verzeichnis; `data/taxonomy` ist der Entwicklungsstandard. `.gitignore` schließt nur `/data/taxonomy/` aus, nicht ein ZIP im Projektstamm. Es gibt keine vorhandene Git-Konvention für große Taxonomie-ZIP-Dateien und keinen Git-LFS-Attributsatz. Das 53,6-MB-Archiv erhöht dauerhaft die Repository-/Clone-Größe; wegen des im Archiv enthaltenen Weitergaberechts ist die Aufnahme zulässig, aber ein großer dauerhafter Binärbestandteil. Ausschließlich dieses Archiv ist im Git-Index vorgemerkt; es gibt keinen Commit oder Push.

## Geladenes Modell und Prüfung aller SKR04-Zuordnungen

Das Modell wurde offline über `TaxonomyResolver` und `ArelleAdapter.model()` aus den installierten Entry-Points geladen. GAAP-CI enthält 3.348 Concepts, 3.346 Labels, 5.557 Presentation-Relationen und 2.172 Calculation-Relationen. GCD enthält 855 Concepts, 855 Labels, 830 Presentation-Relationen und keine Calculation-Relationen. Der GAAP-CI-Calculation-Graph ist vorhanden und wurde für die Prüfschritte verwendet.

Für jede der 187 expliziten Mappingzeilen wurden die Kontenrahmen-HGB-Position, das zugehörige HGB-GAAP-CI-Parent-Concept, das Vorlagen-Concept und die vorhandene Build-Bedingung geprüft: Concept muss existieren und `paths_between(parent_id, target_id)` muss genau einen Pfad liefern. Ergebnis: **187 eindeutig gültig; 0 ohne Pfad; 0 mehrdeutig; 0 unbekannte Concepts; 0 sonstige technische Fehler.** Die vollständige Ergebnistabelle oben enthält für jedes Konto den konkreten Status. Es gibt keine Abweichungen.

Für Konto 2900 ist der konkrete Pfad: `HGB.266.PASSIVA.A.I` → `bs.eqLiab.equity.subscribed` → `bs.eqLiab.equity.subscribed.corp`; `paths_between()` liefert genau einen Pfad. Die bestehende E-Bilanz-Validierungsbedingung akzeptiert das Mapping. Es wurden keine E-Bilanz erzeugt oder übermittelt und keine Änderungen an Anwendungscode, Vorlagen oder Mappingdateien vorgenommen.

Die frühere Downloadstörung bleibt eine separate lokale TLS-/CA-Konfigurationsfrage. Die Taxonomie wurde für diese Prüfung aus dem bereits vorhandenen ZIP installiert; es wurde kein Download und kein TLS-Bypass verwendet.

# Erfolgreiche ERiC-Testübermittlung: SKR04 2026

Dokumentationsstand: 14.11.2026
Projektstand: Branch `feature/ust-jahresabschluss`, Commit `337cb93c2b05fac094f5843e37e8b0c7f5dc9103`
Anwendungs-Version laut `pyproject.toml`: `0.53.0`

## Ergebnis

Der Benutzer hat bestätigt, dass die E-Bilanz des unten beschriebenen künstlichen Testmandanten über die SimpleOB-GUI als ERiC-/ELSTER-Testsendung vollständig angenommen wurde und ein positives Übermittlungsprotokoll vorlag. Codex hat diese Übermittlung nicht ausgeführt und das positive Protokoll nicht lokal vorgefunden. Die Annahme ist daher als Benutzerbestätigung dokumentiert, nicht als unabhängig archivierter Übermittlungsnachweis.

## Testgegenstand und Umgebung

- Rechtsform und Mandant: künstlicher SKR04-Testmandant „SKR04 E-Bilanz Test UG“.
- Geschäftsjahr: 01.01.2026–31.12.2026, abgeschlossen.
- Kontenrahmen: SimpleOB-SKR04 2026 für Kapitalgesellschaften, 248 Konten.
- Individuelle Taxonomiezuordnungen: 187.
- Buchungsbestand vor dem bestätigten Versand: 116 Buchungen und 271 Buchungszeilen.
- Taxonomie: GAAP-CI 6.9, Taxonomie-Einstiegspunkte vom 01.04.2025; ERiC-Datenart `Bilanz_6.9`.
- ERiC: API-Version 44.2.4 laut installiertem `ericversion.h`; verwendetes Installationspaket 44.2.4.0 für Darwin Universal. Die lokale isolierte Konfiguration verwies auf dessen `lib`-Verzeichnis. Die zugehörige ERiC-Dokumentation im Downloadbereich ist als 44.2.4.1 gekennzeichnet; dies ist die Dokumentationspaketversion, nicht die API-Version.
- Isolierung: GUI lief laut Benutzer mit dem aktuellen Quellcode aus `SimpleOB-Clean`; Konfiguration und SQLite-Testdatenbank lagen separat unter `/private/tmp/simpleob-stufe23e-gui/`. Die reguläre Projektkonfiguration und regulären Mandantendaten waren nicht Teil dieser Testumgebung.

Die ERiC-Version ist zusätzlich durch `/Users/ralf/Developer/ERiC/installed/44.2.4/ERiC-44.2.4.0/Darwin-universal/include/ericversion.h` belegt. Die installierte Bibliothek enthält den Validator `lib/plugins/libcheckBilanz_6_9.dylib`.

## Kontrollwerte des Testfalls

Die bekannten Werte aus der SKR04-Testfallprüfung lauten:

| Kennzahl | Erwarteter beziehungsweise geprüfter Wert |
|---|---:|
| Bilanzsumme | 51.487,42 € |
| Jahresfehlbetrag | −1.639,76 € |
| Umsatzerlöse | 59.000,00 € |
| Materialaufwand | 2.500,00 € |
| Bruttoergebnis | 56.500,00 € |
| Finanzergebnis | −195,00 € |
| Sachanlagenabschreibungen | 833,33 € |
| Umsatzsteuerverbindlichkeit, Konto 3840 | 3.247,93 € |

Diese Beträge dokumentieren die bekannten Kontrollwerte des Testfalls. Da die tatsächlich übermittelte XBRL-Datei lokal nicht eindeutig identifiziert werden konnte, wird nicht behauptet, dass eine bestimmte lokale XBRL-Datei bytegenau der angenommenen Übermittlung entsprach.

## Im Entwicklungsstand behobene Probleme

### GuV-Calculation

Die zuvor von ERiC beanstandeten GuV-Beziehungen wurden im Entwicklungsstand korrigiert:

- Finanz-Zwischensumme aus den vorhandenen Finanzwerten bilden.
- Gesamtleistung aus den vorhandenen Umsatzerlösen bilden.
- Doppelte Abbildung der Sachanlagenabschreibung in der GuV vermeiden.
- Monetäre Facts werden mit zwei Nachkommastellen ausgegeben.

Die Korrekturen sind unter anderem in den Commits `c96d33e` (GuV-Calculation-Facts) und `722725b` (monetäre XBRL-Formatierung) enthalten.

### Berichtskennzeichen EV

Commit `337cb93` gibt bei unterstützten Kapitalgesellschaften ohne gespeicherte Ergebnisverwendungsdaten das GCD-Feld EV als expliziten NIL-Fact aus. Bei vorhandenen Ergebnisverwendungsdaten bleibt die bisherige werthaltige Ausgabe erhalten. Für den Testfall wurde außerdem verifiziert, dass `incomeStatementendswithBalProfit=false` bestehen bleibt und die NIL-Angabe keine Ergebnisverwendungsbeträge erzeugt.

### Gesellschafterangaben

Für den vom Benutzer bestätigten erfolgreichen Versand müssen die zuvor beanstandeten Gesellschafterangaben im Testmandanten für den angenommenen Lauf vollständig vorgelegen haben. Der Benutzer bestätigt die Gesamtannahme der Testsendung. Die konkreten Werte werden hier aus Datenschutzgründen nicht wiedergegeben. Eine gesonderte Programmänderung an der Gesellschafterverwaltung ist in diesem Entwicklungsstand nicht dokumentiert.

## Übermittlungsnachweise und Archivierung

Bei der lokalen Bestandsaufnahme wurden im isolierten Testumfeld XBRL-Dateien gefunden:

- `/private/tmp/simpleob-stufe23e-gui/data/simpleob_stufe23f_gui_final.xbrl`
- `/private/tmp/simpleob-stufe23e-gui/data/simpleob_stufe23f_2026_complete.xbrl`
- `/private/tmp/simpleob-stufe23n-regenerated.xbrl`

Diese Dateien sind erzeugte Testartefakte, aber keine davon ist durch einen lokalen Beleg eindeutig als die tatsächlich übermittelte XBRL-Datei identifiziert. Die zuletzt genannte Datei entstand bei einer erneuten lokalen Regenerierung und ist nicht als Versanddatei belegt. Der isolierte Datenbankstand enthält keine Übermittlungshistorientabelle.

Ein eindeutig zuordenbares positives ELSTER-/ERiC-Übermittlungsprotokoll wurde in den geprüften Verzeichnissen nicht gefunden. `/private/tmp/eric.log` existiert, seine Zuordnung zur bestätigten Übermittlung ist jedoch nicht nachgewiesen und es wird deshalb nicht als Beleg geführt.

**Noch zu archivierende Nachweise:**

1. Das positive Übermittlungsprotokoll einschließlich Transferticket beziehungsweise eindeutigem Annahmeergebnis.
2. Die tatsächlich versandte XBRL-Datei oder ein Export der übermittelten Nutzdaten.
3. Eine Zuordnung beider Artefakte zum Mandanten, Geschäftsjahr, Testverfahren und zur verwendeten ERiC-Version.

Die Nachweise sind außerhalb dieses Commits aufzubewahren. Es wurden keine Inhalte oder Protokolle rekonstruiert.

## Aussagekraft und verbleibende technische Punkte

Der bestätigte Test zeigt, dass dieser konkrete künstliche UG-Jahresabschluss mit dem genannten lokalen Software-, Taxonomie- und ERiC-Stand das Testverfahren durchlaufen und laut Benutzer vollständig angenommen wurde. Ein einzelner erfolgreicher Test belegt weder die Annahme produktiver Übermittlungen noch sämtliche Rechtsformen, Kontenverwendungen, Taxonomievarianten oder Geschäftsjahre. Steuerliche Stammdaten und der konkrete Übermittlungszeitpunkt sind nicht Bestandteil dieser Dokumentation.

Im geprüften Projektstand ist für genau diesen unterstützten Standardfall kein weiterer zwingender technischer Eingriff erkennbar. Die fehlenden lokalen Übermittlungsartefakte sind eine Nachweis- und Archivierungslücke; sie widerlegen die Benutzerbestätigung nicht, begrenzen aber die unabhängige Nachprüfbarkeit.

## Versionssicherung

Vorgeschlagene Commit-Nachricht für diese Dokumentation:

`Document successful SKR04 E-Bilanz test transmission`

Vorgeschlagener, klar als Test markierter Tag nach dem Dokumentationscommit:

`skr04-2026-eric-test-accepted`

Der Tag sollte nicht als Produktionsfreigabe oder Produktrelease verstanden werden.

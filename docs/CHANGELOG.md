
# Changelog

# V0.44.001

Das Script  scripts/eric_reference_hgbm_69_multiyear_success.py
unter Grundlage folgedner Testdaten ezeugte heute eine ERIC-valide e-Bilanz:

Mandant: UG-0002
Geschäftsjahr: 2026
Vorjahr: 2025

HGB-AfA 2025:        333,33
Steuer-AfA 2025:     250,00
Vorjahresdifferenz:  +83,33 Buchwert

HGB-AfA 2026:        333,33
Steuer-AfA 2026:     250,00
Periodendifferenz:   +83,33 Buchwert

kumulierte
Buchwertdifferenz:  +166,66

HGB-Ergebnis 2026:  -333,33
Steuer-Ergebnis:    -250,00

ERiC:
<Erfolg/>

Alle wesentlichen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

## v0.17.0 (2026-08-07)

### Highlights

- Einführung eines CSV-Kontenrahmen-Importers
- Import von Bilanz- und GuV-Zuordnungsregeln
- Validierung des statement_type
- Einführung des Referenzkontenrahmens openbilanz_standard.csv
- Integrationstest für den vollständigen Import
- Qualitätsprüfung (pytest, ruff, git diff --check) erfolgreich

## v0.16.0 (2026-08-06)

### Highlights

- Vollständiger automatisierter GuV-Abschluss
- Abschluss sämtlicher Erlös- und Aufwandskonten
- Abschluss des GuV-Kontos bei Jahresüberschuss
- Abschluss des GuV-Kontos bei Jahresfehlbetrag
- Neues Domänenobjekt `ClosingAccounts`
- Gewinn- und Verlustkonten fachlich getrennt modelliert
- `ClosingService` zum Orchestrator des Jahresabschlusses refaktoriert
- Erste automatisierte Abschlussbuchungen erzeugt

### Changed

- Jahresabschlusslogik in kleine, klar abgegrenzte Methoden aufgeteilt
- Öffentliche API des `ClosingService` konsolidiert

### Quality

- Gesamter Testbestand erfolgreich
- `ruff check .` ohne Beanstandungen
- `git diff --check` ohne Beanstandungen
- Repository in sauberem Zustand


## Version 0.15.0 (2026-08-05)

### Highlights

- Vollständige Gewinn- und Verlustrechnung (§ 275 Abs. 2 HGB, GKV)
- Neues Domänenobjekt `IncomeStatement`
- Einführung von `StatementCategory`
- Neuer `ClosingService`
- Neues Domänenobjekt `ClosingResult`
- `FinancialStatementBuilder` unterstützt die Übernahme des Jahresüberschusses
- Erster vollständiger HGB-Jahresabschluss aus echten Buchungen
- End-to-End-Integrationstest vom Geschäftsvorfall bis zur ausgeglichenen Bilanz

### Qualitätsstand

- Alle Tests erfolgreich
- `ruff check .` ohne Beanstandungen
- `git diff --check` ohne Beanstandungen
- Repository in sauberem Zustand

## v0.10.0-dev
- Kontenmodell und Kontenplan

## v0.9.0 – Reporting

- Kontoblatt,
- ReportingService

## v0.8.0 – Accounting


## v0.6.0
- Added BookingValidator
- Validate account existence
- Added domain exceptions

## v0.5.0
- Introduced chart of accounts
- Added account factories

## v0.5.1-alpha1 - 2026-07-28

### Added
- ChartOfAccountsTemplate als neues Value Object
- Validierung von Name und Kontenliste
- Collection-API (`len`, Iteration, `contains`, `get`)
- 40 Unit-Tests für ChartOfAccountsTemplate

### Changed
- Ruff vollständig integriert
- Codebasis einheitlich formatiert

### Quality
- 285 Unit-Tests erfolgreich
- GitHub Actions erfolgreich


## v0.5.0-alpha3

### Added

- Introduced immutable `TemplateAccount` value object.
- Added validation for account numbers and account names.
- Added equality and hash semantics based on value equality.
- Added comprehensive unit tests for construction, validation,
  immutability, equality and hashing.

### Quality

- All tests passing.

## v0.5.0-alpha2

### Added

* Neue Domänenentität `Company`
* Stabile Identität über `UUID`
* Validierung von Unternehmensname und Identität
* Gleichheit und Hashwert basieren ausschließlich auf `company_id`

### Quality

* Gesamter Testbestand erfolgreich
* **209 Tests bestanden**


## v0.5.0-alpha1

### Added

* Neues Domänenobjekt `FiscalYear`
* Unterstützung für kalendergleiche und abweichende Geschäftsjahre
* Validierung von Datumsbereichen und Datentypen
* Berechnete Eigenschaften `duration_days` und `calendar_years`
* Methode `contains()` zur Prüfung, ob ein Datum innerhalb des Geschäftsjahres liegt

### Quality

* Gesamter Testbestand erfolgreich
* **183 Tests bestanden**


## [v0.4.0-apha2.0] - 2026-07-27

### Changed

- TrialBalanceEntry wieder entfernt.
- TrialBalanceRow als einziges Modell einer Summen- und Saldenlistenzeile festgelegt.
- Öffentliche API bereinigt.
- Doppelte Modellierung beseitigt.

### Quality

161 passed



## [v0.4.0-alpha1.0] - 2026-07-27

### Added

- Added immutable `Account` domain model.
- Added `AccountType` enumeration.
- Added validation for account number, account name and account type.
- Added string representation for accounts.
- Added comprehensive unit tests for the account domain model.

### Changed

- Prepared the domain model for future reporting components such as
  Trial Balance, Balance Sheet and Profit & Loss Statement.

### Quality

- All tests passed successfully.
- No regressions detected.

---

## [v0.3.0-alpha3.0]

### Added

- Added immutable `Journal` domain collection.
- Added insertion-order preserving storage.
- Added iteration support.
- Added membership operator (`in`).
- Added comprehensive unit tests.

### Changed

- Extended the domain model with a journal abstraction.

### Quality

- All tests passed successfully.
- No regressions detected.

---

## [v0.3.0-alpha2.0]

### Added

- Added `PostingService`.
- Added support for split debit and credit bookings.
- Added extensive PostingService unit tests.

### Changed

- Separated booking processing from the ledger implementation.

### Quality

- Complete regression test suite passed successfully.
```

---

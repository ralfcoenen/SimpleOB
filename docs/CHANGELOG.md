# Datei: `CHANGELOG.md`

```markdown
# Changelog

Alle wesentlichen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

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


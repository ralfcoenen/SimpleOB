# Changelog


## Version 0.1.0

Initiale Projektstruktur

- Python-Projekt angelegt
- Verzeichnisstruktur erstellt
- Dokumentation vorbereitet


Alle wesentlichen Änderungen an **OpenBilanz-UG** werden in dieser Datei dokumentiert.

Das Projekt orientiert sich an den Empfehlungen von *Keep a Changelog* und verwendet *Semantic Versioning*.

---

## [v0.3.0-alpha2.0] - 2026-07-27

### Added

* Einführung des zustandslosen `PostingService`
* Übertragung von `Booking`-Objekten in das `Ledger`
* Unterstützung von Splittbuchungen

  * eine Sollzeile auf mehrere Habenzeilen
  * mehrere Sollzeilen auf eine Habenzeile
  * mehrere Soll- und Habenzeilen
* Interne Paarbildung von Soll- und Habenzeilen zur Erzeugung elementarer Buchungen
* Unit-Tests für den `PostingService`
* Testabdeckung für:

  * einfache Buchungen
  * Splittbuchungen
  * Mehrfachbuchungen
  * ungültige Parameter
  * Unveränderlichkeit der `Booking`

### Changed

* Klare Trennung zwischen Domänenmodell (`Booking`) und buchhalterischer Verarbeitung (`PostingService`)
* `Ledger` bleibt ausschließlich für die Kontoführung verantwortlich.
* Die fachliche Übersetzung einer Buchung in elementare Soll-/Haben-Buchungen erfolgt ausschließlich im `PostingService`.

### Quality

* Gesamter Testbestand erfolgreich ausgeführt
* **154 Tests erfolgreich**
* Keine Regressionen festgestellt
* Architektur der Schichten erfolgreich validiert

---

## Frühere Versionen

Siehe Git-Historie und Tags.

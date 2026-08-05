# OpenBilanz-UG

Lokale Buchhaltungs- und E-Bilanz-Software für kleine Kapitalgesellschaften.

## Technologie

- Python 3.12
- PySide6
- SQLAlchemy
- SQLite

## Status

Version 0.13.0

## Ziel

Entwicklung einer modularen Anwendung für:

- Buchführung
- Jahresabschluss
- Bilanz
- GuV
- E-Bilanz/XBRL

## Versionshistorie

### 0.14.0

- Bilanzgliederung nach § 266 HGB vollständig modelliert
- Aktiv- und Passivseite als hierarchische Abschlussstruktur umgesetzt
- Mehrstufige Aggregation über den Eigenkapital-Ast abgesichert
- HGB-Regelwerk vom allgemeinen Accounting-Code getrennt
- Bilanzstruktur in private Fabrikfunktionen konsolidiert

### 0.13.0
- FinancialStatementBuilder fertiggestellt
- Aggregation von Abschlusspositionen
- Neues BalanceSheet-Domänenmodell
- Entfernung von BalancePosition und BalanceSection
- 375 Tests grün

### 0.12.0
- Kontenzuordnungsregeln eingeführt
- FinancialStatementPosition ergänzt

# Datei: `ARCHITECTURE.md`

````markdown
# Architecture

## Philosophy

OpenBilanz follows a domain-driven architecture.

Business concepts are represented as immutable domain objects whenever possible.

---

## Layers

```
Application
    │
    ▼
Services
    │
    ▼
Domain
    │
    ▼
Accounting
```

---

## Domain Layer

### EntrySide

Debit / Credit enumeration.

### BookingLine

Single posting line.

### Booking

Balanced accounting transaction.

### Journal

Chronological collection of bookings.

### Account

Represents the identity of a ledger account.

The account is intentionally immutable and forms the central domain object for future accounting reports.


## Domain Model

```
Domain
├── EntrySide
├── Booking
├── BookingLine
├── Journal
└── FiscalYear
```

`FiscalYear` ist ein unveränderliches Value Object und beschreibt ausschließlich den fachlichen Zeitraum eines Geschäftsjahres. Es enthält keine Workflow- oder Statusinformationen.

---

## Service Layer

### PostingService

Transforms bookings into elementary ledger postings.

Future

- TrialBalanceService

---

## Accounting Layer

### Ledger

Stores all postings.

### AccountBalance

Stores the running totals of one account.

Future

- TrialBalance
    └── TrialBalanceRow
- Balance Sheet
- Profit & Loss Statement

TrialBalanceRow ist das fachliche Modell einer Zeile der Summen- und Saldenliste. Weitere konkurrierende Zeilenmodelle werden nicht eingeführt.

---

## Design Principles

- Immutable domain objects
- Single Responsibility Principle
- Small public APIs
- Test-driven development
- Semantic versioning
- Continuous documentation
- Clear separation of responsibilities

---

## Current Status

Implemented

- EntrySide
- BookingLine
- Booking
- Journal
- Account
- AccountType
- PostingService
- AccountBalance
- Ledger

Planned

- TrialBalance
- TrialBalanceService
- Balance Sheet
- Profit & Loss Statement
````

---

# OpenBilanz – Architekturprinzipien

## Ziel
OpenBilanz modelliert die Buchhaltung fachlich korrekt.
Die Fachlichkeit bestimmt die Architektur, nicht umgekehrt.

## Grundsätze

1. Test Driven Development
   - Red
   - Green
   - Refactor

2. Domain Driven Design
   - Fachsprache verwenden.
   - Fachliche Operationen vor technischen Hilfsmethoden.

3. YAGNI
   - Keine spekulativen Attribute.
   - Keine spekulativen Klassen.

4. Immutability
   - Domänenobjekte sind nach Möglichkeit unveränderlich.

5. Kapselung
   - Interne Datenstrukturen bleiben verborgen.

6. Kleine Commits
   - Jeder Commit enthält genau einen fachlichen Schritt.

7. Hohe Testabdeckung
   - Neue Funktionalität entsteht immer aus einem Test.

8. Lesbarkeit vor Cleverness
   - Einfacher Code schlägt komplizierten Code.
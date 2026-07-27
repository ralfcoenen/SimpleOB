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


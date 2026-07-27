# OpenBilanz-UG – Public API

## Einleitung

Dieses Dokument beschreibt die öffentliche Programmierschnittstelle (API) von **OpenBilanz-UG**.

Alle hier aufgeführten Klassen und Methoden gehören zur öffentlichen API und können von Anwendungen verwendet werden. Nicht dokumentierte Klassen, Methoden oder Attribute sind interne Implementierungsdetails und können sich zwischen Versionen ändern.

---

# Paketübersicht

```
openbilanz
├── accounting
├── domain
└── services
```

---

# Domain

Die Domänenschicht beschreibt die fachlichen Objekte der Buchhaltung. Sie enthält keine Logik zur Kontoführung.

## EntrySide

Kennzeichnet die Buchungsseite.

### Werte

```python
EntrySide.DEBIT
EntrySide.CREDIT
```

---

## BookingLine

Repräsentiert eine einzelne Buchungszeile.

### Konstruktor

```python
BookingLine(
    account_no,
    side,
    amount,
)
```

### Eigenschaften

* `account_no`
* `side`
* `amount`

---

## Booking

Repräsentiert einen vollständigen Buchungssatz.

Eine Buchung

* ist unveränderlich (immutable),
* besitzt mindestens zwei Buchungszeilen,
* enthält mindestens eine Soll- und eine Habenzeile,
* ist immer ausgeglichen.

### Konstruktor

```python
Booking(
    booking_date,
    lines,
    voucher_no=None,
    description=None,
)
```

### Eigenschaften

```python
booking.booking_id
booking.booking_date
booking.lines
booking.voucher_no
booking.description
```

### Berechnete Eigenschaften

```python
booking.debit_total
booking.credit_total
booking.is_balanced
booking.debit_lines
booking.credit_lines
```

---

## Journal

Sammlung mehrerer Buchungen.

> Status: vorgesehen, noch nicht implementiert.

---

# Accounting

Die Accounting-Schicht bildet die eigentliche Buchführung ab.

---

## AccountBalance

Verwaltet die Bewegungen eines einzelnen Kontos.

### Eigenschaften

* Sollsaldo
* Habensaldo
* Kontosaldo

---

## Ledger

Repräsentiert das Hauptbuch.

### Methoden

```python
ledger.post(
    debit_account,
    credit_account,
    amount,
)
```

```python
ledger.get_account(
    account_no,
)
```

### Eigenschaften

```python
ledger.debit_total
ledger.credit_total
ledger.is_balanced
```

---

## TrialBalance

Summen- und Saldenliste.

> Status: vorgesehen, noch nicht implementiert.

---

# Services

Die Service-Schicht enthält die Geschäftslogik.

---

## PostingService

Überträgt fachliche Buchungen in das Hauptbuch.

### Methoden

```python
PostingService().post_booking(
    booking,
    ledger,
)
```

Der Service

* validiert die Parameter,
* zerlegt Splittbuchungen in elementare Soll-/Haben-Buchungen,
* überträgt diese an das Ledger,
* verändert die ursprüngliche Buchung nicht.

---

# Architektur

Die öffentliche Architektur besteht aus drei Schichten.

```
Domain
│
├── Booking
├── BookingLine
├── EntrySide
└── Journal

        │

Services
│
└── PostingService

        │

Accounting
│
├── Ledger
├── AccountBalance
└── TrialBalance
```

Abhängigkeiten sind ausschließlich in Pfeilrichtung zulässig.

---

# Grundsätze

* Domänenobjekte sind unveränderlich.
* Fachliche Geschäftslogik befindet sich ausschließlich in Services.
* Kontoführung erfolgt ausschließlich im Ledger.
* Interne Methoden (beginnend mit `_`) gehören nicht zur öffentlichen API.
* Änderungen der öffentlichen API erfolgen gemäß Semantic Versioning.

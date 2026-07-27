# OpenBilanz-UG – Architektur

## Zielsetzung

OpenBilanz-UG ist als modulare Buchhaltungsbibliothek für kleine und mittlere Unternehmen konzipiert.

Die Architektur verfolgt folgende Ziele:

* klare Verantwortlichkeiten
* hohe Testbarkeit
* unveränderliche Domänenobjekte
* geringe Kopplung
* einfache Erweiterbarkeit
* langfristige Wartbarkeit

---

# Schichtenmodell

```
                Anwendungen
                     │
                     ▼
              PostingService
                     │
                     ▼
        ┌──────────────────────┐
        │        Domain         │
        │                      │
        │  Booking             │
        │  BookingLine         │
        │  EntrySide           │
        │  Journal             │
        └──────────────────────┘
                     │
                     ▼
        ┌──────────────────────┐
        │      Accounting      │
        │                      │
        │ Ledger               │
        │ AccountBalance       │
        │ TrialBalance         │
        └──────────────────────┘
```

---

# Domain

Die Domain beschreibt ausschließlich die fachliche Welt.

Sie enthält keine Kenntnisse über

* Datenbanken
* Benutzeroberflächen
* Persistenz
* Kontoführung

Die Domain definiert lediglich, was eine korrekte Buchung ist.

---

# Services

Services enthalten sämtliche Geschäftsprozesse.

Ein Service

* besitzt keinen eigenen Zustand,
* verändert keine Domänenobjekte,
* koordiniert die Zusammenarbeit mehrerer Komponenten.

Der erste implementierte Service ist:

* `PostingService`

Seine Aufgabe besteht darin, fachliche Buchungen in elementare Soll-/Haben-Buchungen zu zerlegen und diese an das Ledger zu übertragen.

---

# Accounting

Die Accounting-Schicht bildet die technische Buchführung ab.

Das Ledger kennt keine Buchungssätze.

Es verarbeitet ausschließlich elementare Soll-/Haben-Buchungen.

Die Verantwortung für die Zerlegung von Splittbuchungen liegt ausschließlich beim `PostingService`.

---

# Entwurfsprinzipien

## Immutability

Alle Domänenobjekte sind unveränderlich.

Vorteile:

* keine Seiteneffekte
* einfache Tests
* Thread-Sicherheit
* reproduzierbares Verhalten

---

## Single Responsibility Principle

Jede Klasse besitzt genau eine fachliche Verantwortung.

Beispiele:

| Klasse         | Verantwortung              |
| -------------- | -------------------------- |
| Booking        | vollständiger Buchungssatz |
| BookingLine    | einzelne Buchungszeile     |
| PostingService | Verarbeitung einer Buchung |
| Ledger         | Kontoführung               |
| AccountBalance | Kontostand                 |

---

## Teststrategie

OpenBilanz-UG wird testgetrieben entwickelt.

Jede neue Funktion entsteht in der Reihenfolge:

1. Test definieren
2. Implementierung erstellen
3. Refactoring
4. Gesamten Testbestand ausführen

Ein Commit wird nur erstellt, wenn sämtliche Tests erfolgreich sind.

---

# Entwicklungsstand

## Version v0.3.0-alpha2.0

Implementiert:

* EntrySide
* BookingLine
* Booking
* AccountBalance
* Ledger
* PostingService

Vorbereitet:

* Journal
* TrialBalance

---

# Entwicklungsrichtlinien

* Öffentliche API sorgfältig dokumentieren.
* Private Methoden beginnen mit `_`.
* Neue Funktionen werden grundsätzlich durch Unit-Tests abgesichert.
* Jeder Commit repräsentiert einen lauffähigen Projektstand.
* Änderungen der öffentlichen API erfolgen gemäß Semantic Versioning.

---

# Ausblick

Die nächsten Ausbaustufen umfassen:

* Journal
* TrialBalance
* Mehrwertsteuer-Unterstützung
* Geschäftsjahre
* Persistenz
* DATEV-Export
* E-Bilanz

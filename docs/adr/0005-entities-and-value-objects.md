# ADR-0005: Entities und Value Objects

## Status

Accepted

## Kontext

Nicht alle Domänenobjekte besitzen dieselbe Art von Identität.

## Entscheidung

Es wird zwischen Entitäten und Value Objects unterschieden.

Beispiele:

Value Objects

* FiscalYear

Entities

* Company

Value Objects vergleichen sämtliche Werte.

Entities vergleichen ausschließlich ihre Identität.

## Konsequenzen

Klare fachliche Modellierung nach Domain-Driven Design.

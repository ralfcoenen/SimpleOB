# ADR-0007: Domain Design Principles

## Status

Accepted

## Kontext

Für alle zukünftigen Domänenobjekte gelten gemeinsame Entwurfsregeln.

## Entscheidung

OpenBilanz-UG folgt diesen Grundsätzen:

1. Domain First
2. Immutable by Default
3. Primärdaten speichern
4. Single Responsibility
5. API-Stabilität
6. Test-Driven Development

Zusätzlich gilt:

Jede Klasse muss in einem Satz fachlich erklärbar sein.

Kann eine Klasse nicht mehr in einem Satz beschrieben werden, ist ihre Verantwortung zu groß und sie sollte aufgeteilt werden.

## Konsequenzen

* Konsistente Architektur
* Verständliche Domänenmodelle
* Langfristig wartbarer Quellcode

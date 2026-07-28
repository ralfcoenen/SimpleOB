# ADR-0001: Test-Driven Development

## Status

Accepted

## Kontext

OpenBilanz-UG soll langfristig eine zuverlässige und wartbare Buchhaltungsbibliothek werden. Änderungen an der Fachlogik dürfen bestehende Funktionalität nicht unbeabsichtigt verändern.

## Entscheidung

Neue Funktionalität wird grundsätzlich testgetrieben entwickelt.

Reihenfolge:

1. Fachlichkeit definieren
2. Tests schreiben
3. Minimale Implementierung
4. Refactoring
5. Dokumentation
6. Vollständiger Testlauf
7. Commit
8. Tag
9. Push

## Konsequenzen

* Hohe Testabdeckung
* Frühe Erkennung von Regressionen
* Klare Definition der öffentlichen API

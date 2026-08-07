# OpenBilanz – Entwicklungsprinzipien

## Ziel

OpenBilanz wird fachlich aus der Buchhaltung heraus entwickelt.
Architektur und Implementierung folgen den fachlichen Anforderungen,
nicht umgekehrt.

---

## 1. Fachlichkeit zuerst

Die Domäne bestimmt das Modell.

Technische Entscheidungen werden erst getroffen,
wenn die fachlichen Anforderungen klar verstanden sind.
Die Architektur folgt der Fachlichkeit.

---

## 2. Entwicklung in kleinen Schritten

Neue Funktionen entstehen in kleinen TDD-Zyklen.

Jeder Zyklus besteht aus:

1. Fachliche Anforderung verstehen.
2. Kleinen roten Test schreiben.
3. Minimal implementieren.
4. Refaktorieren, wenn sich ein Muster zeigt.

---

## 3. Refactoring

Es wird nicht auf Vorrat abstrahiert.

Neue Abstraktionen entstehen erst,
wenn mindestens zwei konkrete Anwendungsfälle existieren.

---

## 4. Verantwortlichkeiten

Jede Klasse besitzt eine klar erkennbare Aufgabe.

- Domänenobjekte modellieren Fachlichkeit.
- Value Objects sind immutable.
- Services orchestrieren fachliche Abläufe.
- Builder erzeugen komplexe Strukturen.
- Importer und Exporte bilden die Schnittstelle zur Außenwelt.

---

## 5. Öffentliche APIs

Öffentliche Schnittstellen bleiben klein und stabil.

Interne Komplexität wird durch private Methoden oder
Domänenobjekte gekapselt.

---

## 6. Fehlerbehandlung

Technische Fehler werden an den Systemgrenzen
in fachliche Exceptions übersetzt.

Die Domäne bleibt unabhängig von Dateiformaten,
Datenbanken oder Benutzeroberflächen.

---

## 7. Codequalität

Vor jedem Commit:

- pytest
- ruff check .
- git diff --check

Nur ein vollständig grüner Stand wird eingecheckt.

---

## 8. Dokumentation

README.md beschreibt das Projekt.

CHANGELOG.md dokumentiert abgeschlossene Versionen.

ROADMAP.md beschreibt die geplante Weiterentwicklung.

Dieses Dokument beschreibt die Entwicklungsprinzipien.

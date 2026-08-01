# Zusammenfassung der Projektphase – OpenBilanzUG

## Ausgangspunkt

Ausgangspunkt des Projekts war die praktische Fragestellung, welche handels- und steuerrechtlichen Pflichten eine Unternehmergesellschaft (haftungsbeschränkt) zu erfüllen hat. Im Mittelpunkt stand dabei insbesondere die Erstellung einer E-Bilanz.

Im Verlauf dieser Analyse entstand die Erkenntnis, dass vorhandene Software häufig den technischen Ablauf unterstützt, das fachliche Modell der Buchführung jedoch nur unzureichend sichtbar macht.

Daraus entwickelte sich die Idee, eine eigene Software zu schaffen, deren Aufbau konsequent aus den fachlichen Anforderungen abgeleitet wird.

---

# Projektvision

OpenBilanzUG ist ein Open-Source-Projekt zur Entwicklung einer transparenten, fachlich korrekten und langfristig wartbaren Anwendung zur Erstellung einer E-Bilanz.

Der fachliche Kern dieser Anwendung wird als eigenständige Domänenbibliothek entwickelt. Diese modelliert die doppelte Buchführung und den handelsrechtlichen Jahresabschluss unabhängig von Benutzeroberflächen, Datenbanken sowie Import- und Exportformaten.

Die Anwendung baut später auf diesem fachlichen Kern auf und ergänzt ihn um alle Funktionen, die zur praktischen Erstellung einer E-Bilanz erforderlich sind.

---

# Entwicklungsstrategie

Die Entwicklung erfolgt konsequent von der Fachlichkeit zur Technik.

Der Weg lautet:

Gesetzliche Anforderungen

↓

Fachliche Analyse

↓

Domänenmodell

↓

Domänenbibliothek

↓

Anwendung

↓

E-Bilanz

Technische Entscheidungen werden erst getroffen, nachdem die fachlichen Zusammenhänge verstanden und modelliert wurden.

---

# Bisherige Architektur

Der fachliche Kern entwickelt sich schrittweise entlang des tatsächlichen Rechnungswesens:

Journal

↓

Ledger

↓

TrialBalance

↓

Kontenzuordnung

↓

BalanceSheet

↓

E-Bilanz

Jede Klasse besitzt eine klar abgegrenzte fachliche Verantwortung.

Komplexität wird bewusst vermieden und erst eingeführt, wenn sie fachlich notwendig wird.

---

# Entwicklungsprinzipien

Während der bisherigen Entwicklung haben sich folgende Grundsätze herausgebildet:

* Fachlichkeit vor Technik.
* Domain First.
* Testgetriebene Entwicklung (TDD).
* Kleine, nachvollziehbare Entwicklungsschritte.
* Immutable Domain Objects.
* Eine fachliche Verantwortung pro Klasse.
* Keine unnötigen Abstraktionen.
* Dokumentation begleitet die Entwicklung.
* Architekturentscheidungen werden nachvollziehbar dokumentiert.
* Langfristige Wartbarkeit ist wichtiger als kurzfristige Geschwindigkeit.

Diese Grundsätze bilden künftig die Grundlage aller Architektur- und Implementierungsentscheidungen.

---

# Dokumentationsstrategie

Die Dokumentation wird als eigenständiger Bestandteil des Projekts verstanden.

Sie gliedert sich in mehrere Ebenen:

* Vision
* Entwicklungsrichtlinien
* Domänenmodell
* Architektur
* Architecture Decision Records (ADR)
* Development Journal
* Roadmap
* Changelog

Jedes Dokument beantwortet eine klar abgegrenzte Fragestellung und vermeidet inhaltliche Überschneidungen.

---

# Architekturentscheidungen

Die wesentlichen Architekturentscheidungen werden dauerhaft als ADR dokumentiert.

Bereits festgehalten sind unter anderem:

* Domain First
* Immutable by Default
* Primärdaten statt abgeleiteter Werte
* Entities und Value Objects
* API-Stabilität
* Domain Design Principles
* Kontenzuordnung über Abschlusspositionen

Diese Entscheidungen bilden den langfristigen architektonischen Rahmen des Projekts.

---

# Erkenntnisse

Im Verlauf der bisherigen Entwicklung wurde deutlich, dass die eigentliche Herausforderung nicht in der Programmierung liegt, sondern im präzisen Verständnis der betriebswirtschaftlichen und rechtlichen Fachlichkeit.

Der Quellcode ist das Ergebnis dieser Modellierung – nicht ihr Ausgangspunkt.

---

# Nächste Phase

Die nächste Projektphase beginnt mit der Konsolidierung der Projektdokumentation.

Anschließend wird die fachliche Kontenzuordnung entwickelt, welche die Verbindung zwischen Trial Balance und Jahresabschluss herstellt.

Erst danach folgen der BalanceSheetBuilder und die weiteren Komponenten des Jahresabschlusses.

---

# Leitgedanke

**Die Fachlichkeit bestimmt das Modell; die Technik dient ausschließlich ihrer Umsetzung.**

Dieser Grundsatz bildet die gemeinsame Grundlage für die weitere Entwicklung von OpenBilanzUG.

**Status:** Draft
**Version:** 0.12.0
Letzte Aktualisierung: 01.08.2026

# Architektur von OpenBilanzUG

## 1. Zweck der Architektur

Die Architektur von OpenBilanzUG beschreibt die technische Umsetzung des im Domänenmodell festgelegten fachlichen Modells.

Sie folgt den in den Entwicklungsrichtlinien formulierten Grundsätzen und dient der Verwirklichung der in der Projektvision beschriebenen Ziele.

OpenBilanzUG wird als Anwendung zur Erstellung einer E-Bilanz entwickelt. Ihr fachlicher Kern besteht aus einer eigenständigen Domänenbibliothek für doppelte Buchführung und handelsrechtlichen Jahresabschluss.

Die Architektur stellt sicher, dass dieser fachliche Kern unabhängig von Benutzeroberflächen, Datenbanken sowie Import- und Exportformaten entwickelt und getestet werden kann.

---

## 2. Architekturziele

Die Architektur verfolgt insbesondere folgende Qualitätsziele:

### Gesetzliche Grundlagen

Die fachliche Struktur von OpenBilanzUG orientiert sich an den gesetzlichen Vorgaben des Handelsgesetzbuches (HGB).

Insbesondere bilden die Gliederungsvorschriften für die Bilanz und die Gewinn- und Verlustrechnung den fachlichen Zielzustand des Jahresabschlusses.

Kontenrahmen wie SKR03 oder SKR04 stellen keine eigene fachliche Struktur dar. Sie konkretisieren die gesetzlichen Abschlusspositionen, indem sie Konten diesen Positionen zuordnen.

Die Kontenzuordnung in OpenBilanzUG basiert daher auf den im Kontenrahmen definierten Zuordnungsregeln. Die eigentliche Zielstruktur wird jedoch durch die gesetzlichen Vorgaben des HGB bestimmt.

Dadurch bleibt die Architektur unabhängig von einem bestimmten Kontenrahmen und kann unterschiedliche Kontenrahmen unterstützen, ohne die Struktur des Jahresabschlusses ändern zu müssen.


### Fachliche Korrektheit

Die technische Struktur soll die Regeln und Begriffe der Buchführung und des Jahresabschlusses möglichst unmittelbar abbilden.

### Verständlichkeit

Verantwortlichkeiten und Abhängigkeiten sollen klar erkennbar sein. Neue Bestandteile müssen sich nachvollziehbar in die bestehende Struktur einfügen.

### Wartbarkeit

Änderungen sollen möglichst lokal vorgenommen werden können, ohne fachlich unabhängige Bereiche unnötig zu beeinflussen.

### Testbarkeit

Der fachliche Kern soll unabhängig von Benutzeroberfläche, Datenbank und externen Schnittstellen getestet werden können.

### Erweiterbarkeit

Neue fachliche Anforderungen sollen schrittweise aufgenommen werden können, ohne das bestehende Modell grundsätzlich neu entwerfen zu müssen.

### Nachvollziehbarkeit

Wesentliche Architekturentscheidungen werden als Architecture Decision Records dokumentiert.

---

## 3. Grundstruktur

OpenBilanzUG besteht aus zwei übergeordneten Bereichen:

### Fachlicher Kern

Der fachliche Kern modelliert Buchführung, Auswertungen, Jahresabschluss und die fachlichen Grundlagen der E-Bilanz.

Er ist unabhängig von technischen Ein- und Ausgabemechanismen.

### Anwendung und Infrastruktur

Die Anwendung verwendet den fachlichen Kern und ergänzt ihn um Benutzeroberfläche, Datenhaltung, Import, Export und weitere technische Dienste.

Die grundlegende Abhängigkeitsrichtung lautet:

```text
Benutzeroberfläche und externe Schnittstellen
                    ↓
              Anwendungsdienste
                    ↓
          Berichte und Auswertungen
                    ↓
                 Buchführung
                    ↓
             Fachliche Domäne
```

Abhängigkeiten sollen grundsätzlich zum fachlichen Kern zeigen. Der fachliche Kern kennt die ihn verwendenden technischen Komponenten nicht.

---

## 4. Verantwortungsbereiche

### 4.1 Fachliche Domäne

Die fachliche Domäne enthält grundlegende Fachobjekte und Regeln.

Dazu gehören insbesondere:

* Unternehmen
* Geschäftsjahr
* Konto
* Kontenrahmen
* Buchung
* Buchungszeile
* Journal

Technische Aspekte wie Datenbanken, Benutzeroberflächen oder Dateiformate gehören nicht in diesen Bereich.

**Paket:** `openbilanz.domain`

---

### 4.2 Buchführung

Der Bereich Buchführung verarbeitet die kontenbezogenen Auswirkungen fachlicher Buchungen.

Dazu gehören insbesondere:

* Kontensalden
* Hauptbuch
* Hauptbucheinträge
* Summen- und Saldenliste
* Bilanz
* Bilanzseiten
* Bilanzpositionen
* später die Gewinn- und Verlustrechnung

Dieser Bereich baut auf den fachlichen Grundobjekten der Domäne auf.

**Paket:** `openbilanz.accounting`

---

### 4.3 Berichte und Auswertungen

Dieser Bereich erzeugt unveränderliche Auswertungen aus vorhandenen Buchführungsdaten.

Dazu gehören beispielsweise:

* Kontoblätter
* Berichtzeilen
* weitere lesende Auswertungen

Berichte verändern die zugrunde liegende Buchführung nicht.

**Paket:** `openbilanz.reporting`

---

### 4.4 Anwendungsdienste

Anwendungsdienste koordinieren fachliche Abläufe, ohne selbst grundlegende Fachobjekte darzustellen.

Sie verbinden bestehende Komponenten, beispielsweise bei:

* der Übertragung einer Buchung in Journal und Hauptbuch,
* der Erstellung eines Kontoblatts,
* später der Erstellung des Jahresabschlusses.

Anwendungsdienste sollen keine Fachregeln duplizieren, die bereits in Domänenobjekten enthalten sind.

**Paket:** `openbilanz.services`

---

### 4.5 Taxonomie

Der Taxonomiebereich beschreibt die für die E-Bilanz erforderlichen Taxonomien und deren Positionen.

Er wird später die Verbindung zwischen dem fachlichen Jahresabschluss und der gesetzlich vorgegebenen elektronischen Struktur herstellen.

Die Taxonomie darf die grundlegende Buchführungslogik nicht bestimmen.

**Paket:** `openbilanz.taxonomy`

---

### 4.6 Datenhaltung

Die Datenhaltung speichert und lädt Anwendungs- und Fachdaten.

Sie ist eine technische Infrastrukturkomponente und darf keine eigenständige Buchführungs- oder Abschlusslogik enthalten.

Der fachliche Kern soll unabhängig von einer konkreten Datenbank verwendbar bleiben.

**Paket:** `openbilanz.database`

---

### 4.7 Benutzeroberfläche

Die Benutzeroberfläche ermöglicht die Bedienung der Anwendung.

Sie stellt Daten dar, nimmt Eingaben entgegen und ruft Anwendungsdienste auf.

Fachliche Berechnungen und Prüfungen gehören nicht in die Benutzeroberfläche.

**Paket:** `openbilanz.gui`

---

### 4.8 Import und Export

Import- und Exportkomponenten übersetzen zwischen externen Formaten und den öffentlichen Schnittstellen der Anwendung.

Dazu gehören später insbesondere:

* CSV
* JSON
* DATEV
* XBRL
* E-Bilanz-Daten

Diese Komponenten dürfen keine fachlichen Regeln duplizieren.

**Pakete:** `openbilanz.importer`, `openbilanz.exporter`

---

## 5. Abhängigkeitsregeln

Für die Zusammenarbeit der Verantwortungsbereiche gelten folgende Regeln:

1. Die fachliche Domäne kennt keine technischen Infrastrukturkomponenten.

2. Der Bereich Buchführung darf auf die fachliche Domäne zugreifen.

3. Berichte und Auswertungen dürfen Buchführungsdaten lesen, verändern diese jedoch nicht.

4. Anwendungsdienste koordinieren fachliche Abläufe und verwenden dafür öffentliche Schnittstellen der Domäne, Buchführung und Berichte.

5. Benutzeroberfläche, Datenhaltung sowie Import und Export dürfen auf Anwendungsdienste und öffentliche fachliche Schnittstellen zugreifen.

6. Fachliche Regeln dürfen nicht in Benutzeroberfläche, Datenbankmodellen oder Exportkomponenten verlagert werden.

7. Zirkuläre Abhängigkeiten zwischen Paketen sind zu vermeiden.

8. Neue Abhängigkeiten müssen fachlich oder architektonisch begründet sein.

---

## 6. Fachlicher Datenfluss

Der grundlegende fachliche Ablauf lautet:

```text
Geschäftsvorfall
       ↓
Buchung
       ↓
Journal
       ↓
Hauptbuch
       ↓
Summen- und Saldenliste
       ↓
Kontenzuordnung
       ↓
Jahresabschluss
       ├── Bilanz
       └── Gewinn- und Verlustrechnung
       ↓
E-Bilanz
```

Die Kontenzuordnung bildet dabei die Verbindung zwischen der Buchführung und den Positionen des Jahresabschlusses.

Die Zuordnung ist vom verwendeten Kontenrahmen und von fachlichen Ausweisregeln abhängig. Sie wird deshalb außerhalb der Summen- und Saldenliste und außerhalb der Abschlussmodelle umgesetzt.

Siehe hierzu ADR-0001.

---

## 7. Öffentliche Schnittstellen

Pakete können ausgewählte Klassen und Funktionen über ihre jeweilige `__init__.py` als öffentliche Schnittstelle bereitstellen.

Interne Implementierungsdetails sollen nicht ohne fachlichen oder technischen Grund von anderen Paketen verwendet werden.

Änderungen an öffentlichen Schnittstellen erfolgen bewusst und unter Beachtung der Regeln zur API-Stabilität.

Siehe hierzu ADR-0006.

---

## 8. Erweiterung der Architektur

Neue Funktionalität wird grundsätzlich von der Fachlichkeit aus entwickelt.

Der typische Ablauf lautet:

```text
Fachliche Anforderung
        ↓
Ergänzung des Domänenmodells
        ↓
Fachliche Tests
        ↓
Implementierung im fachlichen Kern
        ↓
Anwendungsdienst
        ↓
Benutzeroberfläche oder Schnittstelle
```

Nicht jede neue Funktion benötigt Änderungen auf allen Ebenen.

Neue Abstraktionen, Pakete oder Dienste werden nur eingeführt, wenn sie eine konkrete und klar abgegrenzte Verantwortung besitzen.

---

## 9. Architekturentscheidungen

Dauerhafte Architekturentscheidungen werden im Verzeichnis `docs/adr` dokumentiert.

Die Architekturübersicht beschreibt den aktuellen Gesamtaufbau. Die ADRs erläutern dagegen den Kontext, die Begründung und die Konsequenzen einzelner Entscheidungen.

---

## 10. Verwandte Dokumente

* `VISION.md`
* `ENTWICKLUNGSRICHTLINIEN.md`
* `DOMAENENMODELL.md`
* `PFLICHTENHEFT.md`
* `ROADMAP.md`
* `adr/README.md`


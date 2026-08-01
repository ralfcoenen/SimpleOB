# Domänenmodell von OpenBilanzUG

## 1. Ziel des Domänenmodells

Das Domänenmodell beschreibt die betriebswirtschaftlichen Begriffe und ihre Beziehungen, welche der doppelten Buchführung, dem handelsrechtlichen Jahresabschluss und der Erstellung einer E-Bilanz zugrunde liegen.

Es beschreibt bewusst die Fachlichkeit und nicht deren technische Umsetzung.

Die dargestellten Begriffe existieren unabhängig von ihrer Implementierung in OpenBilanzUG.

---

## 2. Grundprinzipien

Das Domänenmodell folgt den folgenden Grundsätzen:

* Es beschreibt ausschließlich fachliche Begriffe.
* Es verwendet die Terminologie des deutschen Rechnungswesens.
* Es ist unabhängig von Programmiersprachen und Softwarearchitekturen.
* Es bildet die gemeinsame Fachsprache des Projekts.
* Es dient als Grundlage für Architektur und Implementierung.

---

## 3. Aufbau der Fachdomäne

Die Fachdomäne gliedert sich in vier Bereiche:

### Unternehmen

Beschreibt das Unternehmen, den Mandanten und das Geschäftsjahr.

### Buchführung

Beschreibt die Erfassung und Verarbeitung sämtlicher Geschäftsvorfälle.

### Jahresabschluss

Beschreibt die Verdichtung der Buchführung zum handelsrechtlichen Jahresabschluss.

### E-Bilanz

Beschreibt die Überführung des Jahresabschlusses in die gesetzlich vorgeschriebene Taxonomie.

---

## 4. Beschreibung der Fachbegriffe

Alle Fachbegriffe werden nach einer einheitlichen Struktur beschrieben:

* Begriff
* Bedeutung
* Beziehungen
* Umsetzung in OpenBilanzUG

---

## 5. Beziehungen der Fachbereiche

Die Fachbereiche bauen logisch aufeinander auf.

Unternehmen

↓

Buchführung

↓

Jahresabschluss

↓

E-Bilanz

Diese Reihenfolge beschreibt den fachlichen Ablauf und bildet zugleich die Grundlage für die Architektur von OpenBilanzUG.


## Abschlussposition

### Definition

Eine Abschlussposition ist ein gesetzlich definierter Bestandteil des handelsrechtlichen Jahresabschlusses.

Sie beschreibt die Struktur der Bilanz oder der Gewinn- und Verlustrechnung entsprechend den gesetzlichen Vorgaben des Handelsgesetzbuches.

Die Abschlussposition besitzt eine unveränderliche fachliche Identität. Sie wird zum Bilanzstichtag durch die den Zuordnungsregeln entsprechenden Kontensalden befüllt.

### Fachliche Eigenschaften

Eine Abschlussposition

* besitzt höchstens eine Elternposition,
* kann beliebig viele Kinderpositionen besitzen,
* gehört entweder zur Bilanz oder zur Gewinn- und Verlustrechnung,
* folgt der gesetzlich vorgegebenen Reihenfolge,
* besitzt keine eigene fachliche Bedeutung außerhalb des Jahresabschlusses.

### Fachliche Regeln

Besitzt eine Abschlussposition untergeordnete Abschlusspositionen, ergibt sich ihr Betrag ausschließlich durch Aggregation ihrer Kinder.

Besitzt sie keine Kinderpositionen, wird ihr Betrag durch die zugeordneten Kontensalden bestimmt.

Eine Abschlussposition besitzt niemals gleichzeitig einen eigenen unmittelbar zugeordneten Betrag und untergeordnete Abschlusspositionen.

Eine Abschlussposition ist ein gesetzlich definierter und innerhalb des Jahresabschlusses hierarchisch eingeordneter Strukturposten. Sie besitzt selbst keinen Betrag. Endpositionen werden bei der Erstellung eines konkreten Jahresabschlusses durch zugeordnete Kontensalden zum Abschlussstichtag befüllt; übergeordnete Positionen aggregieren ausschließlich die Werte ihrer untergeordneten Positionen.

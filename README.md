# SimpleOB

**SimpleOB** ist eine Desktop-Anwendung für die laufende Buchführung, den
Jahresabschluss und die E-Bilanz kleiner Kapitalgesellschaften. Das Projekt
wird im Repository unter dem Entwicklungsnamen **OpenBilanz-UG** geführt; die
ausgelieferte Anwendung heißt **SimpleOB**.

## Aktueller Stand

Aktuelle Projektversion: **0.62.0** (`pyproject.toml`).

SimpleOB bietet derzeit:

- Mandanten- und Geschäftsjahrverwaltung sowie einfache Buchungssätze mit
  Journal, Kontenübersicht, Eröffnungsbuchungen und Buchungsstorno.
- Kontenverwaltung mit mandantenspezifischen Konten, HGB-Zuordnungen,
  Steuerkonten und fachlichen Kontenrollen.
- Geschäftspartnerstammdaten mit Debitoren- und Kreditoren-Personenkonten.
  Ein Geschäftspartner kann beide Rollen besitzen; je Rolle wird ein eigenes
  Konto mit eigener Kontonummer geführt. Debitorennummern liegen im Bereich
  10000–69999, Kreditorennummern im Bereich 70000–99999.
- Anlagenbuchhaltung einschließlich Abschreibungen, Anlagenabgängen und
  steuerlichen AfA-Abweichungen.
- Summen- und Saldenliste, Kontenauswertungen, Journal- und
  Personenkontenberichte sowie HGB-Bilanz und Gewinn- und Verlustrechnung.
- Jahresabschluss mit Prüfung, Umsatzsteuerverrechnung und
  Ergebnisverwendungsabläufen.
- E-Bilanz-Erzeugung mit Taxonomie 6.9, XBRL-Ausgabe und Arelle-Validierung.
  Für die E-Bilanz sind derzeit UG (haftungsbeschränkt) und GmbH unterstützt.
- ELSTER-Test- und Produktivübermittlung über ERiC, sofern das passende
  ERiC-SDK, ein gültiges Zertifikat und die erforderlichen Stammdaten verfügbar
  sind.
- Mandantentransfer als `.simpleob`-Datei einschließlich Geschäftspartnern,
  Personenkonten und Geschäftsjahren.
- SQLite als lokale Datenbank sowie PostgreSQL für eine vorhandene,
  eingerichtete Serverdatenbank.

Die Kontenkonfiguration enthält die Rollen **Kasse**, **Bank**,
**Umsatzerlöse allgemeiner Steuersatz**, **Umsatzsteuer-Vorauszahlungen**,
**Umsatzsteuer laufendes Jahr**, **Umsatzsteuerforderungen Vorjahr** und
**Umsatzsteuerverbindlichkeiten Vorjahr**. Sie beschreiben die fachliche
Verwendung unabhängig von der Kontonummer. Ein Bankkonto mit
Sollsaldo wird in der HGB-Bilanz unter B.IV ausgewiesen; ein Habensaldo wird
als Verbindlichkeit unter C.2 dargestellt. Unterschiedliche Bankkonten werden
nicht gegeneinander saldiert. Für gewöhnliche Bankverbindlichkeiten verwendet
die E-Bilanz-Taxonomie 6.9 die Unterposition
`bs.eqLiab.liab.bank.other`.

Für unbebuchte Personenkonten ist eine gesonderte, bestätigungspflichtige
Löschung verfügbar, wenn keine Buchungszeilen oder sonstigen sperrenden
Referenzen bestehen. Der Geschäftspartner bleibt dabei erhalten.

**Nicht enthalten** sind in Version 0.62.0 die Erfassung von Ein- und
Ausgangsrechnungen, Gutschriften, Anzahlungen und Leistungsvorgängen, eine
Offene-Posten-Nebenbuchführung mit Zahlungszuordnungen sowie eine
Umsatzüberwachung nach § 19 UStG. Debitoren- und Kreditorenkonten sind
Hauptbuchkonten; sie bilden keine Rechnungs- oder Zahlungshistorie ab.

## Arbeitsablauf

```text
Buchungen und Anlagen
        ↓
Journal, Konten und Auswertungen
        ↓
HGB-Bilanz und Gewinn- und Verlustrechnung
        ↓
Jahresabschluss
        ↓
E-Bilanz / XBRL
        ↓
Arelle-Validierung und optional ERiC / ELSTER
```

Die Anwendung trennt dabei Buchführung, HGB-Abschluss, E-Bilanz-Erzeugung
und elektronische Übermittlung. Vor einer produktiven Übermittlung sollten
Buchungen, Stammdaten und Abschlusswerte fachlich geprüft werden.

## Installation und Voraussetzungen

Für macOS wird SimpleOB als eigenständige `SimpleOB.app` in einem
Auslieferungspaket bereitgestellt. Das Paket wird derzeit ohne Apple
Developer-ID-Signatur und Notarisierung ausgeliefert; macOS kann beim ersten
Start deshalb eine Gatekeeper-Warnung anzeigen. Installieren Sie die Anwendung
nur aus einer vertrauenswürdigen Bezugsquelle und folgen Sie bei Bedarf den
Hinweisen im [Benutzerhandbuch](docs/SimpleOB_Benutzerhandbuch.md).

SQLite ist die Standardoption und benötigt keinen separaten Datenbankserver.
Für PostgreSQL ist ein erreichbarer, eingerichteter PostgreSQL-Server
notwendig. Das macOS-Auslieferungspaket enthält den PostgreSQL-Treiber.

Für die Entwicklung wird Python **3.12** benötigt. Das Projekt verwendet
PySide6, SQLAlchemy, Alembic und Arelle. Für den macOS-Build muss ein zum
Zielsystem passendes ERiC-SDK bereitgestellt werden; seine Komponenten werden
in die App eingebunden. ELSTER-Funktionen stehen nur bereit, wenn ERiC in der
Installation verfügbar ist. Die Zertifikats-PIN wird bei der Übermittlung
eingegeben und nicht dauerhaft gespeichert. Für Testsendungen ist ein
gültiges ELSTER-Testzertifikat, für produktive Sendungen ein dafür
zugelassenes persönliches Zertifikat nötig.

## Datenhaltung und Sicherung

SQLite speichert Daten lokal im SimpleOB-Anwendungsdatenverzeichnis.
PostgreSQL-Daten liegen auf dem Server. SimpleOB migriert SQLite beim Start
und legt vor erforderlichen Migrationen eine Sicherung an. PostgreSQL-Schema-
aktualisierungen werden nicht automatisch ausgeführt und müssen administrativ
geplant und vorab gesichert werden.

Eine `.simpleob`-Datei überträgt die unterstützten Daten eines Mandanten,
darunter Geschäftspartner, Personenkontenzuordnungen, Konten, Buchungen,
Anlagen und Geschäftsjahre. Version 0.62.0 verwaltet keine separate
OP-Nebenbuchhistorie. Eine `.simpleob`-Datei ersetzt keine vollständige
SQLite- oder PostgreSQL-Datenbanksicherung. Anwendungsweite ELSTER-
Einstellungen und Zertifikatspfade gehören nicht zum Mandantentransfer.
Details stehen im [Abschnitt zur Mandantensicherung](docs/SimpleOB_Benutzerhandbuch.md#14-datenaustausch-und-mandantensicherung).

## Benutzerhandbuch

Die aktuelle Handbuchquelle ist
[docs/SimpleOB_Benutzerhandbuch.md](docs/SimpleOB_Benutzerhandbuch.md). Sie
beschreibt unter anderem Konten und Personenkonten, Jahresabschluss,
Installation unter macOS, E-Bilanz und ELSTER sowie Mandantentransfer.
Das PDF für die Auslieferung wird aus dieser Markdown-Quelle erzeugt mit:

```bash
scripts/build_user_manual.sh
```

## Entwicklung

Entwicklungsumgebung einrichten:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Für die optionale PostgreSQL-Abhängigkeit:

```bash
python -m pip install -e ".[dev,postgresql]"
```

Die Anwendung kann anschließend mit `simpleob` gestartet werden. Die Tests
werden mit `pytest` ausgeführt. Weitere verwendete Bibliotheken und
Projektkonfigurationen stehen in `pyproject.toml`.

## Projektstatus

SimpleOB befindet sich in Entwicklung. Automatisierte Prüfungen unterstützen
die technische Zuverlässigkeit, ersetzen aber keine fachliche Prüfung der
Buchführung, des Jahresabschlusses und der E-Bilanz.

# SimpleOB

**SimpleOB** ist eine Desktop-Anwendung für Buchführung und E-Bilanz kleiner Kapitalgesellschaften. Sie kann ihre Daten in einer lokalen SQLite-Datenbank oder auf einem PostgreSQL-Server speichern.

Das Projekt wird im Repository unter dem Entwicklungsnamen **OpenBilanz-UG** geführt. Der Name der ausgelieferten Anwendung ist **SimpleOB**.

## Aktueller Stand

Aktuelle Version: **0.51.1**

SimpleOB umfasst inzwischen insbesondere:

- mandantenbezogene Buchführung
- Geschäftsjahre und Jahresabschluss
- Journal und Kontenführung
- Summen- und Saldenliste
- Bilanz nach § 266 HGB
- Gewinn- und Verlustrechnung nach § 275 HGB
- Anlagenbuchhaltung
- Erfassung von Eingangs- und Ausgangsrechnungen sowie Gutschriften
- Offene-Posten-Verwaltung mit Zahlungen, Verrechnungen, Rückerstattungen und Abstimmung
- grundlegenden Workflow für Eröffnungsbilanzen
- Umsatzsteuer- und Steuerkontenkonfiguration
- E-Bilanz auf Basis der Taxonomie 6.9
- XBRL-Erzeugung und -Validierung
- ELSTER-/ERiC-Übermittlung
- Testübermittlung mit ELSTER-Testzertifikat
- informative Umsatzüberwachung zur Kleinunternehmerregelung nach § 19 UStG
- Mandantensicherung und -übertragung im Format `.simpleob`
- SQLite- und PostgreSQL-Datenhaltung
- Datenbankmigrationen mit Alembic
- PDF-Auswertungen
- PySide6-Benutzeroberfläche

## Zielsetzung

SimpleOB ist als lokale Desktop-Anwendung für die Buchführung und den Jahresabschluss kleiner Kapitalgesellschaften konzipiert.

Ein Schwerpunkt liegt auf einem nachvollziehbaren durchgängigen Ablauf:

```text
Buchungen
    ↓
Journal und Konten
    ↓
Summen- und Saldenliste
    ↓
Bilanz und GuV
    ↓
Jahresabschluss
    ↓
E-Bilanz / XBRL
    ↓
ERiC / ELSTER
```

Die Anwendung soll dabei fachliche Buchhaltungslogik, HGB-Abschlusslogik und die technische E-Bilanz-/ELSTER-Übermittlung klar voneinander trennen.

## Technologie

SimpleOB basiert derzeit auf:

- Python 3.12
- PySide6
- SQLAlchemy
- Alembic
- SQLite (Standard)
- PostgreSQL (optionale Python-Abhängigkeit `postgresql`)
- Arelle
- ERiC
- ReportLab

Weitere verwendete Bibliotheken sind in `pyproject.toml` dokumentiert.

## Entwicklung

Vorausgesetzt wird Python 3.12.

Eine Entwicklungsumgebung kann beispielsweise so eingerichtet werden:

```bash
python -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Für eine Entwicklungsinstallation mit PostgreSQL-Treiber verwenden Sie stattdessen:

```bash
python -m pip install -e ".[dev,postgresql]"
```

Die Anwendung kann anschließend aus der Entwicklungsumgebung gestartet werden:

```bash
simpleob
```

SQLite ist ohne zusätzlichen Datenbankserver nutzbar. PostgreSQL erfordert einen eingerichteten und erreichbaren PostgreSQL-Server; für eine Entwicklungsinstallation ist zusätzlich die optionale Abhängigkeit `postgresql` erforderlich. Das macOS-Auslieferungspaket enthält den PostgreSQL-Treiber.

Die Tests werden mit `pytest` ausgeführt:

```bash
pytest
```

## macOS-Auslieferung

Für macOS wird SimpleOB mit PyInstaller als eigenständige Anwendung gebaut.

Das veröffentlichte macOS-Paket wird derzeit ohne Apple-Developer-ID-Signatur und ohne Notarisierung ausgeliefert. macOS kann deshalb beim ersten Start eine Gatekeeper-Warnung anzeigen oder das Öffnen zunächst blockieren. Hinweise zur Freigabe stehen im Benutzerhandbuch. Die Anwendung sollte nur aus einer vertrauenswürdigen Bezugsquelle installiert werden.

Die Release-Werkzeuge befinden sich unter `packaging/macos/`.

Für die einzelnen Release-Schritte stehen zur Verfügung:

```text
version_release.sh
build.sh
package_release.sh
publish_release.sh
```

Ein Release kann bis zum fertig geprüften Auslieferungspaket vorbereitet werden mit:

```bash
packaging/macos/release.sh VERSION
```

Die eigentliche Veröffentlichung erfolgt bewusst getrennt vom Build- und Packaging-Prozess.

## Benutzerhandbuch

Das Benutzerhandbuch befindet sich unter `docs/SimpleOB_Benutzerhandbuch.pdf`. Die bearbeitbare Quelle ist `docs/SimpleOB_Benutzerhandbuch.md`.

Das PDF kann erzeugt werden mit:

```bash
scripts/build_user_manual.sh
```

Das Benutzerhandbuch enthält insbesondere Hinweise zu Installation und erstem Start unter macOS, Mandanten und Geschäftsjahren, Buchführung und Jahresabschluss, E-Bilanz, ELSTER-Zertifikat und ELSTER-Datenlieferant, Test- und Produktivübermittlung sowie Datenbankaktualisierungen.

Es beschreibt außerdem offene Posten, Zahlungen, Rückerstattungen, Mandantensicherungen und die informative Umsatzüberwachung zur Kleinunternehmerregelung samt ihren fachlichen Grenzen.

## Datenhaltung, Sicherung und Aktualisierungen

SimpleOB verwendet standardmäßig SQLite. Die Datenbank und Anwendungskonfiguration liegen lokal im benutzerspezifischen SimpleOB-Anwendungsdatenverzeichnis. Optional kann eine vorhandene, erreichbare PostgreSQL-Datenbank verwendet werden; deren Buchhaltungsdaten liegen auf dem Datenbankserver.

Bei SQLite führt SimpleOB erforderliche Datenbankmigrationen beim Start aus und legt vor einer notwendigen Migration automatisch eine Sicherung der bestehenden Datenbank an. Bei PostgreSQL prüft SimpleOB beim Start den Schema-Stand, migriert eine vorhandene Datenbank aber nicht automatisch. Eine notwendige PostgreSQL-Aktualisierung muss administrativ geplant und vorab gesichert werden.

Eine `.simpleob`-Datei exportiert unterstützte Mandantendaten einschließlich der Geschäftsjahre und Einstellungen zur Kleinunternehmerregelung. Sie enthält derzeit weder Geschäftspartner noch separate OP- und Zahlungszuordnungsdaten und ist daher für Mandanten mit OP-Nutzung keine vollständige Sicherung oder Übertragung. Sie ersetzt auch keine vollständige Datenbanksicherung: SQLite muss lokal gesichert werden, PostgreSQL direkt auf dem Server. Anwendungsweite ELSTER-Einstellungen und Zertifikate werden nicht mit dem Mandanten exportiert. Umfang und Einschränkungen beschreibt das Benutzerhandbuch.

## E-Bilanz und ELSTER

Die E-Bilanz-Erzeugung basiert derzeit auf der **Taxonomie 6.9**.

SimpleOB trennt dabei die fachliche Erzeugung der E-Bilanz von der technischen Übermittlung über ERiC/ELSTER.

Für Testübermittlungen kann ein ELSTER-Testzertifikat verwendet werden. Für produktive Übermittlungen muss der Benutzer sein persönliches ELSTER-Zertifikat auswählen.

Die Zertifikats-PIN wird nicht dauerhaft gespeichert.

## Projektgrundsätze

Bei der Entwicklung stehen insbesondere im Vordergrund:

- nachvollziehbare Buchhaltungslogik
- klare Trennung von Domänen-, Datenbank- und Benutzeroberflächenlogik
- mandantenspezifische Konfiguration statt fest codierter Konten
- kontrollierte Datenbankmigrationen
- reproduzierbare Release-Prozesse
- SQLite als Standard sowie optional PostgreSQL
- möglichst geringe unnötige Komplexität

E-Bilanz- und Taxonomiefunktionalität wird gezielt auf den für die technisch valide und tatsächlich übermittelbare E-Bilanz erforderlichen Umfang begrenzt.

## Projektstatus

SimpleOB befindet sich weiterhin in Entwicklung.

Vor dem produktiven Einsatz sollten insbesondere die erzeugten Abschlüsse, E-Bilanz-Daten und ELSTER-Übermittlungen fachlich geprüft werden.

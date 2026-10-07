# SimpleOB

**SimpleOB** ist eine lokale Buchhaltungs- und E-Bilanz-Anwendung für kleine Kapitalgesellschaften.

Das Projekt wird im Repository unter dem Entwicklungsnamen **OpenBilanz-UG** geführt. Der Name der ausgelieferten Anwendung ist **SimpleOB**.

## Aktueller Stand

Aktuelle Version: **0.47.1**

SimpleOB umfasst inzwischen insbesondere:

- mandantenbezogene Buchführung
- Geschäftsjahre und Jahresabschluss
- Journal und Kontenführung
- Summen- und Saldenliste
- Bilanz nach § 266 HGB
- Gewinn- und Verlustrechnung nach § 275 HGB
- Anlagenbuchhaltung
- grundlegenden Workflow für Eröffnungsbilanzen
- Umsatzsteuer- und Steuerkontenkonfiguration
- E-Bilanz auf Basis der Taxonomie 6.9
- XBRL-Erzeugung und -Validierung
- ELSTER-/ERiC-Übermittlung
- Testübermittlung mit ELSTER-Testzertifikat
- lokale SQLite-Datenhaltung
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
- SQLite
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

Die Anwendung kann anschließend aus der Entwicklungsumgebung gestartet werden:

```bash
openbilanz
```

Die Tests werden mit `pytest` ausgeführt:

```bash
pytest
```

## macOS-Auslieferung

Für macOS wird SimpleOB mit PyInstaller als eigenständige Anwendung gebaut.

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

## Datenhaltung und Aktualisierungen

SimpleOB speichert seine produktiven Daten lokal.

Die Datenbankstruktur wird mit Alembic versioniert. Bei notwendigen Schemaaktualisierungen führt SimpleOB die vorgesehenen Migrationen beim Start aus.

Vor einer tatsächlichen Migration einer bestehenden SQLite-Datenbank wird automatisch eine Sicherungskopie angelegt.

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
- lokale Datenhaltung
- möglichst geringe unnötige Komplexität

E-Bilanz- und Taxonomiefunktionalität wird gezielt auf den für die technisch valide und tatsächlich übermittelbare E-Bilanz erforderlichen Umfang begrenzt.

## Projektstatus

SimpleOB befindet sich weiterhin in Entwicklung.

Vor dem produktiven Einsatz sollten insbesondere die erzeugten Abschlüsse, E-Bilanz-Daten und ELSTER-Übermittlungen fachlich geprüft werden.

# SimpleOB – Benutzerhandbuch

## 1. Über SimpleOB

SimpleOB ist eine lokale Buchhaltungs- und E-Bilanz-Anwendung für kleine
Kapitalgesellschaften, insbesondere für kleine Unternehmergesellschaften
(haftungsbeschränkt).

Die Anwendung unterstützt die laufende Buchführung und führt die erfassten
Daten bis zum Jahresabschluss, zur Bilanz und Gewinn- und Verlustrechnung
sowie zur E-Bilanz weiter.

Zu den Funktionen gehören insbesondere:

- Verwaltung von Mandanten und Geschäftsjahren,
- Verwaltung eines mandantenspezifischen Kontenrahmens,
- Erfassung von Buchungen,
- Anlagenbuchhaltung,
- Erstellung von Bilanz und Gewinn- und Verlustrechnung,
- Unterstützung des Jahresabschlusses,
- Erstellung der E-Bilanz,
- Prüfung der E-Bilanz,
- Testübermittlung und produktive Übermittlung der E-Bilanz über ELSTER.

SimpleOB ist eine Desktop-Anwendung. Die Buchhaltungsdaten werden lokal
gespeichert.

### 1.1 Eigenverantwortliche Verwendung

SimpleOB unterstützt den Anwender bei Buchführung, Jahresabschluss und
E-Bilanz. Die Anwendung ersetzt keine steuerliche oder rechtliche Beratung.

Der Anwender bleibt für die sachliche Richtigkeit und Vollständigkeit der
erfassten Daten sowie für die Prüfung der zu übermittelnden E-Bilanz
verantwortlich.


## 2. Installation unter macOS

### 2.1 Installation

SimpleOB wird als macOS-Anwendung `SimpleOB.app` bereitgestellt.

Die Anwendung kann beispielsweise in den Ordner `Programme` kopiert und
von dort gestartet werden.

Die persönlichen Anwendungs- und Buchhaltungsdaten befinden sich nicht
innerhalb von `SimpleOB.app`. Eine vorhandene Datenbank wird deshalb beim
Austausch der Anwendung gegen eine neuere Programmversion nicht durch das
App-Bundle ersetzt.

### 2.2 SimpleOB beim ersten Start unter macOS freigeben

SimpleOB wird derzeit nicht über den Mac App Store vertrieben und ist nicht von Apple notarisiert.

macOS kann deshalb beim ersten Start verhindern, dass `SimpleOB.app` unmittelbar geöffnet wird. Dies ist eine Schutzfunktion von macOS (Gatekeeper) und bedeutet für sich allein nicht, dass die Anwendung beschädigt ist.

SimpleOB sollte nur freigegeben werden, wenn die Anwendung aus der vorgesehenen und vertrauenswürdigen Bezugsquelle stammt.

Gehen Sie beim ersten Start wie folgt vor:

1. Verschieben Sie `SimpleOB.app` in den Ordner **Programme**, sofern dies noch nicht geschehen ist.

2. Versuchen Sie, **SimpleOB** zu öffnen.

3. Wenn macOS den Start aus Sicherheitsgründen verhindert, schließen Sie die angezeigte Meldung.

4. Öffnen Sie über das Apple-Menü die **Systemeinstellungen**.

5. Wählen Sie **Datenschutz & Sicherheit**.

6. Scrollen Sie im Fenster nach unten zum Bereich **Sicherheit**.

7. Dort sollte ein Hinweis erscheinen, dass das Öffnen von SimpleOB blockiert wurde. Wählen Sie **Dennoch öffnen**.

8. macOS zeigt erneut eine Sicherheitsabfrage an. Prüfen Sie, dass sich diese auf SimpleOB bezieht, und wählen Sie **Öffnen**, wenn Sie die Anwendung aus der vorgesehenen vertrauenswürdigen Quelle erhalten haben.

macOS speichert diese Entscheidung als Ausnahme für die betreffende Anwendung. SimpleOB kann anschließend normalerweise wie andere Anwendungen durch Doppelklick gestartet werden.

> **Wichtig:** Für die Verwendung von SimpleOB ist es nicht erforderlich, Gatekeeper generell zu deaktivieren oder die Sicherheitseinstellungen von macOS dauerhaft herabzusetzen.

Die Möglichkeit **Dennoch öffnen** erscheint erst, nachdem zuvor versucht wurde, die von macOS blockierte Anwendung zu starten.

Auf zentral verwalteten Macs kann die Freigabe nicht verfügbar sein, wenn die Sicherheitseinstellungen durch eine Organisation oder einen Administrator vorgegeben werden. In diesem Fall ist die zuständige Administration zu kontaktieren.


## 3. Anwendungsdaten und Datensicherung

### 3.1 Speicherort

SimpleOB speichert seine Anwendungsdaten unter macOS im Benutzerverzeichnis:

`~/Library/Application Support/SimpleOB/`

Dort befinden sich insbesondere die Datenbank und die
Anwendungskonfiguration.

Die Daten liegen damit getrennt von `SimpleOB.app`.

### 3.2 Datenbank

Die Buchhaltungsdaten werden gegenwärtig in einer lokalen SQLite-Datenbank
gespeichert:

`~/Library/Application Support/SimpleOB/openbilanz.db`

Diese Datei enthält die für SimpleOB gespeicherten Buchhaltungsdaten und
sollte in eine regelmäßige persönliche Datensicherung einbezogen werden.

### 3.3 Konfiguration

Anwendungseinstellungen werden unter anderem in

`~/Library/Application Support/SimpleOB/config.toml`

gespeichert.

Dazu gehören beispielsweise die für die ELSTER-Anbindung benötigten
gespeicherten Einstellungen.

Die PIN des ELSTER-Zertifikats wird von SimpleOB nicht dauerhaft in dieser
Konfigurationsdatei gespeichert.

### 3.4 Eigene Datensicherung

Die automatische Sicherung vor einer notwendigen Datenbankmigration
ersetzt keine regelmäßige Datensicherung durch den Anwender.

Insbesondere vor größeren Änderungen oder Programmaktualisierungen ist
eine zusätzliche Sicherung des Verzeichnisses

`~/Library/Application Support/SimpleOB/`

empfehlenswert.


## 4. Programmaktualisierungen

Eine neue Version von SimpleOB kann das bisherige `SimpleOB.app` ersetzen.
Die vorhandenen Anwendungsdaten befinden sich außerhalb des App-Bundles
und werden dadurch nicht ersetzt.

### 4.1 Datenbankaktualisierung

Benötigt eine neue SimpleOB-Version eine Änderung der Datenbankstruktur,
wird die Datenbank beim Programmstart auf die benötigte Struktur
aktualisiert.

Vor einer tatsächlich erforderlichen Datenbankmigration erstellt SimpleOB
automatisch eine Sicherung der bestehenden SQLite-Datenbank.

Die Sicherungsdatei befindet sich neben der eigentlichen Datenbank und
trägt den Namen:

`openbilanz-before-migration.db`

Ist die Datenbank bereits auf dem von der installierten SimpleOB-Version
benötigten Stand, wird keine unnötige Migrationssicherung erzeugt.

### 4.2 Wenn ein Update der Datenbank nicht erfolgreich abgeschlossen wird

Kann die Sicherung nicht erfolgreich erstellt werden, beginnt SimpleOB
die Datenbankmigration nicht.

Erkennt SimpleOB eine ältere Datenbank ohne Versionsinformation, wird
diese nur dann automatisch übernommen, wenn ihre Struktur einer
bekannten älteren SimpleOB-Datenbank entspricht. Eine unbekannte
Datenbankstruktur wird nicht automatisch verändert.

Tritt während eines Programmupdates ein Fehler bei der
Datenbankmigration auf, sollten keine manuellen Änderungen an
`openbilanz.db` vorgenommen werden.

Insbesondere sollte
`openbilanz-before-migration.db` nicht vorschnell über
`openbilanz.db` kopiert werden.

Stattdessen sollten zunächst beide Datenbankdateien sowie die übrigen
Anwendungsdaten gesichert werden. Danach kann anhand der konkreten
Fehlermeldung beziehungsweise der Ausgabe beim Programmstart geklärt
werden, an welcher Stelle die Migration fehlgeschlagen ist.

> **Wichtig:** Die Datei `openbilanz-before-migration.db` ist eine
> Sicherheitskopie des Datenbestands unmittelbar vor der vorgesehenen
> Datenbankmigration. Sie sollte bei einem Migrationsproblem zunächst
> unverändert aufbewahrt werden.

Eine gezielte Wiederherstellung aus dieser Sicherung sollte erst
erfolgen, wenn geklärt ist, welche Programmversion und welcher
Datenbankstand zusammengehören.

Weitere Hinweise zum Vorgehen bei Start- und Datenbankproblemen enthält
Kapitel 15.


## 5. ELSTER einrichten

Für die Übermittlung einer E-Bilanz über ELSTER benötigt SimpleOB ein
geeignetes ELSTER-Zertifikat sowie die erforderlichen Angaben zum
Datenlieferanten.

### 5.1 ELSTER-Zertifikat

Der Pfad zum ELSTER-Zertifikat wird in SimpleOB über die Einstellungen
festgelegt.

Der eingestellte Zertifikatspfad wird gespeichert und steht bei späteren
Programmstarts wieder zur Verfügung.

Das Zertifikat selbst wird dadurch nicht in die SimpleOB-Datenbank
übernommen.

Für Übungs- und Testzwecke wird mit SimpleOB zusätzlich das
ELSTER-Testzertifikat

`test-softidnr-pse.pfx`

bereitgestellt. Das Testzertifikat wird als separate Datei zusammen mit
SimpleOB ausgeliefert und nicht automatisch eingerichtet.

Der Benutzer kann das Testzertifikat über denselben Einstellungsdialog
auswählen, über den später auch das persönliche ELSTER-Zertifikat
eingerichtet wird. Dadurch kann der vollständige Ablauf der
Zertifikatseinrichtung vor einer produktiven Übermittlung praktisch
erprobt werden.

Das Testzertifikat ist ausschließlich für Testübermittlungen vorgesehen.
Vor einer produktiven ELSTER-Übermittlung muss in SimpleOB das persönliche
ELSTER-Zertifikat des Benutzers ausgewählt werden.

### 5.2 ELSTER-Datenlieferant

Für die E-Bilanz-Übermittlung benötigt ELSTER Angaben zum Datenlieferanten.

Diese Angaben werden in SimpleOB unter den ELSTER-Einstellungen erfasst.
Dazu gehören:

- Name des Erstellers,
- Straße,
- Hausnummer,
- Hausnummerzusatz,
- Adresszusatz,
- Postleitzahl,
- Ort,
- Land,
- Telefon,
- E-Mail-Adresse.

Der Datenlieferant ist nicht mit dem Mandanten und auch nicht mit dem
Softwarehersteller gleichzusetzen.

### 5.3 PIN des ELSTER-Zertifikats

Die PIN des ELSTER-Zertifikats wird von SimpleOB nicht dauerhaft
gespeichert.

Unmittelbar vor einer ELSTER-Übermittlung fordert SimpleOB die PIN in
einem verdeckten Eingabefeld an. Sie wird nur für den jeweiligen
Übermittlungsvorgang verwendet.

### 5.4 Testübermittlung

Vor einer produktiven Übermittlung kann eine ELSTER-Testübermittlung
durchgeführt werden.

Damit kann der technische Übermittlungsweg geprüft werden, ohne die
E-Bilanz als produktive Übermittlung einzureichen.

Für einen vollständigen Praxistest kann das mit SimpleOB ausgelieferte
ELSTER-Testzertifikat

`test-softidnr-pse.pfx`

verwendet werden.

Dazu wird das Testzertifikat zunächst unter

**Einstellungen → ELSTER-Zertifikat…**

ausgewählt. Die Einrichtung erfolgt damit auf demselben Weg wie später
bei einem persönlichen ELSTER-Zertifikat.

Die PIN des mitgelieferten Testzertifikats lautet:

**123456**

Die PIN wird nicht in SimpleOB hinterlegt. Sie wird bei der
Testübermittlung manuell in den von SimpleOB angezeigten PIN-Dialog
eingegeben.

Nach dem Praxistest sollte der Benutzer daran denken, vor einer
produktiven Übermittlung das Testzertifikat durch sein persönliches
ELSTER-Zertifikat zu ersetzen.

Der vollständige Ablauf einer ELSTER-Testübermittlung ist in
Kapitel 13 beschrieben.

### 5.5 Produktive Übermittlung

Vor einer produktiven ELSTER-Übermittlung verlangt SimpleOB eine
ausdrückliche Bestätigung.

Anschließend werden die notwendigen ELSTER-Daten geprüft, die PIN des
Zertifikats abgefragt und die Übermittlung durchgeführt.

Der Anwender sollte das Ergebnis der Übermittlung kontrollieren und die
von SimpleOB bereitgestellten Übermittlungsinformationen aufbewahren.


## 6. Mandanten

SimpleOB kann mehrere Unternehmen getrennt voneinander verwalten.
Beim Programmstart wird ausgewählt, welche Buchhaltung und welches
Geschäftsjahr geöffnet werden sollen.

### 6.1 Vorhandene Buchhaltung öffnen

Nach dem Start zeigt SimpleOB den Dialog **„Buchhaltung öffnen“**.

Unter **„Unternehmen“** wird die gewünschte Buchhaltung ausgewählt.
Anschließend kann unter **„Geschäftsjahr“** eines der für dieses
Unternehmen vorhandenen Geschäftsjahre ausgewählt werden.

Mit **„Öffnen“** wird die ausgewählte Buchhaltung für dieses
Geschäftsjahr geöffnet.

Ist für das ausgewählte Unternehmen noch kein Geschäftsjahr vorhanden,
kann die Buchhaltung erst geöffnet werden, nachdem ein Geschäftsjahr
angelegt wurde.

### 6.2 Neue Buchhaltung anlegen

Eine neue Buchhaltung wird im Startdialog mit
**„Neue Buchhaltung anlegen“** angelegt.

SimpleOB fragt zunächst folgende Angaben ab:

- Unternehmensname,
- Beginn des ersten Geschäftsjahres,
- Ende des ersten Geschäftsjahres.

Datumsangaben können im Format `TT.MM.JJJJ` eingegeben werden.
SimpleOB akzeptiert außerdem Eingaben in den Formen `TTMMJJJJ`
und `TTMMJJ` und normalisiert gültige Eingaben.

Mit **„Buchhaltung anlegen“** werden das neue Unternehmen und sein
erstes Geschäftsjahr angelegt und anschließend geöffnet.

Die weiteren Unternehmens- und Steuerdaten werden nicht in diesem
ersten Dialog erfasst. Sie werden anschließend über die
Unternehmensstammdaten gepflegt.

### 6.3 Unternehmensstammdaten

Nach dem Öffnen einer Buchhaltung können die
**Unternehmensstammdaten** aufgerufen und bearbeitet werden.

Dort stehen folgende Angaben zur Verfügung:

- Rechtsform,
- Steuernummer,
- Finanzamt,
- Steuer-ID,
- Wirtschafts-ID,
- BF4,
- Straße,
- Hausnummer,
- Postleitzahl,
- Ort,
- Land,
- Geschäftstätigkeit,
- Bundesland.

Die mit `*` gekennzeichneten Angaben sind Pflichtfelder für die
E-Bilanz. Dies betrifft derzeit:

- Rechtsform,
- Steuernummer,
- Straße,
- Hausnummer,
- Postleitzahl,
- Ort,
- Land,
- Geschäftstätigkeit,
- Bundesland.

Mit **„Speichern“** werden die geänderten Unternehmensstammdaten
übernommen.

Ungültige Stammdaten werden von SimpleOB beim Speichern zurückgewiesen.
Die angezeigte Fehlermeldung enthält einen Hinweis auf die beanstandete
Eingabe.

Änderungen an den Unternehmensstammdaten wirken sich auch auf die
E-Bilanz aus. Eine bereits vorbereitete E-Bilanz sollte deshalb nach
einer Änderung der Stammdaten erneut erstellt und geprüft werden.

### 6.4 Mandant und Datenlieferant sind unterschiedliche Angaben

Die Unternehmensstammdaten beschreiben das Unternehmen, für das die
Buchhaltung und E-Bilanz erstellt werden.

Der unter den ELSTER-Einstellungen erfasste **Datenlieferant** bezeichnet
dagegen den Ersteller beziehungsweise Lieferanten der an ELSTER
übermittelten Daten.

Beide Angaben können daher voneinander abweichen und werden in SimpleOB
getrennt verwaltet.

### 6.5 Weitere Geschäftsjahre

Weitere Geschäftsjahre können im Startdialog für das ausgewählte
Unternehmen über **„Neues Geschäftsjahr“** angelegt werden.

Die Einzelheiten dazu werden im folgenden Kapitel beschrieben.

### 6.6 Mandanten importieren und exportieren

SimpleOB unterstützt den Austausch vollständiger Mandanten über
portable `.simpleob`-Dateien.

Import und Export werden in Kapitel 14 **„Datenaustausch“** beschrieben.

## 7. Geschäftsjahre

Die Buchhaltung eines Unternehmens wird in SimpleOB nach Geschäftsjahren
getrennt geführt.

Beim Öffnen einer Buchhaltung wird deshalb neben dem Unternehmen auch das
zu bearbeitende Geschäftsjahr ausgewählt.

### 7.1 Vorhandenes Geschäftsjahr öffnen

Im Startdialog werden nach Auswahl eines Unternehmens die für dieses
Unternehmen vorhandenen Geschäftsjahre angezeigt.

Das gewünschte Geschäftsjahr auswählen und anschließend
**„Öffnen“** wählen.

Das aktuell geöffnete Geschäftsjahr wird auch im Hauptfenster von
SimpleOB angezeigt.

### 7.2 Neues Geschäftsjahr anlegen

Im Startdialog zunächst das gewünschte Unternehmen auswählen und
anschließend **„Neues Geschäftsjahr“** wählen.

Für das neue Geschäftsjahr werden erfasst:

- Beginn,
- Ende.

SimpleOB schlägt als Voreinstellung das Kalenderjahr vor, das auf das
zuletzt vorhandene Geschäftsjahr folgt.

Die vorgeschlagenen Daten können vor dem Anlegen geändert werden.

Datumsangaben werden im Format `TT.MM.JJJJ` dargestellt.

Mit **„Geschäftsjahr anlegen“** wird das neue Geschäftsjahr angelegt.

### 7.3 Unmittelbares Vorjahr

Beim Anlegen prüft SimpleOB, ob für das neue Geschäftsjahr ein unmittelbar
vorhergehendes Geschäftsjahr vorhanden ist.

Als unmittelbares Vorjahr gilt dabei ein Geschäftsjahr, dessen Enddatum
genau einen Tag vor dem Beginn des neuen Geschäftsjahres liegt.

Nur ein solches unmittelbar vorhergehendes Geschäftsjahr kann für die
automatische Übernahme von Vorjahressalden verwendet werden.

### 7.4 Vorjahr ist noch nicht abgeschlossen

Ist das unmittelbar vorhergehende Geschäftsjahr noch nicht abgeschlossen,
können dessen Schlussbestände noch nicht als Eröffnungswerte übernommen
werden.

SimpleOB weist in diesem Fall darauf hin und fragt, ob das neue
Geschäftsjahr trotzdem ohne Saldenübernahme angelegt werden soll.

Der Anwender kann:

- das neue Geschäftsjahr ohne Saldenübernahme anlegen oder
- den Vorgang abbrechen.

Soll eine Saldenübernahme erfolgen, sollte zunächst das vorhergehende
Geschäftsjahr abgeschlossen werden.

### 7.5 Vorjahressalden übernehmen

Ist das unmittelbar vorhergehende Geschäftsjahr abgeschlossen, fragt
SimpleOB beim Anlegen des neuen Geschäftsjahres, ob dessen Schlussbestände
als Eröffnungswerte übernommen werden sollen.

Es stehen drei Möglichkeiten zur Verfügung:

- **Ja** – Vorjahressalden übernehmen,
- **Nein** – neues Geschäftsjahr ohne Saldenübernahme anlegen,
- **Abbrechen** – Geschäftsjahr nicht anlegen.

Bei Auswahl von **„Ja“** wird das abgeschlossene unmittelbare Vorjahr als
Quelle für die Eröffnungswerte des neuen Geschäftsjahres verwendet.

### 7.6 Geschäftsjahr ohne Vorjahr

Existiert kein unmittelbar vorhergehendes Geschäftsjahr, kann das neue
Geschäftsjahr ohne automatische Saldenübernahme angelegt werden.

Dies kann beispielsweise beim ersten in SimpleOB geführten Geschäftsjahr
eines bereits bestehenden Unternehmens erforderlich sein.

Die notwendigen Eröffnungswerte müssen in diesem Fall auf andere Weise
erfasst werden.

### 7.7 Abschluss eines Geschäftsjahres

Ein Geschäftsjahr kann in SimpleOB einen offenen oder abgeschlossenen
Status haben.

Der Abschluss eines Geschäftsjahres ist ein eigener Arbeitsablauf.
Nach dem Abschluss sind weitere Buchungen in diesem Geschäftsjahr nicht
mehr möglich.

Der vollständige Ablauf wird in Kapitel 11 **„Jahresabschluss“**
beschrieben.


## 8. Konten und Kontenrahmen

SimpleOB verwendet für jeden Mandanten einen Kontenrahmen. Die Konten
werden nicht nur für Buchungen verwendet, sondern sind auch mit den
Positionen von Bilanz und Gewinn- und Verlustrechnung verbunden.

Darüber hinaus können bestimmte Konten besondere Funktionen übernehmen,
beispielsweise als Umsatzsteuerkonto, Eröffnungsbilanzkonto oder
Bankkonto.

### 8.1 Kontenübersicht

Im Arbeitsbereich **„Konten“** zeigt SimpleOB die Kontenübersicht des
geöffneten Mandanten.

Für jedes Konto werden angezeigt:

- Kontonummer,
- Bezeichnung,
- Soll,
- Haben,
- Saldo,
- E-Bilanz-Zuordnung.

Oberhalb der Tabelle wird außerdem die Anzahl der Buchungen im Journal
angezeigt.

Ein Konto kann in der Tabelle ausgewählt und anschließend bearbeitet
oder – soweit verfügbar – einer feineren E-Bilanz-Taxonomieposition
zugeordnet werden.

### 8.2 Neues Konto anlegen

Solange das Geschäftsjahr offen ist, kann über **„Neues Konto“** ein
weiteres Konto angelegt werden.

Für ein Konto werden folgende Angaben erfasst:

- Kontonummer,
- Bezeichnung,
- Kontotyp,
- HGB-Zuordnung Soll,
- HGB-Zuordnung Haben,
- Aktivstatus.

Als Kontotypen stehen zur Verfügung:

- Aktivkonto,
- Passivkonto,
- Eigenkapital,
- Ertragskonto,
- Aufwandskonto.

Die auswählbaren HGB-Positionen richten sich nach dem gewählten
Kontotyp.

Die HGB-Struktur selbst wird dabei nicht verändert. Das Konto wird
lediglich einer bereits vorhandenen HGB-Position zugeordnet.

Für Ertragskonten ist eine Haben-HGB-Zuordnung erforderlich.

Für Aufwandskonten ist eine Soll-HGB-Zuordnung erforderlich.

Für Aktiv-, Passiv- und Eigenkapitalkonten muss mindestens eine
HGB-Zuordnung vorhanden sein.

Nach dem Anlegen eines Kontos fordert SimpleOB dazu auf, die Buchhaltung
zu schließen und erneut zu öffnen. Erst danach ist der geänderte
Kontenrahmen in allen Bereichen vollständig wirksam.

### 8.3 Konto bearbeiten

Ein vorhandenes Konto in der Kontenübersicht auswählen und
**„Konto bearbeiten“** wählen.

Bearbeitet werden können insbesondere:

- Bezeichnung,
- Kontotyp,
- HGB-Zuordnung,
- Aktivstatus.

Die Kontonummer eines bereits vorhandenen Kontos kann nicht geändert
werden.

Nach einer Änderung sollte die Buchhaltung geschlossen und erneut
geöffnet werden, damit der geänderte Kontenrahmen vollständig wirksam
wird.

Bestimmte technische Steuerungskonten können nicht über die normale
Kontenbearbeitung geändert werden. Dazu gehören insbesondere die
entsprechend konfigurierten Abschluss- und Umsatzsteuerkonten.

Ihre Funktion wird über die Kontenkonfiguration festgelegt.

### 8.4 Aktive und inaktive Konten

Ein Konto kann als aktiv oder inaktiv gekennzeichnet werden.

Die Einstellung erfolgt beim Anlegen oder Bearbeiten des Kontos über
**„Konto ist aktiv“**.

Für die Kontenkonfiguration werden nur aktive Konten zur Auswahl
angeboten.

### 8.5 Mandantenspezifische Kontenkonfiguration

Über **„Kontenkonfiguration“** werden Konten festgelegt, denen SimpleOB
besondere Funktionen zuordnet.

Diese Einstellungen gelten für den aktuell geöffneten Mandanten.

Der Dialog ist in drei Bereiche gegliedert:

- Systemkonten,
- USt-Konten,
- Kontenrollen.

Mit **„Übernehmen“** wird die geänderte Konfiguration gespeichert.

### 8.6 Systemkonten

Unter **„Systemkonten“** werden die Konten ausgewählt, die SimpleOB für
bestimmte automatische Buchungs- und Abschlussvorgänge verwendet.

Konfiguriert werden:

- Eröffnungsbilanzkonto,
- GuV-Sammelkonto,
- Jahresüberschuss,
- Jahresfehlbetrag,
- Gewinn-/Verlustvortrag,
- Gesetzliche Rücklage,
- Andere Gewinnrücklagen,
- Verbindlichkeiten für offene Ausschüttungen,
- Abschreibungsaufwand,
- Gewinn aus Anlagenabgang,
- Verlust aus Anlagenabgang.

Für jede Funktion muss ein vorhandenes Konto ausgewählt werden.

Diese Zuordnungen sollten nur geändert werden, wenn das ausgewählte
Konto fachlich für die betreffende Funktion vorgesehen ist.

### 8.7 Umsatzsteuerkonten

Unter **„USt-Konten“** werden die Konten für die automatische
Umsatzsteuerbehandlung festgelegt.

Konfiguriert werden:

- Vorsteuer 7 %,
- Vorsteuer 19 %,
- Umsatzsteuer 7 %,
- Umsatzsteuer 19 %.

SimpleOB verwendet diese Zuordnungen bei Buchungen, bei denen die
entsprechende Umsatzsteuerbehandlung automatisch erfolgt.

Die hier festgelegten Konten werden als technische Steuerungskonten
behandelt und können nicht über die normale Kontenbearbeitung geändert
werden.

### 8.8 Kontenrollen

Unter **„Kontenrollen“** können Konten bestimmten fachlichen Funktionen
zugeordnet werden.

Derzeit stehen folgende Rollen zur Verfügung:

- Kasse,
- Bank,
- Umsatzerlöse allgemeiner Steuersatz.

Einer Rolle können mehrere Konten zugeordnet werden. Dadurch können
beispielsweise mehrere Bankkonten oder mehrere Kassenkonten verwendet
werden.

Ein Konto darf jedoch nur einer dieser Rollen angehören.

Die Kontenrollen ermöglichen SimpleOB, Konten nach ihrer tatsächlichen
Funktion zu unterscheiden, ohne diese Funktion an eine bestimmte
Kontonummer zu binden.

### 8.9 HGB-Zuordnung und E-Bilanz-Zuordnung

Die HGB-Zuordnung eines Kontos und seine E-Bilanz-Zuordnung erfüllen
unterschiedliche Aufgaben.

Die **HGB-Zuordnung** wird beim Anlegen oder Bearbeiten des Kontos
festgelegt. Sie bestimmt, welcher Position der Bilanz oder Gewinn- und
Verlustrechnung das Konto zugeordnet wird.

Für einzelne HGB-Positionen kann die E-Bilanz-Taxonomie eine feinere
Untergliederung vorsehen. In diesem Fall kann für das ausgewählte Konto
über **„E-Bilanz-Zuordnung“** eine solche feinere Zuordnung festgelegt
werden.

SimpleOB bietet dabei nur die E-Bilanz-Positionen zur Auswahl an, die
für die HGB-Zuordnung des betreffenden Kontos zur Verfügung stehen.

Steht für die HGB-Zuordnung keine feinere E-Bilanz-Position zur
Verfügung, weist SimpleOB darauf hin.

Eine vorhandene feinere E-Bilanz-Zuordnung kann mit
**„Zuordnung entfernen“** wieder aufgehoben werden.

Die grundlegende HGB-Zuordnung des Kontos bleibt davon unberührt.

### 8.10 Änderungen am Kontenrahmen mit Bedacht vornehmen

Konten, HGB-Zuordnungen, Systemkonten, Umsatzsteuerkonten und
Kontenrollen beeinflussen verschiedene automatische Abläufe in
SimpleOB.

Änderungen sollten deshalb fachlich geprüft werden. Insbesondere sollte
ein Konto nicht allein aufgrund seiner Kontonummer einer bestimmten
Funktion zugeordnet werden. Maßgeblich ist die tatsächliche
buchhalterische Funktion des Kontos.

Nach dem Anlegen oder Bearbeiten eines Kontos sollte die Buchhaltung
geschlossen und erneut geöffnet werden, bevor mit dem geänderten
Kontenrahmen weitergearbeitet wird.


## 9. Buchungen

Im Arbeitsbereich **„Buchen“** werden die laufenden Geschäftsvorfälle
des geöffneten Geschäftsjahres erfasst.

SimpleOB stellt dafür zwei Buchungsarten zur Verfügung:

- Einfache Buchung,
- Rechnung mit Umsatzsteuer.

Die gewünschte Erfassungsart wird unter **„Buchungsart“** ausgewählt.

Buchungen können nur in einem offenen Geschäftsjahr erfasst werden.
Nach dem Abschluss eines Geschäftsjahres ist die Buchungserfassung
gesperrt.

### 9.1 Einfache Buchung

Die Buchungsart **„Einfache Buchung“** dient zur unmittelbaren Erfassung
eines Buchungssatzes.

Im oberen Bereich werden erfasst:

- Datum,
- Belegnummer,
- Buchungstext.

Darunter werden die einzelnen Buchungszeilen eingegeben.

Für jede Buchungszeile stehen zur Verfügung:

- Konto,
- Kontoname,
- Soll,
- Haben,
- Einlage.

Das Konto kann über seine Kontonummer beziehungsweise über die
angezeigte Kontobezeichnung ausgewählt werden. Bei der Eingabe unterstützt
SimpleOB die Suche nach vorhandenen Konten.

Für eine Buchungszeile wird der Betrag entweder im Soll oder im Haben
eingetragen.

### 9.2 Mehrzeilige Buchungen

Eine einfache Buchung kann aus mehr als zwei Buchungszeilen bestehen.

SimpleOB fügt während der Erfassung die erforderlichen Buchungszeilen
hinzu. Nicht benötigte Zeilen können über die Schaltfläche **„×“**
entfernt werden.

Unterhalb der Buchungszeilen zeigt SimpleOB laufend:

- Summe Soll,
- Summe Haben,
- Differenz.

Eine Buchung muss in Soll und Haben ausgeglichen sein, bevor sie
übernommen werden kann.

Mit **„Buchung übernehmen“** wird der vollständige Buchungssatz
verbucht.

Nach erfolgreicher Übernahme meldet SimpleOB:

**„Buchung wurde übernommen.“**

Die Eingabemaske wird anschließend für die nächste Buchung geleert.

### 9.3 Beträge und Datum

Beträge werden in deutscher Schreibweise eingegeben, beispielsweise:

`1.234,56`

Buchungsbeträge müssen größer als `0,00` sein.

Das Buchungsdatum wird in der Oberfläche im Format `TT.MM.JJJJ`
dargestellt. Gültige Datumseingaben werden von SimpleOB beim Verlassen
des Feldes normalisiert.

### 9.4 Kennzeichnung einer Einlage

Bei bestimmten Eigenkapitalkonten kann in einer Habenzeile die
Kennzeichnung **„Einlage“** verwendet werden.

Damit wird die betreffende Buchungszeile als Einlage für den
Betriebsvermögensvergleich gekennzeichnet.

Die Kennzeichnung steht nur bei dafür vorgesehenen Konten und
Buchungszeilen zur Verfügung.

Sie sollte nur gesetzt werden, wenn der betreffende Geschäftsvorfall
tatsächlich eine entsprechende Einlage darstellt.

### 9.5 Rechnungen mit Umsatzsteuer

Für Rechnungen, bei denen SimpleOB die Umsatzsteuer automatisch
berücksichtigen soll, wird als Buchungsart
**„Rechnung mit Umsatzsteuer“** gewählt.

Folgende Rechnungsarten stehen zur Verfügung:

- Eingangsrechnung,
- Ausgangsrechnung,
- Kundengutschrift,
- Lieferantengutschrift.

Für die Rechnung werden erfasst:

- Rechnungsart,
- Datum,
- Belegnummer,
- Buchungstext,
- Gegenkonto.

Anschließend werden die einzelnen Rechnungspositionen eingegeben.

### 9.6 Rechnungspositionen

Jede Rechnungsposition enthält:

- Sachkonto,
- Bruttobetrag,
- Umsatzsteuersatz.

Als Umsatzsteuersätze stehen zur Verfügung:

- 0 %,
- 7 %,
- 19 %.

Beim Anlegen einer Position ist 19 % voreingestellt.

Über **„Position hinzufügen“** können weitere Rechnungspositionen
angelegt werden.

Über **„Letzte Position entfernen“** kann die zuletzt angelegte
Position wieder entfernt werden. Mindestens eine Rechnungsposition
bleibt erhalten.

Dadurch können auch Rechnungen mit mehreren Sachkonten oder
unterschiedlichen Umsatzsteuersätzen in einer Buchung erfasst werden.

### 9.7 Gegenkonto

Das Gegenkonto wird einmal für die gesamte Rechnung ausgewählt.

Je nach Geschäftsvorfall kann dies beispielsweise ein Debitoren-,
Kreditoren-, Bank- oder anderes geeignetes Gegenkonto sein.

Das Gegenkonto darf nicht zugleich als Sachkonto derselben
Rechnungsposition verwendet werden.

SimpleOB bietet bei der Rechnungserfassung nur Konten an, die für
diesen Buchungsweg zur Verfügung stehen. Die in der
Kontenkonfiguration festgelegten technischen Umsatzsteuerkonten werden
nicht als normale Sach- oder Gegenkonten angeboten.

### 9.8 Eingangsrechnungen

Für eine Eingangsrechnung wird die Rechnungsart
**„Eingangsrechnung“** gewählt.

Als Sachkonten der Rechnungspositionen sind dabei Aufwands- und
Aktivkonten vorgesehen.

Für jede Position wird der Bruttobetrag und der zutreffende
Umsatzsteuersatz angegeben.

SimpleOB erzeugt daraus die erforderliche Buchung unter Verwendung der
in der Kontenkonfiguration hinterlegten Vorsteuerkonten.

### 9.9 Ausgangsrechnungen

Für eine Ausgangsrechnung wird die Rechnungsart
**„Ausgangsrechnung“** gewählt.

Die Rechnungspositionen enthalten das jeweilige Sachkonto, den
Bruttobetrag und den Umsatzsteuersatz.

SimpleOB erzeugt daraus die erforderliche Buchung unter Verwendung der
in der Kontenkonfiguration hinterlegten Umsatzsteuerkonten.

### 9.10 Gutschriften

SimpleOB unterscheidet bei der Rechnungserfassung zwischen:

- **Kundengutschrift**,
- **Lieferantengutschrift**.

Dadurch kann die umsatzsteuerliche Buchung einer Gutschrift über
denselben Erfassungsbereich wie die zugehörigen Rechnungen vorgenommen
werden.

Bei Lieferantengutschriften sind für die Rechnungspositionen – wie bei
Eingangsrechnungen – Aufwands- und Aktivkonten vorgesehen.

### 9.11 Automatische Umsatzsteuerkonten

Die für 7 % und 19 % hinterlegten Vorsteuer- und Umsatzsteuerkonten
werden nicht bei jeder Rechnung manuell ausgewählt.

SimpleOB verwendet dafür die unter **„Kontenkonfiguration“ →
„USt-Konten“** festgelegten Konten.

Dort werden getrennt konfiguriert:

- Vorsteuer 7 %,
- Vorsteuer 19 %,
- Umsatzsteuer 7 %,
- Umsatzsteuer 19 %.

Bei Änderungen dieser Konten ist deshalb darauf zu achten, dass die
ausgewählten Konten fachlich für die jeweilige Steuerfunktion bestimmt
sind.

### 9.12 Buchung übernehmen

Die Schaltfläche **„Buchung übernehmen“** wird erst verfügbar, wenn die
für den jeweiligen Buchungsweg erforderlichen Eingaben vollständig und
gültig sind.

Nach der Übernahme wird die Buchung im geöffneten Geschäftsjahr
gespeichert. Die Kontensalden, das Journal sowie die daraus abgeleiteten
Auswertungen werden anschließend aktualisiert.

Die Meldung **„Buchung wurde übernommen.“** bestätigt die erfolgreiche
Übernahme.

### 9.13 Abgeschlossenes Geschäftsjahr

Nach dem Abschluss eines Geschäftsjahres können keine weiteren
laufenden Buchungen erfasst werden.

SimpleOB sperrt sowohl die einfache Buchung als auch die
Rechnungserfassung und zeigt den Hinweis:

**„Das Geschäftsjahr ist abgeschlossen. Buchungen sind nicht mehr
möglich.“**

Der Abschluss eines Geschäftsjahres wird in Kapitel 11
**„Jahresabschluss“** beschrieben.

## 10. Anlagenbuchhaltung

SimpleOB enthält eine Anlagenbuchhaltung für die Erfassung und
Fortschreibung von Anlagegütern. Sie ist mit der Finanzbuchhaltung
verbunden, behandelt Anlagegut und Finanzbuchung jedoch als getrennte
Sachverhalte.

Ein Anlagegut wird daher zunächst in der Anlagenbuchhaltung erfasst.
Die zugehörige Anschaffungsbuchung wird anschließend dem Anlagegut
zugeordnet.

SimpleOB berechnet außerdem die linearen Abschreibungen und unterstützt
den Verkauf bzw. Abgang eines Anlageguts.

### 10.1 Anlagenübersicht

Im Arbeitsbereich **Anlagegüter** werden die für den ausgewählten
Mandanten erfassten Anlagegüter angezeigt.

Die Übersicht enthält insbesondere:

- Anlagen-ID,
- Bezeichnung,
- Anschaffungsdatum,
- Anschaffungs- bzw. Herstellungskosten (AK/HK),
- kumulierte Abschreibungen,
- aktuellen Buchwert,
- Nutzungsdauer in Monaten,
- Anlagekonto,
- Abschreibungskonto,
- Status der Anschaffungsbuchung und
- Status des Anlageguts.

Bei der Anschaffungsbuchung wird angezeigt, ob sie dem Anlagegut bereits
**zugeordnet** oder noch **nicht zugeordnet** ist.

Der Status eines Anlageguts zeigt an, ob es noch **Aktiv** oder bereits
**Abgegangen** ist.

Über die Schaltfläche **Anlagegut hinzufügen** kann ein neues Anlagegut
erfasst werden.

Weitere Funktionen stehen über das Kontextmenü eines Anlageguts und
über die Schaltfläche **Aktionen** zur Verfügung.

### 10.2 Neues Anlagegut anlegen

Mit **Anlagegut hinzufügen** wird der Dialog zur Erfassung eines neuen
Anlageguts geöffnet.

Folgende Angaben werden erfasst:

- **Anlagen-ID**
- **Bezeichnung**
- **Anlagenart**
- **Anschaffungsdatum**
- **Anschaffungskosten**
- **AfA-Beginn**
- **Nutzungsdauer in Monaten**

Die Anlagen-ID dient der eindeutigen Kennzeichnung des Anlageguts.

Als Anlagenarten stehen derzeit zur Verfügung:

- **Technische Anlagen und Maschinen**
- **Betriebs- und Geschäftsausstattung**

Die Nutzungsdauer wird in Monaten angegeben und muss eine positive
ganze Zahl sein.

Das Feld **AfA-Beginn** bestimmt den Beginn der Abschreibung. SimpleOB
verwendet die Angaben des Anlageguts anschließend zur Berechnung der
linearen Abschreibungen.

Mit **Speichern** wird das Anlagegut angelegt.

Das Anlegen des Anlageguts erzeugt noch keine Anschaffungsbuchung in
der Finanzbuchhaltung. Die entsprechende Buchung wird separat erfasst
und anschließend dem Anlagegut zugeordnet.

### 10.3 Anschaffungsbuchung zuordnen

Damit ein Anlagegut mit seiner Anschaffung in der Finanzbuchhaltung
verbunden ist, muss die entsprechende Anschaffungsbuchung zugeordnet
werden.

Dazu wird das Anlagegut in der Anlagenübersicht ausgewählt und über
sein Kontextmenü **Anschaffungsbuchung zuordnen** aufgerufen.

SimpleOB sucht nach passenden Buchungszeilen. Für die Zuordnung werden
nur geeignete Buchungen berücksichtigt, die insbesondere zum
Anlagekonto und zu den Anschaffungskosten des Anlageguts passen.

Die gefundenen Buchungen werden mit

- Datum,
- Beleg,
- Buchungstext,
- Konto und
- Betrag

angezeigt.

Nach Auswahl der richtigen Buchungszeile wird sie mit **Zuordnen** mit
dem Anlagegut verknüpft.

Ist bereits eine Anschaffungsbuchung zugeordnet, kann keine zweite
Anschaffungsbuchung zugeordnet werden.

Findet SimpleOB keine passende Buchung, wird darauf hingewiesen.

> **Hinweis:** Die Zuordnung erzeugt keine neue Finanzbuchung. Sie
> verbindet eine bereits vorhandene Buchung mit dem Anlagegut.

### 10.4 Anlagegut bearbeiten

Ein vorhandenes Anlagegut kann über das Kontextmenü mit
**Anlagegut bearbeiten** geöffnet werden.

Die **Anlagen-ID** eines bereits angelegten Anlageguts kann nicht mehr
geändert werden.

Solange noch keine Anschaffungsbuchung zugeordnet wurde, können auch
Angaben zur Anschaffung geändert werden.

Nach Zuordnung der Anschaffungsbuchung können

- Anschaffungsdatum,
- Anschaffungskosten und
- Anlagenart

nicht mehr geändert werden.

Damit verhindert SimpleOB, dass die Daten des Anlageguts nachträglich
von der bereits zugeordneten Finanzbuchung abweichen.

Andere noch zulässige Änderungen können weiterhin über den
Bearbeitungsdialog vorgenommen werden.

### 10.5 Anlagegut löschen

Über das Kontextmenü steht **Anlagegut löschen** zur Verfügung.

Das Löschen ist nur zulässig, solange das Anlagegut noch nicht in einer
Weise buchungswirksam geworden ist, die einer Löschung entgegensteht.
SimpleOB prüft dies beim Löschversuch.

Vor dem Löschen wird eine Sicherheitsabfrage angezeigt.

Ein bestätigter Löschvorgang kann nicht rückgängig gemacht werden.

Kann das Anlagegut aufgrund seines aktuellen Zustands nicht gelöscht
werden, verweigert SimpleOB den Vorgang und zeigt eine entsprechende
Meldung an.

### 10.6 Abschreibungen prüfen und buchen

SimpleOB berechnet die linearen Abschreibungen aus den beim Anlagegut
hinterlegten Daten.

Die Funktion wird über

**Aktionen → Abschreibungen prüfen/buchen**

aufgerufen.

SimpleOB ermittelt zunächst, ob für das ausgewählte Geschäftsjahr noch
offene Abschreibungen vorhanden sind.

Sind keine offenen Abschreibungen vorhanden, wird keine Buchung
erzeugt.

Für jede ermittelte Abschreibung zeigt SimpleOB einzeln einen
Buchungsvorschlag an. Angezeigt werden unter anderem:

- Bezeichnung des Anlageguts,
- Anlagen-ID,
- Abschreibungsbetrag,
- Aufwandskonto,
- Anlagenkonto und
- Buchungsdatum.

Anschließend fragt SimpleOB:

**Soll diese Abschreibung gebucht werden?**

Erst wenn diese Frage mit **Ja** beantwortet wird, erzeugt SimpleOB die
entsprechende Finanzbuchung.

Wird **Nein** gewählt, wird diese Abschreibung nicht gebucht. Die
Prüfung wird mit den weiteren vorhandenen Abschreibungsvorschlägen
fortgesetzt.

Damit werden von SimpleOB berechnete Abschreibungen nicht
stillschweigend in die Finanzbuchhaltung übernommen.

Nach der Buchung werden Konten, Journal, Anlagenübersicht und Bilanz
aktualisiert.

### 10.7 Steuerliche AfA-Abweichungen

Die handelsrechtliche Abschreibung und die steuerlich anzusetzende
Abschreibung können voneinander abweichen.

Für bereits bestätigte Abschreibungen können solche Abweichungen über

**Aktionen → Steuerliche AfA-Abweichungen**

erfasst werden.

Für jede bestätigte Abschreibung zeigt SimpleOB insbesondere:

- das Anlagegut,
- das Abschreibungsdatum,
- die HGB-AfA,
- die steuerliche AfA und
- die Differenz

an.

Standardmäßig entspricht die steuerliche AfA zunächst der
handelsrechtlichen AfA.

Nur wenn die steuerliche AfA davon abweicht, muss ein abweichender
Betrag erfasst werden.

Entspricht die steuerliche AfA der HGB-AfA, wird keine steuerliche
Abweichung gespeichert.

Die steuerliche AfA darf nicht negativ sein.

> **Hinweis:** Die Funktion dient der Erfassung einer steuerlichen
> Abweichung zu einer bereits bestätigten handelsrechtlichen
> Abschreibung. Sie ersetzt nicht die handelsrechtliche
> Abschreibungsbuchung.

### 10.8 Anlagegut verkaufen

Der Verkauf eines Anlageguts kann direkt aus der Anlagenübersicht
bearbeitet werden.

Dazu wird das Anlagegut ausgewählt und im Kontextmenü
**Anlagegut verkaufen …** aufgerufen.

Der direkte Verkaufsablauf steht nur für ein noch aktives Anlagegut
zur Verfügung. Außerdem muss dem Anlagegut bereits eine
Anschaffungsbuchung zugeordnet sein.

Für den Verkauf werden eingegeben:

- **Abgangsdatum**
- **Belegnummer**
- **Verkaufspreis brutto**
- **Umsatzsteuersatz**
- **Gegenkonto**

Als Umsatzsteuersätze stehen **0 %**, **7 %** und **19 %** zur
Verfügung.

SimpleOB berechnet aus diesen Angaben den Anlagenabgang.

### 10.9 Abschreibung vor einem Anlagenverkauf

Vor dem Verkauf prüft SimpleOB, ob bis zum Abgangsdatum noch eine
Abschreibung des Anlageguts erforderlich ist.

Ist noch eine Abschreibung zu buchen, zeigt SimpleOB zunächst einen
gesonderten Abschreibungsvorschlag mit

- Betrag,
- Aufwandskonto,
- Anlagenkonto und
- Datum

an.

Die Abschreibung wird nur gebucht, wenn sie ausdrücklich bestätigt
wird.

Wird die Abschreibung nicht bestätigt, wird auch der anschließend
vorgesehene Anlagenverkauf an dieser Stelle nicht durchgeführt.

Nach einer bestätigten Abschreibung berechnet SimpleOB den
Anlagenverkauf auf Grundlage der aktualisierten Werte erneut.

### 10.10 Verkaufsvorschau und Buchung

Vor der endgültigen Buchung eines Anlagenverkaufs zeigt SimpleOB eine
Vorschau.

Diese enthält insbesondere:

- Anschaffungskosten,
- kumulierte Abschreibungen,
- Restbuchwert,
- Bruttoverkaufspreis,
- Nettoerlös,
- Umsatzsteuer,
- Gewinn bzw. Verlust aus dem Anlagenabgang und
- die vorgesehenen Buchungszeilen.

Damit kann die von SimpleOB berechnete Buchung vor ihrer Übernahme
kontrolliert werden.

Erst nach der ausdrücklichen Bestätigung

**Soll der Anlagenverkauf gebucht werden?**

wird die Buchung erzeugt und der Anlagenabgang übernommen.

Anschließend werden Konten, Journal, Anlagenübersicht und Bilanz
aktualisiert.

Das Anlagegut erhält danach den Status **Abgegangen**.

### 10.11 Bereits vorhandene Abgangsbuchung zuordnen

Wurde der Abgang eines Anlageguts bereits auf anderem Weg in der
Finanzbuchhaltung erfasst, kann diese Buchung dem Anlagegut
nachträglich zugeordnet werden.

Dazu steht im Kontextmenü

**Abgangsbuchung zuordnen**

zur Verfügung.

Voraussetzung ist insbesondere, dass

- das Anlagegut noch als aktiv geführt wird und
- bereits eine Anschaffungsbuchung zugeordnet ist.

SimpleOB sucht nach geeigneten Buchungszeilen auf dem Anlagekonto und
zeigt die gefundenen Buchungen mit

- Datum,
- Beleg,
- Buchungstext,
- Konto und
- Betrag

an.

Nach Auswahl der richtigen Buchungszeile wird sie mit **Zuordnen** dem
Anlagegut zugeordnet.

> **Hinweis:** Auch hierbei wird keine neue Finanzbuchung erzeugt.
> Eine bereits vorhandene Buchung wird mit dem Anlagegut verknüpft.

### 10.12 Anlagenspiegel als PDF

Über die Schaltfläche

**Anlagenspiegel PDF exportieren**

kann der Anlagenspiegel des ausgewählten Geschäftsjahres als
PDF-Datei ausgegeben werden.

SimpleOB schlägt einen Dateinamen nach dem Schema

`SimpleOB_Anlagenspiegel_<Unternehmen>_<Jahr>.pdf`

vor.

Der Speicherort kann beim Export ausgewählt werden.

Ist für das ausgewählte Geschäftsjahr kein Anlagenspiegel vorhanden,
weist SimpleOB darauf hin und erzeugt keine PDF-Datei.

### 10.13 Anlagenbuchhaltung und abgeschlossenes Geschäftsjahr

Ändernde Funktionen der Anlagenbuchhaltung stehen nur in einem offenen
Geschäftsjahr zur Verfügung.

Dazu gehören insbesondere das Anlegen und Bearbeiten von
Anlagegütern, Zuordnungen, Anlagenverkäufe und die Bearbeitung von
Abschreibungen.

Der Abschluss eines Geschäftsjahres und die dabei durchgeführte
Prüfung noch offener Abschreibungen werden in Kapitel 11 beschrieben.

## 11. Jahresabschluss

Der Arbeitsbereich **Jahresabschluss** unterstützt den Abschluss des
ausgewählten Geschäftsjahres.

SimpleOB zeigt dort insbesondere:

- den Status des Geschäftsjahres,
- das ermittelte Jahresergebnis,
- den Status der Plausibilitätsprüfung und
- gegebenenfalls festgestellte Fehler.

Außerdem stehen dort die Funktionen für die Ergebnisverwendung zur
Verfügung.

Der Jahresabschluss sollte erst durchgeführt werden, wenn alle
Buchungen des Geschäftsjahres vollständig erfasst und geprüft worden
sind.

### 11.1 Jahresergebnis

SimpleOB ermittelt aus den Buchungen des Geschäftsjahres das
Jahresergebnis.

Je nach Ergebnis wird angezeigt:

- **Jahresüberschuss** bei einem positiven Ergebnis,
- **Jahresfehlbetrag** bei einem negativen Ergebnis oder
- **Jahresergebnis** bei einem Ergebnis von 0,00 €.

Das angezeigte Jahresergebnis bildet zugleich eine Grundlage für die
spätere Ergebnisverwendung.

### 11.2 Abschreibungen vor dem Jahresabschluss

Vor der Abschlussprüfung kontrolliert SimpleOB, ob noch offene
Abschreibungen vorhanden sind.

Sind noch Abschreibungen zu bearbeiten, kann die Abschlussprüfung
nicht fortgesetzt werden.

SimpleOB weist in diesem Fall darauf hin, zunächst im Bereich
**Anlagen** die Funktion

**Aktionen → Abschreibungen prüfen/buchen**

auszuführen.

Die einzelnen Abschreibungsvorschläge werden dort jeweils gesondert
angezeigt und müssen ausdrücklich bestätigt werden. Der Ablauf ist in
Kapitel 10 beschrieben.

Erst wenn keine offenen Abschreibungen mehr vorhanden sind, kann die
eigentliche Plausibilitätsprüfung des Jahresabschlusses durchgeführt
werden.

### 11.3 Abschluss prüfen

Mit der Schaltfläche

**Abschluss prüfen**

führt SimpleOB eine Plausibilitätsprüfung des Jahresabschlusses durch.

Dabei werden die für den Abschluss ermittelten Daten aus Bilanz,
Gewinn- und Verlustrechnung, Jahresergebnis und Kontensalden auf
Konsistenz geprüft.

Das Ergebnis wird im Bereich **Plausibilitätsprüfung** angezeigt.

Bei erfolgreicher Prüfung erscheint:

**Plausibilitätsprüfung erfolgreich.**

Erst dann wird die Schaltfläche

**Geschäftsjahr abschließen**

freigegeben.

Schlägt die Prüfung fehl, erscheint:

**Plausibilitätsprüfung fehlgeschlagen.**

Die festgestellten Fehler werden darunter aufgelistet. Das
Geschäftsjahr kann in diesem Zustand nicht abgeschlossen werden.

Die Ursachen müssen zunächst beseitigt und die Prüfung anschließend
erneut durchgeführt werden.

### 11.4 Geschäftsjahr endgültig abschließen

Nach erfolgreicher Plausibilitätsprüfung kann das Geschäftsjahr mit

**Geschäftsjahr abschließen**

abgeschlossen werden.

Vor dem Abschluss zeigt SimpleOB eine ausdrückliche Sicherheitsabfrage.

Dabei wird darauf hingewiesen, dass

- das Geschäftsjahr endgültig abgeschlossen wird,
- die Erfolgskonten abgeschlossen werden und
- weitere Buchungen in diesem Geschäftsjahr anschließend gesperrt
  sind.

Der Vorgang wird nur durchgeführt, wenn die Sicherheitsabfrage
bestätigt wird.

Nach erfolgreichem Abschluss zeigt SimpleOB:

**Das Geschäftsjahr wurde erfolgreich abgeschlossen.**

Der Status wechselt anschließend von

**Geschäftsjahr: Offen**

zu

**Geschäftsjahr: Abgeschlossen**.

> **Wichtig:** Ein abgeschlossenes Geschäftsjahr ist für weitere
> Buchungen gesperrt. Vor dem endgültigen Abschluss sollten deshalb
> Buchungen, Abschreibungen, Bilanz und Gewinn- und Verlustrechnung
> sorgfältig geprüft werden.

### 11.5 Auswirkungen des Jahresabschlusses

Beim Abschluss werden die erforderlichen Abschlussvorgänge für das
Geschäftsjahr durchgeführt und die Erfolgskonten abgeschlossen.

Anschließend aktualisiert SimpleOB insbesondere:

- das Journal,
- die Bilanz,
- den Jahresabschluss,
- die Auswertung für den Betriebsvermögensvergleich und
- den Stand der E-Bilanz.

Buchungs- und andere ändernde Funktionen des abgeschlossenen
Geschäftsjahres stehen danach nicht mehr zur Verfügung.

Bilanz und Gewinn- und Verlustrechnung werden in Kapitel 12
beschrieben.

### 11.6 Ergebnisverwendung

Die Ergebnisverwendung ist vom eigentlichen Jahresabschluss getrennt.

Zunächst wird das Geschäftsjahr abgeschlossen. Erst für das
abgeschlossene Geschäftsjahr kann anschließend ein
**Ergebnisverwendungsbeschluss** erfasst werden.

Der Beschluss selbst gehört zum abgeschlossenen Geschäftsjahr.

Die daraus entstehenden Finanzbuchungen werden dagegen nicht
nachträglich in dieses abgeschlossene Geschäftsjahr gebucht. SimpleOB
schlägt die entsprechenden Umsetzungsbuchungen im Folgegeschäftsjahr
gesondert vor.

Damit bleiben Jahresabschluss, Ergebnisverwendungsbeschluss und
spätere Umsetzung des Beschlusses voneinander getrennt.

### 11.7 Ergebnisverwendungsbeschluss erfassen

Nach dem Abschluss des Geschäftsjahres wird die Schaltfläche

**Ergebnisverwendungsbeschluss**

verfügbar.

Der Dialog zeigt zunächst:

- das Geschäftsjahr,
- den Jahresüberschuss bzw. Jahresfehlbetrag und
- einen vorhandenen Gewinn-/Verlustvortrag aus dem Vorjahr.

Für den Beschluss können folgende Beträge erfasst werden:

- **Zuführung gesetzliche Rücklage**
- **Zuführung andere Gewinnrücklagen**
- **Auflösung gesetzliche Rücklage**
- **Auflösung andere Gewinnrücklagen**
- **Ausschüttung**
- **Neuer Gewinn-/Verlustvortrag**

Bei einem erstmals erfassten Beschluss sind Zuführungen, Auflösungen
und Ausschüttung zunächst mit 0,00 € vorbelegt.

Der neue Gewinn-/Verlustvortrag wird zunächst aus dem Jahresergebnis
und einem gegebenenfalls vorhandenen Gewinn-/Verlustvortrag des
Vorjahres abgeleitet.

SimpleOB prüft beim Speichern, ob der Ergebnisverwendungsbeschluss
rechnerisch ausgeglichen ist.

Ist dies nicht der Fall, wird der Beschluss nicht gespeichert und
SimpleOB zeigt die festgestellten Fehler an.

### 11.8 Beschluss und Finanzbuchungen

Das Speichern des Ergebnisverwendungsbeschlusses erzeugt noch keine
Finanzbuchungen.

Der Beschluss wird dem abgeschlossenen Geschäftsjahr zugeordnet.

Die daraus erforderlichen Buchungen werden erst im folgenden
Geschäftsjahr über

**Ergebnisverwendung Vorjahr buchen**

vorgeschlagen.

Dies betrifft je nach Beschluss insbesondere:

- Zuführung zur gesetzlichen Rücklage,
- Zuführung zu anderen Gewinnrücklagen,
- Auflösung der gesetzlichen Rücklage,
- Auflösung anderer Gewinnrücklagen und
- Ausschüttungen.

### 11.9 Ergebnisverwendung des Vorjahres buchen

Die Funktion

**Ergebnisverwendung Vorjahr buchen**

steht in einem offenen Geschäftsjahr zur Verfügung, wenn ein
entsprechendes Vorjahr als Eröffnungsquelle vorhanden ist.

Zunächst wird das Buchungsdatum abgefragt.

SimpleOB ermittelt anschließend die noch offenen
Umsetzungsbuchungen aus dem Ergebnisverwendungsbeschluss des
Vorjahres.

Sind keine solchen Buchungen vorhanden, weist SimpleOB darauf hin.

Andernfalls wird jede erforderliche Buchung einzeln angezeigt.

Die Anzeige enthält insbesondere:

- Art der Ergebnisverwendung,
- Betrag,
- Sollkonto,
- Habenkonto und
- Buchungsdatum.

Für jede Buchung fragt SimpleOB ausdrücklich:

**Soll diese Buchung jetzt durchgeführt werden?**

Nur nach Bestätigung mit **Ja** wird die betreffende Buchung
durchgeführt.

Wird **Nein** gewählt, wird diese Buchung nicht durchgeführt und
SimpleOB fährt mit gegebenenfalls weiteren Vorschlägen fort.

Damit werden auch Buchungen aus einem Ergebnisverwendungsbeschluss
nicht automatisch und ohne Bestätigung in die Finanzbuchhaltung
übernommen.

### 11.10 Sperre des Ergebnisverwendungsbeschlusses

Solange aus einem Ergebnisverwendungsbeschluss noch keine wirksamen
Umsetzungsbuchungen vorhanden sind, kann der Beschluss des
abgeschlossenen Geschäftsjahres erfasst oder geändert werden.

Sobald daraus bereits wirksame Umsetzungsbuchungen vorhanden sind,
wird der Beschluss gesperrt.

SimpleOB zeigt dann:

**Der Ergebnisverwendungsbeschluss ist gesperrt, weil bereits wirksame
Umsetzungsbuchungen vorhanden sind.**

Der Beschluss kann weiterhin angezeigt, aber nicht mehr geändert
werden.

Damit wird verhindert, dass ein bereits buchungswirksam umgesetzter
Beschluss nachträglich verändert wird.

### 11.11 Empfohlene Reihenfolge

Für einen regulären Jahreswechsel ergibt sich damit folgende
Reihenfolge:

1. Alle laufenden Buchungen des Geschäftsjahres vollständig erfassen.
2. Anlagegüter und offene Abschreibungen prüfen.
3. Bilanz und Gewinn- und Verlustrechnung kontrollieren.
4. Im Bereich **Jahresabschluss** die Funktion **Abschluss prüfen**
   ausführen.
5. Eventuelle Fehler beseitigen und die Prüfung wiederholen.
6. Nach erfolgreicher Prüfung **Geschäftsjahr abschließen**.
7. Für das abgeschlossene Geschäftsjahr gegebenenfalls den
   **Ergebnisverwendungsbeschluss** erfassen.
8. Das Folgegeschäftsjahr anlegen und gegebenenfalls die
   Vorjahressalden übernehmen.
9. Im Folgegeschäftsjahr die Funktion
   **Ergebnisverwendung Vorjahr buchen** aufrufen.
10. Die vorgeschlagenen Umsetzungsbuchungen einzeln prüfen und
    bestätigen.


## 12. Bilanz und Gewinn- und Verlustrechnung

SimpleOB erstellt aus den Buchungen des ausgewählten Geschäftsjahres
eine laufende Bilanz und Gewinn- und Verlustrechnung.

Beide Auswertungen können während des laufenden Geschäftsjahres zur
Kontrolle verwendet werden. Nach dem Jahresabschluss stehen sie
weiterhin für das abgeschlossene Geschäftsjahr zur Verfügung.

Bilanz und Gewinn- und Verlustrechnung können außerdem jeweils als
PDF-Datei exportiert werden.

### 12.1 Grundlage der Auswertungen

Die Auswertungen werden aus den Kontensalden des ausgewählten
Geschäftsjahres erzeugt.

Dabei verwendet SimpleOB die bei den Konten hinterlegten
HGB-Zuordnungen, um die Kontensalden den Positionen von Bilanz und
Gewinn- und Verlustrechnung zuzuordnen.

Änderungen an den Buchungen des offenen Geschäftsjahres wirken sich
damit auf die daraus ermittelten Auswertungen aus.

Nach dem endgültigen Abschluss des Geschäftsjahres sind weitere
Buchungen für dieses Geschäftsjahr gesperrt.

### 12.2 Bilanz

Der Arbeitsbereich **Bilanz** zeigt die

**Bilanz nach § 266 HGB**.

Die Darstellung ist in zwei Bereiche aufgeteilt:

- **Aktiva**
- **Passiva**

Auf beiden Seiten werden die Bilanzpositionen hierarchisch in einer
Baumansicht dargestellt.

Für jede angezeigte Position werden

- die Bezeichnung der Position und
- der zugehörige Betrag

ausgegeben.

Positionen ohne Betrag werden in der laufenden Baumansicht nicht
angezeigt.

Die vorhandenen Positionen werden entsprechend ihrer HGB-Gliederung
unter den übergeordneten Positionen zusammengefasst.

### 12.3 Bilanzsummen und Bilanzausgleich

Unterhalb der Bilanz zeigt SimpleOB die Summen von Aktiva und Passiva
an.

Zusätzlich wird angezeigt, ob die Bilanz ausgeglichen ist.

Bei einer ausgeglichenen Bilanz erscheint:

**Bilanz ausgeglichen: Ja**

Stimmen Aktiva und Passiva nicht überein, erscheint:

**Bilanz ausgeglichen: Nein**

Zusätzlich wird die Differenz zwischen Aktiva und Passiva angezeigt.

Eine nicht ausgeglichene Bilanz sollte vor dem Jahresabschluss
geprüft und korrigiert werden.

### 12.4 Fehlende oder fehlerhafte Kontenzuordnungen

Damit SimpleOB die Bilanz vollständig ermitteln kann, müssen die
verwendeten Bilanzkonten den erforderlichen HGB-Positionen zugeordnet
sein.

Kann ein Kontensaldo wegen einer fehlenden Zuordnung nicht in die
Bilanz eingeordnet werden, zeigt SimpleOB an, dass die Bilanz nicht
vollständig ermittelt werden kann.

Die betreffende Kontenzuordnung muss dann im Bereich **Konten**
geprüft werden.

Die Einrichtung und Bearbeitung der Konten sowie ihrer
HGB-Zuordnungen ist in Kapitel 8 beschrieben.

### 12.5 Gewinn- und Verlustrechnung

Der Arbeitsbereich **GuV** zeigt die

**Gewinn- und Verlustrechnung nach § 275 HGB**.

Die Darstellung ist in zwei Bereiche aufgeteilt:

- **Erträge**
- **Aufwendungen**

Die GuV-Positionen werden jeweils hierarchisch in einer Baumansicht
dargestellt.

Für jede angezeigte Position werden

- die Bezeichnung der Position und
- der zugehörige Betrag

ausgegeben.

Positionen ohne Betrag werden in der laufenden Darstellung nicht
angezeigt.

### 12.6 Jahresergebnis in der GuV

Unterhalb der Gewinn- und Verlustrechnung zeigt SimpleOB das
ermittelte Ergebnis an.

Je nach Höhe des Ergebnisses wird es bezeichnet als:

- **Jahresüberschuss** bei einem positiven Ergebnis,
- **Jahresfehlbetrag** bei einem negativen Ergebnis oder
- **Ergebnis** bei 0,00 €.

Dieses Ergebnis wird auch für den Jahresabschluss verwendet.

### 12.7 GuV nach dem Jahresabschluss

Beim endgültigen Jahresabschluss werden die Erfolgskonten
abgeschlossen.

SimpleOB bewahrt für die Darstellung der Gewinn- und Verlustrechnung
den dafür maßgeblichen Stand vor diesen Abschlussbuchungen.

Dadurch kann die GuV des Geschäftsjahres auch nach dessen Abschluss
weiterhin angezeigt werden.

Die nach dem Abschluss leeren Erfolgskonten führen somit nicht dazu,
dass die GuV des abgeschlossenen Jahres verloren geht.

### 12.8 Bilanz als PDF exportieren

Die aktuell angezeigte Bilanz kann über

**PDF exportieren**

als PDF-Datei gespeichert werden.

SimpleOB öffnet dazu einen Dialog zur Auswahl des Dateinamens und des
Speicherorts. Als Dateiname wird zunächst

**Bilanz.pdf**

vorgeschlagen.

Die PDF-Ausgabe wird für den aktuell ausgewählten Mandanten und das
ausgewählte Geschäftsjahr erzeugt.

Nach erfolgreichem Export zeigt SimpleOB den Speicherort der erzeugten
Datei an.

Steht keine Bilanz zur Verfügung, kann kein PDF-Export durchgeführt
werden.

### 12.9 Gewinn- und Verlustrechnung als PDF exportieren

Auch die aktuell ermittelte Gewinn- und Verlustrechnung kann über

**PDF exportieren**

als PDF-Datei gespeichert werden.

Als Dateiname wird zunächst

**GuV.pdf**

vorgeschlagen.

Die PDF-Ausgabe enthält die Gewinn- und Verlustrechnung einschließlich
des ermittelten Jahresergebnisses für den aktuell ausgewählten
Mandanten und das ausgewählte Geschäftsjahr.

Nach erfolgreichem Export zeigt SimpleOB den Speicherort der erzeugten
Datei an.

Steht keine GuV zur Verfügung, kann kein PDF-Export durchgeführt
werden.

### 12.10 Verhältnis zum Jahresabschluss

Bilanz und Gewinn- und Verlustrechnung sollten vor dem endgültigen
Jahresabschluss kontrolliert werden.

Ein sinnvoller Ablauf ist:

1. Alle Buchungen des Geschäftsjahres erfassen.
2. Erforderliche Abschreibungen prüfen und buchen.
3. Bilanz kontrollieren.
4. Gewinn- und Verlustrechnung kontrollieren.
5. Gegebenenfalls fehlerhafte Kontenzuordnungen oder Buchungen
   korrigieren.
6. Im Bereich **Jahresabschluss** die Funktion
   **Abschluss prüfen** ausführen.
7. Erst nach erfolgreicher Prüfung das Geschäftsjahr endgültig
   abschließen.

Der eigentliche Jahresabschluss ist in Kapitel 11 beschrieben.

### 12.11 Abgrenzung zur E-Bilanz

Die in diesem Kapitel beschriebenen Ansichten sind die
handelsrechtlichen Auswertungen von Bilanz und Gewinn- und
Verlustrechnung innerhalb von SimpleOB.

Die **E-Bilanz** ist davon zu unterscheiden. Für sie werden die
Abschlussdaten für die vorgeschriebene elektronische Übermittlung
aufbereitet und weiteren Prüfungen unterzogen.

Die Erstellung, Prüfung und Übermittlung der E-Bilanz wird in
Kapitel 13 beschrieben.


## 13. E-Bilanz

Der Arbeitsbereich **E-Bilanz** dient zur Vorbereitung, Erzeugung,
Prüfung und elektronischen Übermittlung der E-Bilanz für das
ausgewählte Geschäftsjahr.

SimpleOB führt den Benutzer dabei schrittweise durch den erforderlichen
Arbeitsablauf.

Der Arbeitsbereich ist in drei Bereiche gegliedert:

- **Taxonomie und Status**
- **Steuerliche Gewinnermittlung (BVV)**
- **E-Bilanz-Aktionen**

Die E-Bilanz kann erst vorbereitet werden, nachdem das Geschäftsjahr
abgeschlossen wurde.

Der Jahresabschluss ist in Kapitel 11 beschrieben.

### 13.1 Voraussetzungen

Für die Erstellung einer E-Bilanz müssen insbesondere folgende
Voraussetzungen erfüllt sein:

- Für den Mandanten muss eine von SimpleOB unterstützte Rechtsform
  hinterlegt sein.
- Die erforderlichen Unternehmensstammdaten müssen vorhanden sein.
- Das Geschäftsjahr muss abgeschlossen sein.
- Eine Gewinn- und Verlustrechnung muss für das Geschäftsjahr
  vorliegen.
- Die für das Geschäftsjahr benötigte E-Bilanz-Taxonomie muss
  vollständig installiert sein.
- Für eine ELSTER-Übermittlung müssen zusätzlich die in Kapitel 5
  beschriebenen ELSTER-Einstellungen vorhanden sein.

Solange das Geschäftsjahr noch offen ist, zeigt SimpleOB:

**Das Geschäftsjahr ist noch nicht abgeschlossen. Die E-Bilanz kann
erst nach dem Jahresabschluss vorbereitet werden.**

### 13.2 Taxonomie

Im Bereich **Taxonomie und Status** zeigt SimpleOB die für das
Geschäftsjahr benötigte Taxonomie und deren Installationsstatus an.

Mögliche Zustände sind:

- **installiert und vollständig**
- **installiert, aber unvollständig**
- **nicht installiert**

Ist die erforderliche Taxonomie noch nicht verwendbar, steht die
Schaltfläche

**Taxonomie installieren**

zur Verfügung.

Damit installiert SimpleOB die für das ausgewählte Geschäftsjahr
benötigte Taxonomie.

Nach erfolgreicher Installation erscheint eine entsprechende
Bestätigung.

Die Auswahl und technische Verarbeitung der Taxonomie erfolgt durch
SimpleOB. Für den normalen Arbeitsablauf ist keine manuelle
Bearbeitung der Taxonomiedateien erforderlich.

### 13.3 Steuerliche Gewinnermittlung – BVV

Im Arbeitsbereich E-Bilanz zeigt SimpleOB außerdem die
**Steuerliche Gewinnermittlung (BVV)** an.

BVV steht hier für den Betriebsvermögensvergleich.

Die angezeigten Werte werden aus der Buchführung ermittelt.

SimpleOB zeigt insbesondere:

- **HGB-Eigenkapital**
- **Buchwertabweichung aus steuerlicher AfA**
- **Steuerliches Betriebsvermögen Ende**
- **HGB-Eigenkapital zu Jahresbeginn**
- **Buchwertabweichung zu Jahresbeginn**
- **Steuerliches Betriebsvermögen Vorjahr**
- **Veränderung des Betriebsvermögens**
- **gebuchte Einlagen**
- **gebuchte Entnahmen / Ausschüttungen**
- **Steuerlicher Gewinn / Verlust**

Steuerliche Abweichungen bei der AfA werden aus den in der
Anlagenbuchhaltung erfassten steuerlichen AfA-Abweichungen
berücksichtigt.

Die Erfassung solcher Abweichungen ist in Kapitel 10 beschrieben.

### 13.4 BVV als PDF exportieren

Sobald die BVV-Auswertung zur Verfügung steht, kann sie über

**BVV als PDF exportieren**

als PDF-Datei ausgegeben werden.

Damit kann die aus der Buchführung ermittelte steuerliche
Gewinnermittlung unabhängig von der eigentlichen XBRL-Datei
kontrolliert und dokumentiert werden.

### 13.5 E-Bilanz vorbereiten

Nach dem Abschluss des Geschäftsjahres steht die Funktion

**E-Bilanz vorbereiten**

zur Verfügung.

SimpleOB bereitet damit die Abschlusswerte für die E-Bilanz auf.

Nach erfolgreicher Vorbereitung zeigt der Statusbereich unter anderem
die Anzahl der aufbereiteten

- Bilanzpositionen und
- GuV-Positionen

an.

Die Vorbereitung erzeugt noch nicht die endgültige XBRL-E-Bilanz.

Sie bildet die Grundlage für den nächsten Schritt.

### 13.6 E-Bilanz erzeugen

Nach erfolgreicher Vorbereitung und bei vollständig installierter
Taxonomie kann

**E-Bilanz erzeugen**

ausgeführt werden.

SimpleOB erzeugt daraus das E-Bilanz-Dokument.

Nach erfolgreicher Erzeugung erscheint:

**Die E-Bilanz wurde erfolgreich erzeugt.**

Das erzeugte Dokument muss anschließend noch validiert werden.

### 13.7 E-Bilanz mit Arelle validieren

Mit

**E-Bilanz validieren**

prüft SimpleOB die erzeugte E-Bilanz mit Arelle.

Arelle ist die in SimpleOB verwendete technische Validierungskomponente
für das erzeugte XBRL-Dokument.

Bei erfolgreicher Validierung erscheint:

**Die E-Bilanz wurde von Arelle erfolgreich validiert.**

Stellt Arelle Fehler fest, zeigt SimpleOB die gemeldeten Fehler an.

Eine fehlerhafte E-Bilanz wird nicht für Export und
ELSTER-Übermittlung freigegeben.

Die Ursachen der gemeldeten Fehler müssen zunächst beseitigt werden.
Anschließend ist die E-Bilanz erneut vorzubereiten bzw. zu erzeugen
und zu validieren, soweit dies aufgrund der vorgenommenen Änderungen
erforderlich ist.

> **Hinweis:** Eine erfolgreiche technische Validierung bedeutet nicht
> automatisch, dass die E-Bilanz steuerlich oder inhaltlich richtig
> ist. Die Verantwortung für die sachliche Richtigkeit der übermittelten
> Angaben verbleibt beim Benutzer.

### 13.8 E-Bilanz als XBRL exportieren

Nach erfolgreicher Validierung steht

**E-Bilanz XBRL exportieren**

zur Verfügung.

Damit kann das erzeugte E-Bilanz-Dokument als XBRL-Datei gespeichert
werden.

Wird beim Speichern keine Dateiendung angegeben, ergänzt SimpleOB die
Endung

**.xbrl**

automatisch.

Die XBRL-Datei enthält das maschinenlesbare E-Bilanz-Dokument.

Der Export einer XBRL-Datei ist von der direkten Übermittlung an
ELSTER zu unterscheiden.

### 13.9 E-Bilanz als PDF exportieren

Nach erfolgreicher Erzeugung und Arelle-Validierung kann außerdem

**E-Bilanz PDF exportieren**

verwendet werden.

Die PDF-Ausgabe dient der lesbaren Darstellung und Dokumentation der
für die E-Bilanz aufbereiteten Abschlusswerte.

Soweit ein Anlagenspiegel vorhanden ist, wird dieser bei der
PDF-Erstellung berücksichtigt.

SimpleOB schlägt einen Dateinamen nach folgendem Muster vor:

**SimpleOB_E-Bilanz_Mandant_Jahr.pdf**

Die PDF-Datei ist eine lesbare Dokumentation. Sie ersetzt nicht die
für die elektronische Übermittlung verwendete XBRL-E-Bilanz.

### 13.10 Voraussetzungen für die ELSTER-Übermittlung

Eine ELSTER-Übermittlung ist erst möglich, wenn

- die E-Bilanz erzeugt wurde,
- die E-Bilanz erfolgreich mit Arelle validiert wurde,
- die ERiC-/ELSTER-Komponenten zur Verfügung stehen,
- ein ELSTER-Datenlieferant konfiguriert ist und
- ein verwendbares ELSTER-Zertifikat konfiguriert ist.

Die Einrichtung des Zertifikats und des Datenlieferanten ist in
Kapitel 5 beschrieben.

Die PIN des ELSTER-Zertifikats wird nicht dauerhaft in der
SimpleOB-Konfiguration gespeichert. Sie wird unmittelbar vor einer
Übermittlung abgefragt.

### 13.11 ELSTER-Testübermittlung

Vor einer produktiven Übermittlung kann eine

**ELSTER-Testübermittlung**

durchgeführt werden.

Für einen vollständigen Praxistest kann das zusammen mit SimpleOB
ausgelieferte ELSTER-Testzertifikat

`test-softidnr-pse.pfx`

verwendet werden.

Das Testzertifikat wird nicht automatisch von SimpleOB eingerichtet.
Der Benutzer wählt es zunächst unter

**Einstellungen → ELSTER-Zertifikat…**

aus. Damit wird derselbe Einrichtungsvorgang durchlaufen, der später
auch für das persönliche ELSTER-Zertifikat erforderlich ist.

Die PIN des Testzertifikats lautet:

**123456**

Sie wird nicht in SimpleOB gespeichert, sondern bei der Testübermittlung
manuell in den PIN-Dialog eingegeben.

Bei der Testübermittlung handelt es sich um eine echte Verbindung zum
ELSTER-Server.

Der Datensatz wird jedoch als Testsendung mit dem ELSTER-Testmerker

**700000004**

übertragen.

SimpleOB weist vor der Übertragung ausdrücklich darauf hin, dass eine
Verbindung zum ELSTER-Server hergestellt wird.

Zum Start der Testsendung muss der Benutzer exakt

**TESTSENDUNG**

eingeben.

Erst danach werden der konfigurierte Datenlieferant und die
Zertifikatsdaten verwendet und die PIN des ELSTER-Zertifikats
abgefragt.

Vor der eigentlichen Sendung führt SimpleOB außerdem die für die
Testübermittlung vorgesehene ERiC-Prüfung durch.

Schlägt diese Prüfung oder die Übermittlung fehl, zeigt SimpleOB die
Fehlermeldung an.

### 13.12 Erfolgreiche Testübermittlung

Wird die Testübermittlung ohne Fehler abgeschlossen, zeigt SimpleOB
unter anderem das von ELSTER zurückgegebene

**TransferTicket**

an.

Zusätzlich wird ausdrücklich darauf hingewiesen:

**Es wurde keine produktive Steuerübermittlung durchgeführt.**

SimpleOB fragt anschließend, ob ein Übertragungsnachweis gespeichert
werden soll.

Eine erfolgreiche Testsendung sollte vor der ersten produktiven
Übermittlung genutzt werden, um den technischen Übertragungsweg zu
prüfen.

Wurde für den Praxistest das mitgelieferte Testzertifikat verwendet,
muss vor einer späteren produktiven Übermittlung unter

**Einstellungen → ELSTER-Zertifikat…**

das persönliche ELSTER-Zertifikat des Benutzers ausgewählt werden.

### 13.13 ELSTER-Produktivübermittlung

Mit

**ELSTER-Produktivübermittlung**

wird die E-Bilanz produktiv an ELSTER übertragen.

Diese Funktion ist ausdrücklich von der Testübermittlung zu
unterscheiden.

Wurde zuvor das mit SimpleOB ausgelieferte Testzertifikat verwendet,
muss vor der Produktivübermittlung das persönliche ELSTER-Zertifikat
des Benutzers unter

**Einstellungen → ELSTER-Zertifikat…**

ausgewählt werden.

Das mitgelieferte Testzertifikat darf nicht für eine produktive
Übermittlung verwendet werden.

SimpleOB zeigt vor dem Versand eine deutliche Warnung an:

- Es handelt sich um eine produktive ELSTER-Übermittlung.
- Der Datensatz wird ohne Testmerker übertragen.
- Es handelt sich nicht um eine Testsendung.
- Mandant, Geschäftsjahr und E-Bilanz sollen vor dem Versand nochmals
  geprüft werden.

Zum endgültigen Start muss der Benutzer exakt

**PRODUKTIV SENDEN**

eingeben.

Wird diese Zeichenfolge nicht exakt eingegeben oder der Dialog
abgebrochen, findet keine produktive Übermittlung statt.

Danach werden der Datenlieferant und das konfigurierte
ELSTER-Zertifikat verwendet und die Zertifikats-PIN abgefragt.

Vor der eigentlichen Übertragung führt SimpleOB die für die
Produktivübermittlung vorgesehene ERiC-Prüfung durch.

### 13.14 Vor einer Produktivübermittlung

Vor der Bestätigung einer produktiven Übermittlung sollten mindestens
folgende Angaben nochmals kontrolliert werden:

1. Ist der richtige Mandant geöffnet?
2. Ist das richtige Geschäftsjahr ausgewählt?
3. Ist das Geschäftsjahr ordnungsgemäß abgeschlossen?
4. Sind Bilanz und GuV geprüft?
5. Sind die Unternehmensstammdaten vollständig und richtig?
6. Ist die richtige E-Bilanz erzeugt worden?
7. Wurde diese E-Bilanz erfolgreich mit Arelle validiert?
8. Ist der richtige ELSTER-Datenlieferant hinterlegt?
9. Wird das richtige ELSTER-Zertifikat verwendet?

Die Sicherheitsabfrage **PRODUKTIV SENDEN** soll verhindern, dass eine
produktive Übermittlung versehentlich ausgelöst wird.

### 13.15 Erfolgreiche Produktivübermittlung

Nach einer ohne Fehler abgeschlossenen Produktivübermittlung zeigt
SimpleOB das von ELSTER zurückgegebene

**TransferTicket**

an.

Anschließend kann ein Übertragungsnachweis gespeichert werden.

Das TransferTicket sollte zusammen mit den Unterlagen zum
Geschäftsjahr aufbewahrt werden.

### 13.16 ELSTER-Übertragungsnachweis

Nach einer erfolgreichen Test- oder Produktivübermittlung bietet
SimpleOB an, einen Übertragungsnachweis als Textdatei zu speichern.

Der vorgeschlagene Dateiname enthält insbesondere:

- SimpleOB,
- den Mandantennamen,
- das Jahr,
- die Übertragungsart und
- den Zeitpunkt der Übertragung.

Der Nachweis enthält:

- Mandant,
- Geschäftsjahr,
- Übertragungsart,
- Zeitpunkt,
- Datenart,
- bei einer Testsendung den Testmerker,
- TransferTicket und
- den Status der erfolgreichen Übertragung.

Bei einer Testsendung wird als Übertragungsart **TEST**, bei einer
Produktivsendung **PRODUKTIV** angegeben.

Der Übertragungsnachweis sollte für die Dokumentation des
Übermittlungsvorgangs aufbewahrt werden.

### 13.17 Empfohlener E-Bilanz-Ablauf

Für die Erstellung und Übermittlung einer E-Bilanz ergibt sich damit
folgende Reihenfolge:

1. Buchführung des Geschäftsjahres vervollständigen.
2. Anlagenbuchhaltung und Abschreibungen prüfen.
3. Bilanz und GuV prüfen.
4. Jahresabschluss prüfen.
5. Geschäftsjahr endgültig abschließen.
6. Im Arbeitsbereich **E-Bilanz** den Taxonomiestatus prüfen und die
   benötigte Taxonomie gegebenenfalls installieren.
7. **E-Bilanz vorbereiten**.
8. Die angezeigte steuerliche Gewinnermittlung (BVV) kontrollieren.
9. **E-Bilanz erzeugen**.
10. **E-Bilanz validieren**.
11. Fehler aus der Arelle-Validierung gegebenenfalls beseitigen und
    die erforderlichen Schritte wiederholen.
12. Bei Bedarf XBRL-, PDF- und BVV-PDF-Dateien zur Dokumentation
    exportieren.
13. ELSTER-Datenlieferant und Zertifikat kontrollieren.
14. Eine **ELSTER-Testübermittlung** durchführen.
15. Das TransferTicket bzw. den Übertragungsnachweis der Testsendung
    kontrollieren.
16. Vor der produktiven Übermittlung Mandant, Geschäftsjahr und
    E-Bilanz nochmals sorgfältig prüfen.
17. **ELSTER-Produktivübermittlung** durchführen.
18. TransferTicket anzeigen lassen und den Übertragungsnachweis
    speichern.

### 13.18 Änderungen nach Erzeugung einer E-Bilanz

Wurden für die E-Bilanz relevante Daten geändert, kann eine bereits
erzeugte E-Bilanz nicht ungeprüft weiterverwendet werden.

SimpleOB verwirft in entsprechenden Fällen den zuvor erzeugten
E-Bilanz-Stand beziehungsweise dessen erfolgreichen
Validierungsstatus.

Die E-Bilanz muss dann auf Grundlage der aktuellen Daten erneut
erzeugt und mit Arelle validiert werden.

Dadurch soll verhindert werden, dass eine ältere validierte
E-Bilanz-Datei versehentlich als aktueller Datenstand behandelt wird.

### 13.19 Verantwortung des Benutzers

SimpleOB unterstützt die technische Erstellung, Validierung und
Übermittlung der E-Bilanz.

Die Plausibilitäts- und technischen Prüfungen können jedoch nicht
garantieren, dass sämtliche buchhalterischen, handelsrechtlichen und
steuerlichen Angaben inhaltlich richtig sind.

Vor einer produktiven Übermittlung sind deshalb insbesondere die
Buchführung, der Jahresabschluss, die Stammdaten und die aufbereiteten
E-Bilanz-Daten fachlich zu prüfen.


## 14. Datenaustausch und Mandantensicherung

SimpleOB kann einen vollständigen Mandanten in eine portable Datei
exportieren und später wieder importieren.

Hierfür verwendet SimpleOB Dateien mit der Endung

**.simpleob**

Eine solche Datei kann sowohl zur Sicherung eines einzelnen Mandanten
als auch zur Übertragung dieses Mandanten in eine andere
SimpleOB-Installation verwendet werden.

Die `.simpleob`-Datei ist von der zentralen SimpleOB-Datenbank und von
der Anwendungskonfiguration zu unterscheiden.

### 14.1 Mandanten exportieren

Für den aktuell geöffneten Mandanten steht die Funktion zum Export
einer Mandantensicherung zur Verfügung.

SimpleOB schlägt als Dateinamen den Namen des Mandanten mit der Endung

**.simpleob**

vor.

Wird beim Speichern keine Endung angegeben, ergänzt SimpleOB
`.simpleob` automatisch.

Nach erfolgreichem Export bestätigt SimpleOB die Erstellung der Datei.

### 14.2 Umfang einer Mandantensicherung

Eine `.simpleob`-Datei enthält den vollständigen von SimpleOB
unterstützten Datenbestand des exportierten Mandanten.

Dazu gehören insbesondere:

- Unternehmensstammdaten,
- Konten und Kontenzuordnungen,
- Systemkonten,
- Umsatzsteuerkonten,
- Kontenrollen,
- mandantenspezifische E-Bilanz-Zuordnungen,
- Gesellschafterdaten,
- sämtliche in SimpleOB verwalteten Geschäftsjahre,
- Buchungen und Buchungszeilen,
- Verknüpfungen zwischen den Geschäftsjahren,
- Anlagegüter,
- Anlagenbewegungen,
- gebuchte Abschreibungen,
- steuerliche AfA-Abweichungen,
- Daten zur Ergebnisverwendung,
- Buchungen zur Ergebnisverwendung und
- erfasste Einlagen.

Der Export beschränkt sich damit nicht auf das gerade ausgewählte
Geschäftsjahr.

Auch andere in SimpleOB für denselben Mandanten vorhandene
Geschäftsjahre werden in die Mandantensicherung aufgenommen.

### 14.3 Was nicht zur Mandantensicherung gehört

Die `.simpleob`-Datei enthält mandantenbezogene Daten.

Anwendungsweite Einstellungen gehören dagegen nicht zum
Mandantentransfer.

Insbesondere werden die in Kapitel 5 beschriebenen
ELSTER-Einstellungen nicht als Bestandteil des Mandanten exportiert.

Dazu gehören insbesondere:

- der lokal konfigurierte Pfad zum ELSTER-Zertifikat und
- der ELSTER-Datenlieferant.

Die PIN des ELSTER-Zertifikats kann ebenfalls nicht Bestandteil einer
Mandantensicherung sein, da SimpleOB diese PIN grundsätzlich nicht
dauerhaft speichert.

Nach der Übertragung eines Mandanten auf einen anderen Rechner müssen
die dort benötigten ELSTER-Einstellungen deshalb gegebenenfalls
separat eingerichtet werden.

### 14.4 Technischer Aufbau der `.simpleob`-Datei

Eine `.simpleob`-Datei ist ein von SimpleOB erzeugter
Mandantentransfercontainer.

Der Container enthält die strukturierten Mandantendaten in einer
internen Datei namens

**client.json**

Diese interne Struktur ist für den normalen Benutzer nicht zur
manuellen Bearbeitung vorgesehen.

Beim Import prüft SimpleOB die Struktur und den Inhalt der Datei.

Eine beschädigte, unvollständige oder nicht als gültiger
SimpleOB-Mandantentransfer lesbare Datei wird abgelehnt.

> **Hinweis:** Eine `.simpleob`-Datei sollte nicht manuell verändert
> werden. Änderungen an ihrem internen Inhalt können dazu führen, dass
> die Datei nicht mehr importiert werden kann oder inhaltlich
> inkonsistent wird.

### 14.5 Mandanten importieren

Der Import erfolgt im Startfenster von SimpleOB über

**Mandant importieren …**

Nach Auswahl einer `.simpleob`-Datei liest und prüft SimpleOB zunächst
deren Inhalt.

Ist die Datei gültig und kann der Mandant importiert werden, werden
die enthaltenen Mandantendaten in die lokale SimpleOB-Datenbank
übernommen.

Nach erfolgreichem Import erscheint der importierte Mandant in der
Mandantenauswahl und wird dort ausgewählt.

### 14.6 Bereits vorhandener Mandant

Jeder SimpleOB-Mandant besitzt neben seinem sichtbaren Namen eine
interne eindeutige Kennung.

Ist ein Mandant mit derselben internen Kennung bereits in der
SimpleOB-Datenbank vorhanden, wird der Import abgelehnt.

SimpleOB überschreibt in diesem Fall den vorhandenen Mandanten nicht.

Eine `.simpleob`-Datei dient daher nicht dazu, einen bereits
vorhandenen Mandanten automatisch mit einem älteren oder neueren
Datenstand zu überschreiben oder zusammenzuführen.

Dies schützt insbesondere davor, dass ein vorhandener Mandantenbestand
durch einen versehentlichen Import ersetzt wird.

### 14.7 Gleichnamige Mandanten

Für die Erkennung eines bereits vorhandenen Mandanten ist nicht allein
der sichtbare Unternehmensname maßgeblich.

Entscheidend ist die interne eindeutige Mandantenkennung.

Dadurch ist die technische Identität eines Mandanten unabhängig von
seinem angezeigten Namen.

Ein vorhandener Mandant kann deshalb nicht dadurch aktualisiert
werden, dass eine `.simpleob`-Datei mit demselben Namen importiert
wird.

### 14.8 Sicherheit beim Import

Vor dem eigentlichen Import prüft SimpleOB die im Transfer enthaltenen
Daten und deren interne Verknüpfungen.

Dazu gehören beispielsweise Beziehungen zwischen

- Konten und Buchungen,
- Geschäftsjahren,
- Buchungszeilen,
- Anlagenbewegungen und Buchungen,
- Abschreibungen und Buchungen sowie
- Ergebnisverwendungsdaten und den zugehörigen Buchungen.

Der Import wird erst dauerhaft gespeichert, wenn der Importvorgang
erfolgreich abgeschlossen werden konnte.

Tritt während des Imports ein Fehler auf, wird der Importvorgang
zurückgesetzt.

Dadurch soll verhindert werden, dass nur ein Teil eines Mandanten in
der Datenbank verbleibt.

### 14.9 `.simpleob` als Mandantensicherung

Die Exportfunktion eignet sich dazu, einen Mandanten einschließlich
seiner in SimpleOB gespeicherten Geschäftsjahre und Buchhaltungsdaten
in einer einzelnen Datei zu sichern.

Eine solche Sicherung sollte insbesondere erstellt werden

- vor größeren Änderungen am Datenbestand,
- vor einem Rechnerwechsel,
- vor einer Neuinstallation,
- vor wichtigen Arbeiten am Jahresabschluss und
- in regelmäßigen Abständen als zusätzliche Sicherung des
  Mandantenbestands.

Die Sicherungsdateien sollten außerhalb des SimpleOB-
Anwendungsverzeichnisses aufbewahrt werden.

Für wichtige Daten empfiehlt sich zusätzlich eine Sicherung auf einem
anderen Datenträger oder einem anderweitig geschützten
Sicherungsmedium.

### 14.10 Unterschied zur Sicherung der gesamten SimpleOB-Datenbank

Eine `.simpleob`-Datei sichert einen einzelnen Mandanten in einem
portablen SimpleOB-Format.

Davon zu unterscheiden ist eine Sicherung der vollständigen lokalen
SimpleOB-Anwendungsdaten.

Wie in Kapitel 3 beschrieben, befinden sich die lokalen
Anwendungsdaten unter macOS im Verzeichnis

`~/Library/Application Support/SimpleOB/`

Eine Sicherung dieses Verzeichnisses beziehungsweise insbesondere der
darin enthaltenen Datenbank schützt den gesamten lokalen
SimpleOB-Datenbestand.

Die beiden Sicherungsarten haben daher unterschiedliche Zwecke:

- **`.simpleob`-Mandantensicherung:** portabler Export eines einzelnen
  Mandanten einschließlich seiner Geschäftsjahre und
  Buchhaltungsdaten.
- **Sicherung der lokalen Anwendungsdaten:** Sicherung des gesamten
  lokalen SimpleOB-Datenbestands und der lokalen Konfiguration.

Für eine belastbare Datensicherungsstrategie empfiehlt es sich, nicht
ausschließlich auf eine einzige Sicherungsart zu vertrauen.

### 14.11 Übertragung auf einen anderen Rechner

Für die Übertragung eines Mandanten auf einen anderen Rechner kann
folgender Ablauf verwendet werden:

1. Den gewünschten Mandanten auf dem bisherigen Rechner öffnen.
2. Den Mandanten als `.simpleob`-Datei exportieren.
3. Die Datei auf den neuen Rechner übertragen.
4. SimpleOB auf dem neuen Rechner starten.
5. Im Startfenster **Mandant importieren …** auswählen.
6. Die übertragene `.simpleob`-Datei öffnen.
7. Prüfen, ob der Mandant und seine Geschäftsjahre vollständig
   vorhanden sind.
8. Bei Bedarf die lokalen ELSTER-Einstellungen auf dem neuen Rechner
   einrichten.
9. Vor einer weiteren produktiven Arbeit die wichtigsten
   Buchhaltungsdaten und Auswertungen kontrollieren.

### 14.12 Aufbewahrung von Mandantensicherungen

Mandantensicherungen können sensible Unternehmens-, Buchhaltungs- und
Steuerdaten enthalten.

Sie sollten deshalb vor unbefugtem Zugriff geschützt und nur an
geeigneten Speicherorten aufbewahrt werden.

Beim Versand oder bei der Übertragung einer `.simpleob`-Datei ist zu
beachten, dass die Datei nicht lediglich technische
Programmeinstellungen, sondern den eigentlichen Mandantendatenbestand
enthalten kann.


## 15. Fehlerbehebung

SimpleOB prüft an vielen Stellen Eingaben und Voraussetzungen und zeigt
bei einem Problem eine entsprechende Meldung an.

Die Meldung sollte zunächst vollständig gelesen werden. Häufig nennt sie
bereits die Ursache oder die Voraussetzung, die noch erfüllt werden
muss.

Bei Problemen mit Buchhaltungsdaten sollte nicht versucht werden, die
SimpleOB-Datenbank manuell zu verändern.

### 15.1 SimpleOB startet nicht

Startet SimpleOB nach einer Installation oder einem Update nicht,
kommen unterschiedliche Ursachen in Betracht.

Insbesondere nach einem Programmupdate kann beim Start eine Anpassung
der Datenbankstruktur erforderlich sein.

SimpleOB prüft beim Start automatisch, ob die vorhandene Datenbank zur
installierten Programmversion passt.

Ist keine Änderung erforderlich, wird die Datenbank unverändert
verwendet.

Ist eine Datenbankmigration erforderlich, legt SimpleOB vor der
Schemaänderung automatisch eine Sicherung der vorhandenen
SQLite-Datenbank an.

Diese Sicherungsdatei befindet sich im selben Verzeichnis wie die
Datenbank und trägt den Zusatz

`-before-migration`

im Dateinamen.

Bei der standardmäßigen Datenbankdatei `openbilanz.db` lautet der Name
der Sicherung daher:

`openbilanz-before-migration.db`

Kann die Sicherung nicht erstellt werden, wird die Migration nicht
durchgeführt.

Erkennt SimpleOB eine vorhandene Datenbank ohne Versionsinformation,
die nicht einer bekannten älteren SimpleOB-Datenbankstruktur
entspricht, wird die Datenbank ebenfalls nicht automatisch verändert.

> **Wichtig:** Wenn SimpleOB nach einem Update bereits beim Start
> scheitert, sollte die Datenbank nicht manuell bearbeitet und eine
> vorhandene Sicherungsdatei nicht vorschnell über die aktuelle
> Datenbank kopiert werden.

In diesem Fall sollten zunächst die vorhandenen Dateien im
SimpleOB-Anwendungsdatenverzeichnis gesichert werden.

Unter macOS befindet sich dieses Verzeichnis standardmäßig unter:

`~/Library/Application Support/SimpleOB/`

Insbesondere sollten `openbilanz.db`, eine gegebenenfalls vorhandene
`openbilanz-before-migration.db` und `config.toml` erhalten bleiben.

Anschließend sollte die konkrete Fehlermeldung beziehungsweise die
Ausgabe beim Programmstart zur Fehleranalyse herangezogen werden.

### 15.2 Buchungen oder Änderungen sind nicht möglich

Kann eine Buchung nicht erfasst oder eine andere Änderung nicht
durchgeführt werden, sollte zunächst geprüft werden, ob das richtige
Geschäftsjahr geöffnet wurde.

Ein bereits abgeschlossenes Geschäftsjahr ist für weitere reguläre
Buchungen gesperrt.

Der Jahresabschluss ist als endgültiger Abschluss des Geschäftsjahres
vorgesehen. Ein abgeschlossenes Geschäftsjahr sollte daher nicht durch
manuelle Änderungen an der Datenbank wieder geöffnet werden.

Bei Fehlermeldungen während einer Buchung sollten außerdem insbesondere
geprüft werden:

- Buchungsdatum,
- ausgewählte Konten,
- Soll- und Habenbeträge,
- Ausgeglichenheit der Buchung,
- Umsatzsteuerangaben bei Rechnungsbuchungen und
- die für den Mandanten hinterlegte Kontenkonfiguration.

Bei automatisierten Buchungsvorgängen, beispielsweise Abschreibungen
oder Ergebnisverwendungsbuchungen, sollten zusätzlich die in der
Fehlermeldung genannten Voraussetzungen geprüft werden.

### 15.3 Jahresabschluss kann nicht durchgeführt werden

Vor dem endgültigen Jahresabschluss muss die
Plausibilitätsprüfung erfolgreich durchgeführt worden sein.

Sind noch Abschreibungen zu prüfen oder zu buchen, weist SimpleOB
darauf hin. Diese müssen zunächst über die Anlagenbuchhaltung
bearbeitet werden.

Schlägt die Plausibilitätsprüfung fehl, zeigt SimpleOB die festgestellten
Probleme an.

Diese sollten behoben und anschließend die Prüfung erneut ausgeführt
werden.

Der Schalter zum endgültigen Abschluss des Geschäftsjahres wird erst
nach erfolgreicher Plausibilitätsprüfung freigegeben.

Die Plausibilitätsprüfung ist eine programminterne Prüfung der für den
Abschluss benötigten Daten. Sie ersetzt keine handels- oder
steuerrechtliche Prüfung des Jahresabschlusses.

### 15.4 Bilanz oder GuV kann nicht ermittelt werden

Kann die Bilanz nicht vollständig ermittelt werden, kann insbesondere
eine fehlende oder ungeeignete HGB-Zuordnung eines Kontos die Ursache
sein.

In diesem Fall sollte die Kontenkonfiguration beziehungsweise die
Zuordnung des betroffenen Kontos geprüft werden.

Bei Bilanz und GuV ist außerdem darauf zu achten, dass die Auswertungen
immer zum aktuell ausgewählten Mandanten und Geschäftsjahr gehören.

Kann lediglich die PDF-Datei nicht exportiert werden, sollte zusätzlich
geprüft werden, ob

- ein gültiger Speicherort ausgewählt wurde,
- Schreibrechte für diesen Speicherort bestehen und
- eine dort bereits vorhandene Datei möglicherweise von einem anderen
  Programm verwendet wird.

### 15.5 E-Bilanz kann nicht vorbereitet oder erzeugt werden

Die E-Bilanz setzt mehrere vorhergehende Arbeitsschritte voraus.

Kann sie nicht vorbereitet oder erzeugt werden, sollte insbesondere
geprüft werden:

- Sind die Unternehmensstammdaten vollständig?
- Unterstützt die eingestellte Rechtsform den vorgesehenen
  E-Bilanz-Ablauf?
- Ist das Geschäftsjahr abgeschlossen?
- Kann die Bilanz und GuV vollständig ermittelt werden?
- Ist die von SimpleOB benötigte Taxonomie installiert und vollständig?
- Sind erforderliche Konten- und E-Bilanz-Zuordnungen vorhanden?

Die einzelnen Schritte

**E-Bilanz vorbereiten**,

**E-Bilanz erzeugen**

und

**E-Bilanz validieren**

bauen aufeinander auf.

Schlägt ein früherer Schritt fehl, sollte dessen Ursache behoben werden,
bevor mit dem nächsten Schritt fortgefahren wird.

### 15.6 E-Bilanz-Validierung schlägt fehl

Die erzeugte E-Bilanz wird vor dem Export und vor einer
ELSTER-Übermittlung mit Arelle validiert.

Meldet Arelle Fehler, zeigt SimpleOB die Validierung als fehlgeschlagen
an.

Die gemeldeten Fehler sollten nicht dadurch umgangen werden, dass die
erzeugte XBRL-Datei manuell verändert wird.

Stattdessen sollte die Ursache in den zugrunde liegenden
SimpleOB-Daten, Stammdaten oder Zuordnungen korrigiert werden.

Anschließend ist die E-Bilanz erneut vorzubereiten beziehungsweise zu
erzeugen und zu validieren.

Eine erfolgreiche technische Validierung bedeutet nicht automatisch,
dass die E-Bilanz steuerlich oder inhaltlich richtig ist.

### 15.7 ELSTER-Übermittlung schlägt fehl

Vor einer ELSTER-Übermittlung müssen insbesondere folgende
Voraussetzungen erfüllt sein:

- Die E-Bilanz wurde erzeugt.
- Die Arelle-Validierung war erfolgreich.
- Der ELSTER-Datenlieferant ist eingerichtet.
- Ein gültiges ELSTER-Zertifikat ist ausgewählt.
- Die zugehörige PIN wurde für den aktuellen Übertragungsvorgang
  eingegeben.

Schlägt eine Test- oder Produktivübermittlung fehl, zeigt SimpleOB eine
Fehlermeldung an.

Soweit ELSTER beziehungsweise ERiC zusätzliche Fehlerinformationen
liefert, sollten diese für die weitere Fehleranalyse berücksichtigt
werden.

Bei einem Fehler sollte nicht unmittelbar wiederholt eine
Produktivübermittlung ausgelöst werden, ohne zuvor die Ursache zu
prüfen.

Bestehen Zweifel, ob die Übertragung tatsächlich erfolgreich war,
sollte insbesondere geprüft werden, ob SimpleOB einen erfolgreichen
Übertragungsvorgang mit TransferTicket gemeldet hat.

Bei einer erfolgreichen Übertragung kann der von SimpleOB angebotene
Übertragungsnachweis gespeichert werden.

### 15.8 ELSTER-Zertifikat wird nicht gefunden

Ist der gespeicherte Zertifikatspfad nicht mehr gültig, sollte unter

**Einstellungen → ELSTER-Zertifikat …**

das vorhandene Zertifikat erneut ausgewählt werden.

Dies kann beispielsweise nach einem Rechnerwechsel oder nach dem
Verschieben der Zertifikatsdatei erforderlich sein.

Die Zertifikats-PIN wird von SimpleOB nicht dauerhaft gespeichert und
muss bei einer Übertragung erneut eingegeben werden.

### 15.9 PDF- oder XBRL-Export schlägt fehl

SimpleOB erzeugt verschiedene externe Dateien, beispielsweise

- Bilanz,
- GuV,
- Anlagenspiegel,
- BVV,
- E-Bilanz als PDF,
- E-Bilanz als XBRL und
- ELSTER-Übertragungsnachweise.

Kann eine solche Datei nicht gespeichert werden, sollte zunächst ein
anderer lokaler Speicherort versucht werden.

Außerdem sollte geprüft werden, ob der gewünschte Zielordner
beschreibbar ist und ob eine vorhandene Datei gleichen Namens
gegebenenfalls noch in einem anderen Programm geöffnet ist.

Ein fehlgeschlagener Dateiexport bedeutet nicht automatisch, dass die
zugrunde liegenden Buchhaltungsdaten verloren gegangen sind.

### 15.10 Mandantenexport schlägt fehl

Beim Export einer `.simpleob`-Mandantensicherung prüft SimpleOB den
zu exportierenden Mandantenbestand und dessen interne Verknüpfungen.

Schlägt der Export fehl, sollte die angezeigte Fehlermeldung
festgehalten werden.

Die zugrunde liegende SimpleOB-Datenbank sollte nicht manuell verändert
werden, um einen Export zu erzwingen.

Vor weiteren Eingriffen empfiehlt sich eine Sicherung der lokalen
Anwendungsdaten entsprechend Kapitel 3.

### 15.11 Mandantenimport schlägt fehl

Eine `.simpleob`-Datei wird vor und während des Imports geprüft.

Ein Import kann insbesondere abgelehnt werden, wenn

- die Datei kein gültiger SimpleOB-Mandantentransfer ist,
- der Inhalt beschädigt oder inkonsistent ist oder
- derselbe Mandant anhand seiner internen Kennung bereits vorhanden
  ist.

Ein fehlgeschlagener Import wird nicht als teilweise importierter
Mandant dauerhaft gespeichert.

Eine `.simpleob`-Datei sollte zur Fehlerbehebung nicht manuell
verändert werden.

Weitere Einzelheiten zum Mandantentransfer enthält Kapitel 14.

### 15.12 Vorgehen bei einem nicht selbst lösbaren Fehler

Kann ein Problem nicht anhand der angezeigten Meldung behoben werden,
sollten vor weiteren Änderungen möglichst folgende Informationen
festgehalten werden:

- verwendete SimpleOB-Version,
- Mandant und betroffenes Geschäftsjahr,
- Arbeitsschritt, bei dem der Fehler aufgetreten ist,
- vollständiger Wortlaut der Fehlermeldung,
- gegebenenfalls zusätzliche Fehlerdetails,
- ob das Problem nach einem Programmupdate aufgetreten ist und
- ob aktuelle Sicherungen vorhanden sind.

Vor Reparaturversuchen an der Datenbank sollte eine zusätzliche Kopie
der vorhandenen Anwendungsdaten angelegt werden.

Passwörter, Zertifikats-PINs und andere Zugangsdaten sollten nicht in
Fehlerberichte oder Bildschirmfotos übernommen werden.

Bei Fehlern im Zusammenhang mit einer ELSTER-Übermittlung sollte
außerdem festgehalten werden, ob es sich um eine Test- oder
Produktivübermittlung handelte und ob ein TransferTicket ausgegeben
wurde.

### 15.13 Grundregel bei Datenbankproblemen

Die Datei `openbilanz.db` enthält den lokalen SimpleOB-Datenbestand.

Sie sollte nicht mit einem SQLite-Werkzeug oder einem anderen
Datenbankprogramm verändert werden, sofern dies nicht im Rahmen einer
gezielten und fachkundig begleiteten Wiederherstellung geschieht.

Auch die automatische Datei

`openbilanz-before-migration.db`

sollte zunächst unverändert aufbewahrt werden.

Bei einem Datenbankproblem ist es in der Regel sicherer, zuerst Kopien
der vorhandenen Dateien anzulegen und anschließend die Ursache zu
untersuchen, als unmittelbar Änderungen am Originalbestand
vorzunehmen.


## 16. Datenschutz, Lizenzen und rechtliche Hinweise

SimpleOB verarbeitet geschäftliche, buchhalterische und steuerlich
relevante Daten.

Der Schutz dieser Daten sowie ein verantwortungsvoller Umgang mit
Sicherungen, Exportdateien und ELSTER-Zugangsdaten sind deshalb
wesentliche Bestandteile der Nutzung von SimpleOB.

### 16.1 Lokale Speicherung der SimpleOB-Daten

Die mit SimpleOB erfassten Buchhaltungs- und Unternehmensdaten werden
in der lokalen SimpleOB-Datenbank gespeichert.

Unter macOS befinden sich die Anwendungsdaten standardmäßig unter:

`~/Library/Application Support/SimpleOB/`

Zu diesen Daten gehören insbesondere die lokale Datenbank und die
Anwendungskonfiguration.

Die lokale Speicherung bedeutet nicht, dass SimpleOB niemals Daten an
externe Stellen überträgt. Eine ausdrücklich vom Benutzer ausgelöste
ELSTER-Übermittlung überträgt die dafür vorgesehenen Steuerdaten an die
Finanzverwaltung.

### 16.2 ELSTER und ERiC

SimpleOB verwendet ERiC für die elektronische Übermittlung der
E-Bilanz an ELSTER.

Eine Übermittlung wird nicht allein durch das Erstellen oder Validieren
einer E-Bilanz ausgelöst.

Für eine Test- oder Produktivübermittlung ist jeweils eine ausdrückliche
Benutzeraktion erforderlich.

Vor einer Produktivübermittlung verlangt SimpleOB zusätzlich eine
ausdrückliche Bestätigung des Benutzers.

Die Einzelheiten des Übermittlungsablaufs sind in Kapitel 13
beschrieben.

### 16.3 Datenschutzinformationen der Finanzverwaltung

Vor der Nutzung der ERiC-/ELSTER-Funktionen zeigt SimpleOB die
vorgesehenen Datenschutzinformationen der Finanzverwaltung an.

Die Kenntnisnahme muss bestätigt werden, bevor SimpleOB fortgesetzt
werden kann.

Wird die Kenntnisnahme nicht bestätigt, kann der Start an dieser Stelle
beendet werden.

Die Datenschutzinformationen bleiben auch später in SimpleOB
erreichbar.

Hierzu steht die Funktion

**Datenschutz und ERiC-Hinweise**

zur Verfügung.

Dort können die Datenschutzinformationen der Finanzverwaltung erneut
angezeigt werden.

Die dort wiedergegebenen amtlichen Informationen sind für die
Datenverarbeitung durch die Finanzverwaltung maßgeblich und sollten bei
Fragen zur Verarbeitung der über ELSTER übermittelten Daten
herangezogen werden.

### 16.4 ERiC-Protokolldateien

Bei der Nutzung von ERiC werden Protokolldateien erstellt und lokal auf
dem Computer gespeichert.

Diese Protokolldateien verbleiben grundsätzlich auf dem Computer des
Benutzers.

SimpleOB übermittelt diese Protokolldateien nicht automatisch an den
Hersteller oder an die Finanzverwaltung.

In einem Supportfall dürfen solche Protokolldateien nur nach
ausdrücklicher Erlaubnis des Benutzers weitergegeben werden.

Eine Weiterleitung an die Finanzverwaltung erfolgt ebenfalls nur nach
ausdrücklicher Erlaubnis.

Da Protokolldateien Informationen enthalten können, die für die
Fehleranalyse einer Steuerübermittlung relevant sind, sollten auch sie
vertraulich behandelt werden.

### 16.5 ELSTER-Zertifikat und PIN

SimpleOB speichert den Pfad zum ausgewählten ELSTER-Zertifikat in der
lokalen Anwendungskonfiguration.

Die PIN des Zertifikats wird dagegen nicht dauerhaft gespeichert.

Sie wird für den jeweiligen Übertragungsvorgang abgefragt und nur für
diesen Vorgang verwendet.

Die PIN sollte weder in Fehlerberichte noch in Bildschirmfotos,
Supportanfragen oder andere Dokumentationen übernommen werden.

Auch die Zertifikatsdatei selbst ist vor unbefugtem Zugriff zu
schützen.

### 16.6 ELSTER-Datenlieferant

Die Angaben zum ELSTER-Datenlieferanten werden als
Anwendungseinstellung lokal gespeichert.

Sie werden für die Erstellung der bei einer ELSTER-Übermittlung
benötigten Daten verwendet.

Der ELSTER-Datenlieferant ist von den Stammdaten des jeweiligen
Mandanten zu unterscheiden.

Wie in Kapitel 14 beschrieben, gehören diese anwendungsweiten
ELSTER-Einstellungen nicht zum portablen `.simpleob`-Mandantentransfer.

### 16.7 Datensicherung und Vertraulichkeit

Die mit SimpleOB verwalteten Daten können vertrauliche geschäftliche
und steuerliche Informationen enthalten.

Es sollten deshalb regelmäßig geeignete Datensicherungen erstellt und
an einem sicheren Ort aufbewahrt werden.

Dies gilt sowohl für Sicherungen der vollständigen lokalen
Anwendungsdaten als auch für exportierte `.simpleob`-Dateien.

Sicherungsmedien und Übertragungswege sollten entsprechend dem
Schutzbedarf der enthaltenen Unternehmens- und Steuerdaten gewählt
werden.

Weitere Hinweise zur Datensicherung enthält Kapitel 3.

Hinweise zur `.simpleob`-Mandantensicherung enthält Kapitel 14.

### 16.8 Verwendete Drittsoftware

SimpleOB verwendet Softwarekomponenten und Bibliotheken anderer
Hersteller beziehungsweise Open-Source-Projekte.

Zur ausgelieferten Anwendung gehören insbesondere Komponenten aus den
Bereichen:

- Qt/PySide6,
- GNU gettext und
- ERiC.

Für diese Komponenten gelten jeweils deren eigene Lizenzbedingungen.

Die zugehörigen Lizenzinformationen und Lizenztexte werden mit der
SimpleOB-Anwendung ausgeliefert.

### 16.9 Qt und PySide6

Die grafische Benutzeroberfläche von SimpleOB basiert auf PySide6 und
Qt.

Mit der Anwendung werden die für die verwendeten Qt-/PySide6-
Komponenten vorgesehenen Lizenzinformationen ausgeliefert.

Dazu gehören insbesondere die entsprechenden LGPL- und GPL-Lizenztexte
sowie ergänzende Hinweise zu den für diese Distribution maßgeblichen
Quellcode- und Relinking-Möglichkeiten.

Für die verbindlichen Bedingungen sind die mit der Anwendung
ausgelieferten Lizenztexte und Hinweise maßgeblich.

Dieses Benutzerhandbuch ersetzt diese Lizenztexte nicht.

### 16.10 GNU gettext

SimpleOB enthält beziehungsweise verwendet im ausgelieferten
Programmpaket Komponenten aus GNU gettext.

Die zugehörigen Lizenzinformationen, einschließlich des
LGPL-2.1-Lizenztextes, werden mit der Anwendung ausgeliefert.

Auch hier sind für die Lizenzbedingungen die mitgelieferten
Originalinformationen maßgeblich.

### 16.11 ERiC

Für die elektronische Steuerdatenübermittlung verwendet SimpleOB die
von der Finanzverwaltung bereitgestellte ERiC-Komponente.

Die zugehörige ERiC-Lizenzdokumentation wird mit der Anwendung
ausgeliefert.

Die Nutzung von ERiC und der damit verbundenen Komponenten richtet sich
nach den dafür geltenden Bedingungen.

Dieses Handbuch gibt diese Bedingungen nicht vollständig wieder und
ersetzt die mitgelieferte ERiC-Lizenzdokumentation nicht.

### 16.12 Bedeutung der mitgelieferten Lizenztexte

Die in der Anwendung enthaltenen Lizenztexte sind Bestandteil der
Informationen über die jeweils verwendeten Drittkomponenten.

Bei Abweichungen zwischen einer zusammenfassenden Beschreibung in
diesem Benutzerhandbuch und dem jeweiligen Original-Lizenztext ist für
die betreffende Drittkomponente der Original-Lizenztext maßgeblich.

Die Aufnahme eines Lizenztextes in die SimpleOB-Distribution bedeutet
nicht, dass sämtliche Bestandteile von SimpleOB automatisch unter
derselben Lizenz stehen.

### 16.13 Verantwortung für Buchführung und Steuerdaten

SimpleOB unterstützt bei der Erfassung und Auswertung von
Buchhaltungsdaten sowie bei der technischen Erstellung und Übermittlung
einer E-Bilanz.

Die Software kann die fachliche Prüfung der eingegebenen Daten nicht
ersetzen.

Insbesondere bleiben die sachliche Richtigkeit und Vollständigkeit der
erfassten Unternehmens-, Buchhaltungs- und Steuerdaten sowie die
Prüfung einer zur Übermittlung vorgesehenen E-Bilanz in der
Verantwortung des Benutzers beziehungsweise der dafür fachlich
verantwortlichen Personen.

Eine erfolgreiche programminterne Plausibilitätsprüfung,
E-Bilanz-Erzeugung, Arelle-Validierung oder technische
ELSTER-Übermittlung bedeutet für sich allein nicht, dass die
zugrunde liegenden Angaben handelsrechtlich oder steuerrechtlich
richtig und vollständig sind.

### 16.14 Keine Steuer- oder Rechtsberatung durch die Software

Die von SimpleOB durchgeführten Berechnungen, Prüfungen und
Darstellungen dienen der Unterstützung der mit der Software
durchgeführten Buchführungs- und E-Bilanz-Arbeiten.

Sie ersetzen keine im Einzelfall erforderliche steuerliche oder
rechtliche Beratung.

Bei Zweifeln über die handelsrechtliche oder steuerrechtliche
Behandlung eines Sachverhalts sollte fachkundiger Rat eingeholt
werden.

### 16.15 Schutz wichtiger Dateien und Zugangsdaten

Besonders geschützt werden sollten:

- die SimpleOB-Datenbank,
- `.simpleob`-Mandantensicherungen,
- weitere Datensicherungen,
- exportierte Buchhaltungs- und E-Bilanz-Dokumente,
- ELSTER-Zertifikatsdateien,
- ERiC-Protokolldateien und
- gespeicherte ELSTER-Übertragungsnachweise.

Zertifikats-PINs und andere Zugangsdaten sollten nicht gemeinsam mit
diesen Dateien ungeschützt aufbewahrt oder weitergegeben werden.

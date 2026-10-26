# OP-Verwaltung – Implementierungsstufe 4A

## Ergebnis

Stufe 4A ergänzt eine rein lesende, stichtagsbezogene Abstimmung der vier konfigurierten OP-Sammelkonto-Rollen. Hauptbuchbuchungen und OP-Ereignisse werden weder angelegt noch geändert. Die gezielte Korrektur der historischen Datumsabgrenzung ergänzt zusätzlich eine Migration für das Buchungsdatum am Korrekturkopf.

Die Anwendung zeigt Kundenforderungen, Lieferantenverbindlichkeiten, Kundenguthaben und Lieferantenguthaben jeweils auf den tatsächlich ermittelten Sammelkonten. Abweichungen werden als Differenz `Hauptbuchsaldo minus OP-Saldo` angezeigt. Hauptbuchbewegungen auf diesen Konten, zu denen kein OP-bezogener Vorgang gefunden wird, erscheinen zusätzlich als ungeklärt.

## Umsetzung

- `src/simpleob/domain/open_item_reconciliation.py`: unveränderliche Ergebnisdatentypen für Bericht, Kontenzeilen und ungeklärte Buchungsbewegungen.
- `src/simpleob/database/open_item_reconciliation_repository.py`: tenantbezogene, lesende Salden- und Ereignisabfragen; Ermittlung der tatsächlich bebuchten Konten aus den Ursprungsbuchungszeilen.
- `src/simpleob/services/open_item_reconciliation_service.py`: dünne Service-Schnittstelle ohne Commit- oder Schreiboperationen.
- `src/simpleob/ui_qt/open_item_reconciliation_widget.py`: Stichtagsauswahl, Aktualisierung, Ergebnistabelle und Detailtabelle ungeklärter Bewegungen.
- `src/simpleob/ui_qt/main_window.py`: Integration als Tab „OP-Abstimmung“ ohne Buchungs- oder Korrekturaktionen.
- `src/simpleob/qt_main.py`: Verdrahtung des Services mit der vorhandenen Session.
- `src/simpleob/database/models.py`, `src/simpleob/domain/payment_allocation_correction.py`, `src/simpleob/database/payment_allocation_correction_repository.py` und `src/simpleob/services/payment_allocation_correction_service.py`: persistiertes, verpflichtendes Buchungsdatum für neue Zahlungszuordnungskorrekturen; unabhängige Geschäftsjahresprüfung und Konsistenz mit einer möglichen Hauptbuchumbuchung.
- `migrations/versions/c71f4db9e2a6_add_payment_correction_booking_date.py`: nullable Historienfeld, Backfill aus verknüpften Hauptbuchbuchungen und NULL-Erhalt ohne Referenz.
- `tests/integration/test_open_item_reconciliation.py`: gezielte Abstimmungs-, Stichtags-, Kontrollkonto- und Geschäftsjahres-Integrationstests.
- `tests/ui/test_open_item_reconciliation_widget.py`: Darstellung, Stichtagsweitergabe, Differenz und ausschließlich lesende UI-Aktion.
- `tests/database/test_migration_service.py` und `tests/database/test_migrations.py`: Migrations- und Head-Revision-Absicherung.

Neben dem neuen Datumsfeld am bestehenden Korrekturkopf wurden keine anderen OP-Datenmodelle oder Zahlungsbuchungsabläufe verändert. E-Bilanz-/ERiC-Funktionen und Mandantentransferfunktionen blieben unverändert.

## Berechnungsregeln

### Geschäftsjahr und Hauptbuch

Für den Hauptbuchsaldo wird das Geschäftsjahr mit dem jüngsten `start_date` bis einschließlich des Stichtags verwendet. Innerhalb dieses Geschäftsjahrs werden die Buchungszeilen bis zum Stichtag saldiert. So werden im Folgejahr die dort vorhandenen Eröffnungsbuchungen einbezogen, während die Vorjahresbewegungen nicht ein zweites Mal addiert werden. Das folgt der in SimpleOB vorhandenen Jahresabschluss- und Eröffnungsbuchungssystematik.

Gibt es noch kein Geschäftsjahr, dessen `start_date` am oder vor dem Stichtag liegt, wird kein Geschäftsjahr eingeschränkt; vorhandene Buchungen des Mandanten bis zum Stichtag werden dann berücksichtigt. Bei Geschäftsjahreslücken, überlappenden Geschäftsjahren oder nicht ausgeführten erforderlichen Eröffnungsbuchungen ist das Ergebnis deshalb anhand der Mandantenkonfiguration zu beurteilen.

### OP-Saldo und Datumsabgrenzung

Der OP-Saldo wird aus dem unveränderlichen Ursprungsbetrag und den zugehörigen Ereignissen rekonstruiert. Ein Rechnungs- oder Gutschriften-OP beginnt erst ab dem Buchungsdatum seiner Ursprungshauptbuchbuchung. Ereignisse werden nur einbezogen, wenn ihr maßgebliches Buchungsdatum spätestens am gewählten Stichtag liegt:

- Zahlung: Buchungsdatum der über `Zahlung.booking_id` referenzierten Hauptbuchbuchung. Zahlungsdatum und `effective_date` ändern die Stichtagsabgrenzung nicht.
- Gutschriftenverrechnung: Buchungsdatum der Hauptbuchbuchung des Verrechnungsvorgangs.
- Korrektur einer Zahlungszuordnung: gespeichertes `booking_date` am Korrekturkopf, unabhängig davon, ob eine Hauptbuchumbuchung entstanden ist. Bei einer Umbuchung wird zusätzlich geprüft, dass deren Hauptbuchdatum mit dem gespeicherten Datum übereinstimmt.
- Historische Korrektur ohne rekonstruierbares `booking_date`: nicht in den scheinbar exakten OP-Saldo einrechnen; betroffene Konten als `ZEITLICH_UNGEKLAERT` kennzeichnen und Korrekturdatum, Begründung, Betrag und OP-Referenzen als Detail anzeigen.

Für Rechnungs-OPs vermindern Zahlungen und Verrechnungen den offenen Betrag. Korrekturereignisse verwenden das vorhandene Vorzeichenmodell; deren `amount_delta` wird entsprechend der vorhandenen Restbetragsberechnung verrechnet. Für Guthaben-OPs werden die signierten Guthabenereignisse addiert; eine Verrechnung vermindert den Guthabenbetrag.

### Vorzeichen

Die Salden werden jeweils auf ihrer normalen Kontenseite positiv ausgewiesen:

| Rolle | Kontotyp | Positiver Hauptbuchsaldo |
| --- | --- | --- |
| Kundenforderungen | Aktivkonto | Soll minus Haben |
| Lieferantenverbindlichkeiten | Passivkonto | Haben minus Soll |
| Kundenguthaben | Passivkonto | Haben minus Soll |
| Lieferantenguthaben | Aktivkonto | Soll minus Haben |

Die OP-Beträge werden positiv in derselben fachlichen Richtung ausgewiesen. Die Differenz ist Hauptbuchsaldo minus OP-Saldo. Null ist saldengleich.

### Kontoermittlung und ungeklärte Bewegungen

Ein Rechnungs- oder Gutschriften-OP wird seinem tatsächlichen Ursprungskonto zugeordnet. Das Repository verlangt dazu genau ein Konto passenden Mandanten und Kontotyps, auf der für die OP-Rolle normalen Buchungsseite, dessen aggregierter Betrag dem OP-Ursprungsbetrag entspricht. Kann dieses Konto nicht eindeutig festgestellt werden, wird die Rolle als `OP_KONTO_UNERMITTELBAR` gekennzeichnet; die betroffene OP-Summe wird nicht willkürlich einem konfigurierten Konto zugerechnet.

Konten, die aus historischen Ursprungsbuchungen gefunden werden, bleiben als eigene Zeile sichtbar, auch wenn eine Rolle inzwischen einem anderen Konto zugeordnet ist. Solche Konten erhalten den Status `KONTO_NICHT_MEHR_ZUGEORDNET`. Ein nicht vorhandenes oder mit falschem Kontotyp geführtes Konto erhält `KONTOFEHLER`.

Eine Sammelkonto-Buchungszeile wird als ungeklärt angezeigt, wenn ihre Buchung keinem erkannten OP-Ursprung, Zahlung, Verrechnung oder einer verknüpften Korrektur angehört. Der Bericht benennt keine Ursache. Eine manuelle Zuordnung oder Buchung wird nicht vorgenommen.

## Statuswerte

- `ABGESTIMMT`: Salden stimmen überein, die Kontenzuordnung ist aktuell und es ist keine unzugeordnete Bewegung erkennbar.
- `ABWEICHUNG`: Hauptbuch- und OP-Saldo unterscheiden sich.
- `UNGEKLAERTE_BEWEGUNG`: Mindestens eine Bewegung auf dem Sammelkonto hat keinen erkannten OP-Vorgang; die Bewegung wird separat aufgelistet.
- `OP_KONTO_UNERMITTELBAR`: Mindestens ein Ursprungskonto kann nicht anhand der Ursprungsbuchung eindeutig zugeordnet werden.
- `KONTO_NICHT_MEHR_ZUGEORDNET`: Das historische Konto ist für die OP-Rolle aktuell nicht mehr konfiguriert.
- `KONTOFEHLER`: Das Konto fehlt oder sein gespeicherter Typ passt nicht zur Rolle.
- `ZEITLICH_UNGEKLAERT`: Mindestens eine historische Zahlungszuordnungskorrektur hat kein bekanntes Buchungsdatum; der angezeigte OP-Saldo ist für den Stichtag nicht als exakt bestätigt.
- `NICHT_KONFIGURIERT`: Für die Rolle ist kein Sammelkonto konfiguriert und es wurde kein historisches Ursprungskonto ermittelt.

## Prüfungen

Neu hinzugefügte Integrationstests prüfen:

- unbezahlte Ausgangsrechnung, Teilzahlung und historische Abgrenzung vor/nach dem Zahlungsbuchungsdatum;
- Kundengutschriftenverrechnung zusammen mit einer Teilzahlung;
- Lieferantenrechnung und Lieferantengutschriftenverrechnung;
- Korrektur einer Zahlungszuordnung ohne zusätzliche Hauptbuchbuchung bei gleichem Konto;
- abweichendes Korrektur- und Buchungsdatum mit Stichtag vor/nach dem Buchungsdatum, Buchungsdatumsprüfung im Geschäftsjahr sowie unveränderter Zahlung und Bankbuchung;
- Migration: Datum aus referenzierter Hauptbuchumbuchung übernehmen, ohne Referenz NULL erhalten; Rückbau der neuen Migration;
- historische Korrektur mit unbekanntem Buchungsdatum wird sichtbar zeitlich ungeklärt und nicht als abgestimmt markiert;
- Erkennung einer unverbundenen manuellen Buchung und Darstellung der konkreten Bewegung;
- getrennte Salden historisch verwendeter und aktuell konfigurierter Kundenforderungskonten;
- Rechnung im Geschäftsjahr 2025, Jahresabschluss und Folgejahreseröffnung mit den vorhandenen Workflows, Zahlung 2026 sowie unveränderte Abstimmung zum 31.12.2025;
- Qt-Widget zeigt Stichtag, Differenz und Aktualisierung ohne Buchungs- oder Korrekturaktion.

Ausgeführt:

- OP-, Rechnungs-, Gutschriften-, Zahlungs-, Verrechnungs-, Korrektur- und Jahresabschluss-/Eröffnungs-Regressionen: **70 bestanden, 2 übersprungen**.
- SQLite-Migrationsdiensttests (PostgreSQL-Fälle ausgefiltert): **7 bestanden, 15 ausgefiltert**; darunter Upgrade auf Head und gezielter Backfill-/NULL-/Downgrade-Test dieser Migration.
- übrige Migrationstests ohne vollständigen Downgrade zur Baseline: **4 bestanden, 1 ausgefiltert**.
- `tests/ui/test_open_item_reconciliation_widget.py` mit `QT_QPA_PLATFORM=offscreen`: **1 bestanden**.
- Ruff auf allen geänderten Python-Dateien: **bestanden**.
- `git diff --check`: **bestanden**.

Die Qt-Ansicht wurde automatisiert unter Offscreen-Bedingungen geprüft, aber nicht interaktiv in einer Desktop-Sitzung abgenommen.

Der vollständige Downgrade bis zur Baseline wurde ebenfalls geprüft und scheitert in der bereits vorhandenen Migration `cf6b9217da40` beim Wiederanlegen einer nicht benannten Unique-Constraint. Der Downgrade der neuen Migration `c71f4db9e2a6` auf ihre direkte Vorgängerrevision ist dagegen im gezielten Migrationstest erfolgreich. PostgreSQL-Tests wurden im abschließenden Lauf ausgefiltert; die bekannte PostgreSQL-Testumgebung war nicht Gegenstand dieser Stufe.

## Einschränkungen und Risiken

1. **Ungeklärte Bewegungen:** Die Erkennung basiert auf dem Vorhandensein eines OP-bezogenen Vorgangs mit derselben Hauptbuchreferenz. Sie prüft nicht vollständig, ob jede einzelne Kontrollkontozeile eines bereits verknüpften Vorgangs in Betrag und Richtung exakt seiner fachlichen Erwartung entspricht. Solche Fehler können als Saldenabweichung sichtbar werden, aber nicht zwingend als konkrete ungeklärte Einzelbewegung.
2. **Historische Korrektur ohne Buchung:** Für Altzeilen ohne Hauptbuchreferenz ist das ursprünglich gewählte Buchungsdatum nicht rekonstruierbar. Die Migration lässt das Feld NULL; die Abstimmung kennzeichnet diese Fälle zeitlich ungeklärt und verwendet `correction_date` nicht als Ersatz.
3. **Rollenhistorie:** Die Anwendung speichert keine zeitliche Historie der Rollenbelegung. Der Bericht weist historische Konten anhand der tatsächlichen OP-Ursprungsbuchungen aus und markiert Konten, die aktuell nicht mehr zugeordnet sind.
4. **Eröffnungsbuchungen:** Für ein Folgejahr setzt ein mit dem Hauptbuch vergleichbarer Saldo die vorhandenen Eröffnungsbuchungen voraus. Fehlen sie, kann das Hauptbuch den Vorjahresbestand im Folgejahr nicht ausweisen; eine daraus entstehende Differenz wird angezeigt.
5. **Manuelle Sammelkonto-Zuordnung:** Eine Zuordnung nicht verknüpfter Bewegungen ist ausdrücklich nicht Teil von 4A und bleibt der späteren Stufe 4B vorbehalten.
6. **Storno, Anzahlungen, Überzahlungen und § 19 UStG:** Diese Bereiche werden nicht ergänzt und sind nicht Bestandteil der Abstimmungsansicht.

## Abschluss

Die Stufe bietet die vereinbarte stichtagsbezogene, lesende Abstimmung einschließlich Geschäftsjahreswechsel und sichtbar ungeklärter Sammelkontobewegungen. Kein Commit wurde erstellt. Unabhängige Änderungen im Arbeitsbaum wurden nicht bearbeitet.

## Korrektur- und Buchungsdatum

Die Nachprüfung hatte gezeigt, dass Stufe 3D das ausdrücklich gewählte Buchungsdatum bei identischen Sammelkonten verworfen hat. Stufe 4A korrigiert dies mit dem Feld `booking_date` am Korrekturkopf. Das Feld ist im Domainvorgang verpflichtend, während die Datenbank NULL für nicht rekonstruierbare Altzeilen zulässt.

Die neue Alembic-Migration `c71f4db9e2a6` hängt an Revision `7d0c4a28b9f1`. Sie ergänzt die nullable Date-Spalte. Für Korrekturen mit `booking_id` übernimmt sie das tatsächliche `Buchung.booking_date`. Für Datensätze ohne Hauptbuchreferenz bleibt das Feld NULL; die Migration setzt es ausdrücklich nicht aus dem Korrekturdatum.

Service und Repository verlangen für neue Vorgänge ein Buchungsdatum und prüfen es unabhängig vom Korrekturdatum gegen das angegebene, vorhandene und offene Geschäftsjahr des Mandanten. Bei einer Hauptbuchumbuchung muss ihr Buchungsdatum mit dem Datum am Korrekturkopf übereinstimmen. Ohne Umbuchung wird das Datum trotzdem gespeichert. Das Korrekturdatum und `recorded_at` bleiben eigene Angaben; die Hauptbuchbuchung der ursprünglichen Zahlung wird nicht verändert.

Die Abstimmung verwendet ausschließlich das gespeicherte Korrekturbuchungsdatum. Ereignisse mit einem Datum nach dem Stichtag bleiben außen vor. Datensätze mit NULL-Datum werden nicht anhand des Korrekturdatums geschätzt oder eingerechnet. Für die betroffenen Sammelkonten erscheint der Status `ZEITLICH_UNGEKLAERT`; die Detailansicht zeigt Korrekturdatum, ausdrücklich „Unbekannt (Altbestand)“ als Buchungsdatum, Betrag, Quell- und Ziel-OP sowie Begründung. Der Status hat Vorrang vor `ABGESTIMMT`, auch wenn die rechnerische Differenz null ist.

Der geforderte Regressionstest setzt Korrekturdatum und Buchungsdatum auseinander, prüft den gespeicherten Wert und die Stichtagsgrenze vor und nach diesem Datum. Weil die beiden OP-Ereignisse bei gemeinsamem Sammelkonto in Summe null ergeben, prüft er zusätzlich die Datumsgrenze mit der zur Berechnung verwendeten fokussierten Funktion. Weitere Tests decken die Geschäftsjahresgrenze ohne Umbuchung, den Erhalt der Zahlung und Bankbuchung sowie die zeitliche Kennzeichnung einer historischen NULL-Korrektur ab.

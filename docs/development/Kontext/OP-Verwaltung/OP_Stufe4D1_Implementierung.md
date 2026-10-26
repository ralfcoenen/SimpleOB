# Stufe 4D-1 – Allgemeines Journal-Storno für OP-Buchungen absichern

**Ausgangsbasis:** `ef517100c184c3e3360c7fada48872b1a1861d66`

**Umfang:** Verhindert das isolierte Storno von Hauptbuchursprungsbuchungen gebuchter Kunden-/Lieferantenrechnungen und Kunden-/Lieferantengutschriften. Es wurde kein OP-Stornovorgang implementiert.

## Umsetzung

### Tatsächlich abgesicherte Aufrufwege

1. `FiscalYearWorkspace.create_reversal_booking()` in `src/simpleob/services/fiscal_year_workspace.py` fragt vor der Erzeugung der Gegenbuchung beim Repository ab, ob die ausgewählte Originalbuchung ein OP-Ursprungsbeleg ist. Dadurch wird der übliche Journalweg bereits vor Buchungsvorschau und Bestätigung mit einer verständlichen `ValueError` beendet.
2. `BookingRepository.add()` in `src/simpleob/database/booking_repository.py` führt dieselbe fachliche Prüfung zusätzlich beim Persistieren jeder `BookingType.REVERSAL`-Buchung durch. Dies schützt auch direkte Repository-Aufrufe oder weitere gegenwärtige Aufrufwege, die `FiscalYearWorkspace.create_reversal_booking()` nicht verwenden.
3. `FiscalYearWorkspace.post_booking()` delegiert reguläre Stornobuchungen an `BookingRepository.add()`. Der Anlagen-Sonderweg verwendet ebenfalls dieses Repository; sein zusätzlicher Nebenbuchpfad betrifft Anlagenbewegungen, nicht OP-Belege. Der Einlagen-Sonderweg akzeptiert nur reguläre Buchungen. `PostingService.post_booking()` ist nur ein In-Memory-Buchungspfad und persistiert keine Buchung.

Die Prüfung verknüpft die `reversal_of_booking_id` mit `Ausgangsrechnung.booking_id`, `Eingangsrechnung.booking_id` oder `Gutschrift.booking_id` und filtert jeweils nach `mandant_id` des geöffneten Mandanten/Geschäftsjahrs. Die Unterscheidung basiert nicht auf Buchungstext, Kontoname oder Kontonummer. `Gutschrift` umfasst beide Gutschriftenarten.

### Fehlermeldung

> Diese Buchung gehört zu einem OP-Beleg. Für Kunden- und Lieferantenrechnungen sowie Kunden- und Lieferantengutschriften ist eine spezielle OP-Stornierung erforderlich; diese Funktion wird in einer späteren Stufe implementiert.

### Verhalten gewöhnlicher Buchungen

Das vorhandene allgemeine Storno bleibt für Buchungen ohne OP-Belegbeziehung verfügbar. Soll-/Haben-Umkehr, Geschäftsjahres- und Abschlussprüfung sowie Schutz vor doppelter Stornierung bleiben erhalten. Auch die Ablage gewöhnlicher Stornobuchungen und bestehende OP-Funktionen wurden nicht geändert.

Die zentrale Sperre blockiert gezielt nur eine Gegenbuchung, deren referenzierte Ursprungsbuchung als OP-Beleg desselben Mandanten gespeichert ist. Sie sperrt weder Sammelkonten generell noch gewöhnliche Buchungen, die zufällig dieselbe Kontonummer verwenden.

### Abgrenzung für spätere OP-Stornierung

Es gibt weiterhin keinen OP-Stornoservice und keine OP-Stornoereignisse. Eine spätere ausdrücklich autorisierte OP-Stornierung muss einen eigenen, kontrollierten Service-/Persistenzpfad erhalten, der OP-Stornokopf, Gegenbuchung(en) und OP-Ereignisse atomar gemeinsam speichert. Es wurde kein frei wählbarer `allow_reversal`-Parameter und kein UI-Bypass eingeführt. Die allgemeine `add()`-Methode bleibt absichtlich gesperrt; eine spätere autorisierte Funktion muss als gesonderter, fachlich validierter Repository-Ablauf ergänzt werden.

## Tests und Prüfungen

Neue fokussierte Integrationstests in `tests/integration/test_op_journal_reversal_protection.py` prüfen:

- Ablehnung eines allgemeinen Journal-Gegenbuchungsversuchs für Kundenrechnung, Lieferantenrechnung, Kundengutschrift und Lieferantengutschrift.
- Keine zusätzliche Hauptbuch-Gegenbuchung und unveränderte Ursprungsbelege/-OPs; keine Zahlungs-, Zahlungszuordnungs-, Verrechnungs- oder Guthabenereignisse werden erzeugt.
- Weiterhin mögliche Gegenbuchung einer gewöhnlichen Buchung mit der Kontonummer `1200`; maßgeblich ist die Belegbeziehung, nicht eine Kontonummer.

Der bestehende Test `test_create_reversal_booking_mirrors_original_booking` in `tests/services/test_fiscal_year_workspace.py` prüft jetzt außerdem, dass der Workspace vor dem Erzeugen einer Journal-Gegenbuchung die OP-Ursprungsprüfung aufruft.

Ausgeführt:

```text
.venv/bin/pytest -q tests/integration/test_op_journal_reversal_protection.py tests/database/test_booking_repository.py tests/services/test_fiscal_year_workspace.py -k 'reversal or reverse or ordinary_booking_can_still_be_reversed'
17 passed, 72 deselected

.venv/bin/ruff check src/simpleob/database/booking_repository.py src/simpleob/services/fiscal_year_workspace.py tests/integration/test_op_journal_reversal_protection.py tests/services/test_fiscal_year_workspace.py
All checks passed

git diff --check
sauber
```

## Geänderte Dateien

- `src/simpleob/database/booking_repository.py` – mandantenbezogene zentrale Prüfung bei jeder persistierten Gegenbuchung.
- `src/simpleob/services/fiscal_year_workspace.py` – frühe Prüfung vor der Erzeugung eines Journal-Stornos.
- `tests/integration/test_op_journal_reversal_protection.py` – vier Belegarten und gewöhnliche Buchung.
- `tests/services/test_fiscal_year_workspace.py` – Prüfung des UI-nahen Workspace-Aufrufwegs.
- `docs/development/Kontext/OP-Verwaltung/OP_Stufe4D1_Implementierung.md` – dieser Bericht.

## Verbleibende Einschränkungen

- Die Fehlermeldung weist auf eine spätere OP-Stornofunktion hin; diese bleibt außerhalb dieses Umfangs.
- Die Prüfungen schützen gegen aktuelle OP-Dokumentbeziehungen. Eine spätere Stornoimplementierung muss eine eigene, eng begrenzte Autorisierung auf Service-/Repositoryebene etablieren und die dann vorhandenen OP-Stornodaten atomar validieren.
- Tests wurden gezielt lokal mit SQLite ausgeführt. PostgreSQL wurde in dieser Stufe nicht geprüft; die bekannte PostgreSQL-Testeinschränkung bleibt unberührt.
- Unabhängige Änderungen im Arbeitsbaum wurden nicht verändert.

Es wurden keine Migrationen, Änderungen an OP-Restbetragsberechnungen oder Änderungen an E-Bilanz/ERiC vorgenommen. Es wurde kein Commit erstellt.

# SimpleOB – Stufe 4D-2a: Kompakte OP-Übersicht

## Umsetzung

Die OP-Übersicht wurde nach Variante B des Layoutentwurfs umgesetzt. Die Hauptansicht zeigt keine Ereignistabelle mehr dauerhaft. Die OP-Zeilen- und Summenauswertung stehen in zwei internen Ansichten „Einzelposten“ und „Summen“. Die kompakte Aktionsleiste bietet „Details“ und – sofern ein Stornoservice übergeben wurde – „Rechnung vollständig stornieren“.

Ein neuer modaler, rein lesender `OpenItemDetailDialog` zeigt Partner, OP-Art, Belegnummer, Beleg- und Buchungsdatum, gegebenenfalls Fälligkeit, Ursprungsbetrag, Zahlungen, Verrechnungen, aktuellen Restbetrag sowie die vom bestehenden Overview-Service gelieferten Ereignisse. Darunter sind Ereignisart, Vorgangs- und Buchungsdatum, Betrag, lesbare Referenz und Hinweis sichtbar. Der Dialog nimmt keine Schreiboperation vor.

## Filter

Drei Filter wirken gemeinsam auf Einzelposten und Summen:

- Partnerart: Alle, Kunden, Lieferanten.
- Status: Nur offene, Nur vollständig ausgeglichene, Alle Posten.
- Geschäftspartner: Alle oder ein einzelner Partner.

Der Partnerartfilter gruppiert `CUSTOMER_RECEIVABLE` und `CUSTOMER_CREDIT` als Kunden sowie `SUPPLIER_PAYABLE` und `SUPPLIER_CREDIT` als Lieferanten. Geschäftspartner mit beiden Rollen können in beiden Kategorien erscheinen. Die Partnerauswahl passt sich der aktuellen Partnerart und dem Status an. Wenn ein Filterwechsel die ausgewählte OP-Zeile nicht entfernt, bleibt sie ausgewählt; andernfalls wird eine sichtbare Zeile ausgewählt.

Es war keine Repository- oder Domainänderung erforderlich. Das vorhandene Repository liefert alle vier Arten; der Widgetfilter verwendet diese Daten und den bereits berechneten Restbetrag. Die Summenansicht wird aus derselben gefilterten OP-Menge aufgebaut wie die Einzelpostenansicht.

## Navigation und Stornoaktion

Details lassen sich per Doppelklick, Enter, Return oder Schaltfläche öffnen. Das Kontextmenü enthält „Details anzeigen“ und, wenn die Funktion vorhanden ist, „Rechnung vollständig stornieren“. Die sichtbare Stornoschaltfläche und der Menüeintrag verwenden dieselbe UI-Zulässigkeitsprüfung: ausgewählter offener Rechnungs-OP, verfügbarer Stornoservice und Geschäftsjahr. Guthaben und ausgeglichene Posten erlauben diese Aktion nicht. Die abschließende fachliche Prüfung bleibt beim Service.

Der bisherige Stornoablauf bleibt erhalten: Vorschau, Abfrage von Buchungsdatum und verpflichtendem Grund sowie explizite Bestätigung. Nach Erfolg wird die OP-Übersicht neu geladen und der bestehende MainWindow-Callback zur Aktualisierung der Hauptbuchanzeigen aufgerufen. Zahlungs-, Verrechnungs- und Zahlungszuordnungskorrekturdialoge bleiben im Reiter „Buchen“.

## Geänderte Dateien

- `src/simpleob/ui_qt/open_item_overview_widget.py` – kompaktes Layout, kombinierte Filter, Auswahlbeibehaltung, interne Ansichten, Navigation und gemeinsame Stornozulässigkeit für Schaltfläche/Kontextmenü.
- `src/simpleob/ui_qt/open_item_detail_dialog.py` – neuer modaler, rein lesender Detaildialog.
- `tests/ui/test_open_item_overview_widget.py` – fokussierte Filter-, Detail-, Navigation-, Kontextmenü- und Stornotests.
- `docs/development/Kontext/OP-Verwaltung/OP_Stufe4D2a_Implementierung.md` – dieser Bericht.

Keine Änderungen an Buchungs- oder Zahlungsservices, OP-Berechnungen, Abstimmung, Datenbankmodell, Migrationen, E-Bilanz/ERiC oder bestehenden Zahlungs-/Verrechnungs-/Korrekturdialogen. Es wurden keine Funktionen aus Stufe 4D-3 vorgezogen.

## Tests und Prüfungen

- Der Benutzer hat die praktische GUI-Abnahme erfolgreich durchgeführt.
- `tests/ui/test_open_item_overview_widget.py` prüft zusätzlich ausdrücklich Enter und Return als Tastaturwege zum Detaildialog.
- `tests/ui/test_open_item_overview_widget.py` prüft zusätzlich, dass ein vorhandenes Verrechnungsereignis mit Referenz und Betrag in den Detaildaten dargestellt wird.
- Die UI-Tests benötigen in Umgebungen ohne native Bildschirmfläche `QT_QPA_PLATFORM=offscreen`; ohne diese Plattform kann Qt beim Anzeigen eines Fensters mit „Cannot create window: no screens available“ abbrechen.
- `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/ui/test_open_item_overview_widget.py` – **3 bestanden**.
- `env -u SIMPLEOB_POSTGRES_TEST_URL QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/integration/test_open_item_overview.py` – **8 bestanden, 1 PostgreSQL-Test übersprungen**. Die vorhandene URL wies auf `simpleob_migration_test`, aber den Benutzer `ralf`; deshalb wurde sie entfernt und keine PostgreSQL-Verbindung hergestellt.
- `.venv/bin/ruff check src/simpleob/ui_qt/open_item_overview_widget.py src/simpleob/ui_qt/open_item_detail_dialog.py tests/ui/test_open_item_overview_widget.py` – **bestanden**.
- `git diff --check` – **bestanden**.

Die praktische GUI-Abnahme war erfolgreich. Eine systematische Abnahme sämtlicher Plattform- und Bildschirmgrößen ist damit nicht dokumentiert. Es wurde noch kein Commit erstellt.

## Einschränkungen

- Die Übersicht zeigt weiterhin aktuelle Restbeträge, keine historische OP-Einzelposten-Stichtagsauswertung.
- Details zu Zahlungen, Verrechnungen, Zahlungszuordnungskorrekturen und Rechnungsstornos beruhen auf den vorhandenen Ereignisdaten und der bestehenden `get_detail()`-Abfrage.
- Die Aktionen Zahlung, Gutschriftenverrechnung und Zahlungszuordnungskorrektur werden noch nicht aus der OP-Übersicht geöffnet.
- Die UI-Zulässigkeit blendet keine fachlichen Servicegründe vorab ein; nicht zulässige Stornos werden weiterhin durch die vorhandene Vorschau-/Serviceprüfung erklärt.
- Die optionale PostgreSQL-spezifische Integration wurde nicht ausgeführt; diese UI-Änderung benötigt keine PostgreSQL-Prüfung.

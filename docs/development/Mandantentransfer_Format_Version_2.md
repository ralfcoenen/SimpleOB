# Mandantentransferformat Version 2

Version 2 ergänzt den bestehenden portablen Mandantentransfer um die
Personenkonten- und Partnerzuordnung. Version 1 bleibt lesbar und wird beim
Einlesen ohne Personenkontenlisten als Transfer ohne Personenkonten behandelt.
Neue Exporte verwenden Version 2.

## Neue Felder

`client.business_partners` enthält die referenzierten Geschäftspartner mit
stabiler Partner-UUID, Name, Kunden-/Lieferantenrolle und Aktivstatus.
`client.person_accounts` verbindet eine fünfstellige Kontonummer mit Partner-UUID
und Rolle (`DEBITOR` oder `KREDITOR`). Ein Partner kann in beiden Rollen
referenziert werden.

## Validierung und Import

Vor dem Import werden Kontoreferenz, Rollen-Nummernkreis, Eindeutigkeit,
Partnerrollen, Namensgleichheit von Partner und Konto sowie fehlende individuelle
HGB-Zuordnungen geprüft. Nicht referenzierte Partner und fehlende Partner- oder
Kontodatensätze werden abgelehnt. Anschließend legt der Import Partner, Konten
und Zuordnungen innerhalb derselben Datenbanktransaktion an. Ein Fehler rollt
den gesamten Import zurück.

Die regulären Kontenfelder einschließlich vorhandener HGB-Zuordnungen bleiben
Bestandteil des Transfers und werden unverändert verarbeitet. Die OP-Datenfelder
des Transfervertrags wurden nicht geändert.

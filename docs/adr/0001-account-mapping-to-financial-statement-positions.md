# ADR-0001: Konten werden Abschlusspositionen zugeordnet

**Status:** Accepted
**Datum:** 31.07.2026
**Version:** 0.12.0

## Kontext

Die Summen- und Saldenliste enthält für jedes Konto die Soll- und Habenumsätze sowie den Soll- oder Habensaldo.

Für die Erstellung einer Bilanz oder Gewinn- und Verlustrechnung reicht der allgemeine `AccountType` eines Kontos jedoch nicht aus.

Der Kontotyp ermöglicht lediglich eine grobe Einordnung:

* `ASSET`
* `LIABILITY`
* `EQUITY`
* `REVENUE`
* `EXPENSE`

Er bestimmt nicht, in welcher konkreten Position des Jahresabschlusses ein Konto auszuweisen ist.

Außerdem kann ein Konto einen atypischen Saldo besitzen. Beispielsweise kann ein Bankkonto mit Sollsaldo als Aktivposten und mit Habensaldo als Verbindlichkeit auszuweisen sein.

Eine feste Zuordnung allein anhand des Kontotyps oder der Bilanzseite wäre deshalb fachlich nicht ausreichend.

## Entscheidung

Konten werden nicht unmittelbar einer Bilanzseite oder einer GuV-Seite zugeordnet.

Stattdessen wird ein Konto einer konkreten Abschlussposition zugeordnet.

Die Zuordnung kann von der Saldenrichtung abhängen. Für dasselbe Konto können daher unterschiedliche Zielpositionen für Sollsaldo und Habensaldo vorgesehen werden.

Der fachliche Datenfluss lautet:

```text
TrialBalanceRow
        +
Kontenzuordnung
        ↓
Abschlussposition
        ↓
BalanceSheet oder IncomeStatement
```

Die Zuordnungslogik wird außerhalb von

* `TrialBalance`,
* `BalanceSheet`,
* `BalancePosition`,
* `Account`
* und `TemplateAccount`

implementiert.

Damit bleiben diese Klassen unabhängig von Kontenrahmen, HGB-Gliederungen und konkreten Ausweisregeln.

## Konsequenzen

### Positive Konsequenzen

* Atypische Kontensalden können fachlich korrekt behandelt werden.
* Die Bilanz bleibt unabhängig von SKR03, SKR04 oder anderen Kontenrahmen.
* Unterschiedliche Kontenrahmen können eigene Zuordnungen bereitstellen.
* Die spätere Zuordnung zu HGB- oder Taxonomiepositionen bleibt möglich.
* Bilanz und GuV können dieselbe Zuordnungsarchitektur verwenden.

### Negative Konsequenzen

* Für die Erstellung eines Jahresabschlusses wird eine zusätzliche Zuordnungskomponente benötigt.
* Ein `AccountType` allein genügt nicht für die vollständige Abschlussdarstellung.
* Fehlende oder mehrdeutige Kontenzuordnungen müssen später erkannt und behandelt werden.

## Nicht Bestandteil dieser Entscheidung

Dieses ADR legt noch nicht fest:

* wie die Zuordnungsregeln technisch gespeichert werden,
* wie die Zuordnungskomponente benannt wird,
* ob Positionscodes als `str`, `Enum` oder eigener Werttyp dargestellt werden,
* wie SKR03- oder SKR04-Zuordnungen aussehen,
* wie HGB- oder E-Bilanz-Taxonomien eingebunden werden.

Diese Entscheidungen werden erst getroffen, wenn dafür konkrete Anforderungen vorliegen.


## Historie

Entstanden während Version 0.12.0
Auslöser:
Beim Entwurf des BalanceSheetBuilder wurde erkannt,
dass der AccountType für eine fachlich korrekte
Bilanzzuordnung nicht ausreicht.

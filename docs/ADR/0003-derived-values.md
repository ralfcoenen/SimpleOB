# ADR-0003: Primärdaten speichern

## Status

Accepted

## Kontext

Redundante Daten führen leicht zu Inkonsistenzen.

## Entscheidung

Nur Primärdaten werden gespeichert.

Abgeleitete Werte werden berechnet.

Beispiele:

* Kontosalden
* Bilanzsummen
* Gewinn
* duration_days
* calendar_years

werden nicht persistent gespeichert.

## Konsequenzen

* Keine redundanten Daten
* Konsistente Berechnungen
* Einfachere Wartung

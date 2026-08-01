# Entwicklungsrichtlinien für OpenBilanzUG

## 1. Grundprinzipien

Die Entwicklung von OpenBilanzUG folgt nicht primär technischen, sondern fachlichen Anforderungen. Ziel ist die Erstellung einer transparenten, fachlich korrekten und langfristig wartbaren Anwendung zur Erfüllung handels- und steuerrechtlicher Pflichten, insbesondere zur Erstellung einer E-Bilanz.

Die nachfolgenden Grundprinzipien bilden den verbindlichen Rahmen für alle Architektur-, Entwurfs- und Implementierungsentscheidungen.

### 1.1 Fachlichkeit vor Technik

Die Fachlichkeit bestimmt das Modell; die Technik dient ausschließlich ihrer Umsetzung.

Architektur und Quellcode werden aus den fachlichen Anforderungen der doppelten Buchführung und des handelsrechtlichen Jahresabschlusses abgeleitet. Technische Möglichkeiten oder Frameworks dürfen diese Modellierung nicht bestimmen.

### 1.2 Domain First

Der fachliche Kern wird unabhängig von Benutzeroberflächen, Datenbanken, Import- und Exportformaten entwickelt.

Alle Infrastrukturkomponenten greifen auf das Domänenmodell zu; das Domänenmodell kennt diese Komponenten jedoch nicht.

### 1.3 Testgetriebene Entwicklung

Neue Funktionalität entsteht grundsätzlich testgetrieben.

Jede fachliche Anforderung wird zunächst als Test formuliert. Erst anschließend erfolgt die kleinstmögliche Implementierung, gefolgt von einer bewussten Überarbeitung des Codes.

### 1.4 Kleine Entwicklungsschritte

Die Entwicklung erfolgt in kleinen, fachlich abgeschlossenen Schritten.

Jeder Entwicklungsschritt soll nachvollziehbar sein, einen klaren fachlichen Mehrwert liefern und durch Tests abgesichert werden.

### 1.5 Dokumentation begleitet die Entwicklung

Dokumentation ist Bestandteil der Entwicklung und wird nicht nachträglich erstellt.

Wesentliche Architekturentscheidungen werden als ADR dokumentiert. Grundlegende Projektentscheidungen werden in den entsprechenden Projektdokumenten nachvollziehbar festgehalten.

### 1.6 Architektur entsteht schrittweise

Architektur wird nicht vollständig im Voraus entworfen.

Sie entwickelt sich durch begründete Entscheidungen, die aus den fachlichen Anforderungen hervorgehen und kontinuierlich überprüft werden.

### 1.7 Langfristige Wartbarkeit

Kurzfristige Vereinfachungen dürfen die langfristige Verständlichkeit und Erweiterbarkeit des Projekts nicht beeinträchtigen.

Komplexität wird nur eingeführt, wenn sie fachlich erforderlich ist und einen nachvollziehbaren Nutzen bietet.


# Rechenlabor zur Gesamtausgabe v9.18

Die kompakte Ausgabe enthält die früheren Bachelor-Lehrübungen und das QSS-Prüflabor mit den vier wiederholten Studien. Unter `rechenlabor/qss_pruefung/messung/revisionsvergleich.csv` stehen alle 1.513 gepaarten Konfigurationen. Der erste Kalenderstand ist `d656b6f`. Auf dem abschließenden Solverstand `c635504` wurden alle 1.513 Einstellungen erneut ausgeführt. Zusätzlich stehen 82 Vertragsproben und zwölf gezielte Gegenläufe mit erweitertem Zeitlimit bereit. Die 1.176 beidseitig protokollierten Fehlerwerte stimmen überein. Alle 135 Statuswechsel betreffen Zeitüberschreitungen im ersten Lauf. [Gegenlauf auf dem geprüften Solver](rechenlabor/qss_pruefung/messung/skalenfix_c635504/skalenvergleich.csv)

## Das vollständige Labor öffnen

Beim GitHub-Actions-Lauf **Studienbuch** entsteht die Datei `ARGESIM_Rechenlabor_v9_18.zip` mit allen Quelltexten, Modellgewichten, Feldmessungen und Druckvorlagen. Sie lässt sich auch aus einem Checkout der veröffentlichten Revision mit der Python-Standardbibliothek erzeugen.

```bash
python scripts/build_studienbuch.py --check
python scripts/build_studienbuch.py --full-lab ARGESIM_Rechenlabor_v9_18.zip
python -m zipfile -e ARGESIM_Rechenlabor_v9_18.zip labor
cd labor
python pruefen.py
```

Die zehn Feldarchive liegen im Repository unter `pakete/` in nummerierten Teilen. Der Aufbau prüft den SHA-256-Wert jedes zusammengesetzten Archivs. Die Tabellen, Abbildungen und Programme behalten im entpackten Labor ihre ursprünglichen relativen Pfade. Die Python- und C++-Programme, die optionale Bibliotheken oder einen Compiler benötigen, sind in den jeweiligen Versuchsanleitungen beschrieben.

## Kalenderfehler nachvollziehen

Der kleinste positive Binär64-Wert ist `u = math.ulp(0.0)`. Das Polynom mit den Koeffizienten `[2*u, -3*u, u]` hat die erste positive Nullstelle bei 1. Vor dem Fix meldete der Kalender bei einem Suchhorizont von 3 den Zeitpunkt 1,5. Die stets positive Variante `[3*u, -3*u, u]` hat keinen Meldetermin.

```bash
cd rechenlabor/qss_pruefung
PYTHONPATH=quellen:programme python -m unittest -v test_qss_calendar_regressions
```

Die 82 ergänzenden Vertragsproben ergeben dieselbe Ergebnistabelle vor und nach dem Skalierungsfix. Für C03, C05, C12, C13 und C21 stimmen in den zwölf direkten Gegenläufen Status, numerischer Score sowie die aufgezeichneten Schritt- und RHS-Zähler überein. Die Laufzeiten stehen separat im jeweiligen Protokoll.

# Rechenlabor zur Gesamtausgabe v9.19

**QSS3/4-Nachtrag:** Der [Vorher-Nachher-Vergleich](rechenlabor/qss_pruefung/messung/taylor_kontakt/README.md) enthält die neu gemessenen 120 Konfigurationen. Die ursprünglichen Tabellen und Vollgitterberichte gehören weiterhin zum publizierten Messstand v9.19. Zum Nachrechnen des alten Stands den dort genannten Git-Commit auschecken.

Die vier Primärdateien und der zeilenweise Vergleich mit `c635504` liegen in [kontakt_v919](rechenlabor/qss_pruefung/messung/kontakt_v919). Für alle 19 nativen Verfahren sind Mechanismus, Verfahrenseinstieg, zugehörige Abbildung und analytische Proben im [Methodenregister](rechenlabor/qss_pruefung/messung/kontakt_v919/methodenregister.csv) aufgeführt. Für die logarithmischen und gruppierten Varianten gibt es eigene Zeilen. Die beiden CSV-Anlagen `qss-extension.csv` und `rk23-devs.csv` in der PDF gehören zum aktuellen Messstand. Anlagen mit Präfix `Archiv_` und die Übungen im Wurzelverzeichnis des kompakten Bachelor-Labors dokumentieren frühere Ausgaben.


## Das vollständige Labor öffnen

Beim GitHub-Actions-Lauf **Studienbuch** entsteht die Datei `ARGESIM_Rechenlabor_v9_19.zip` mit allen Quelltexten, Modellgewichten, Feldmessungen und Druckvorlagen. Sie lässt sich auch aus einem Checkout der veröffentlichten Revision mit der Python-Standardbibliothek erzeugen.

```bash
python scripts/build_studienbuch.py --check
python scripts/build_studienbuch.py --full-lab ARGESIM_Rechenlabor_v9_19.zip
python -m zipfile -e ARGESIM_Rechenlabor_v9_19.zip labor
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

Im historischen Skalierungsvergleich ergeben die 82 ergänzenden Vertragsproben dieselbe Ergebnistabelle vor und nach dem Skalierungsfix. Für C03, C05, C12, C13 und C21 stimmen in den zwölf direkten Gegenläufen Status, numerischer Score sowie die aufgezeichneten Schritt- und RHS-Zähler überein. Die Laufzeiten stehen separat im jeweiligen Protokoll.

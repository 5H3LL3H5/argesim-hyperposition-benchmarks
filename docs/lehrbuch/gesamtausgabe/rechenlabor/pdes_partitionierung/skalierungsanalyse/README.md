# CP2-Skalierung nachrechnen

Die vier Tafeln in Kapitel 16 entstehen aus den archivierten Originalzeiten. D2Q9-MPI erreicht auf 257 × 257 Knoten Takt 350 000. Die komponentenweisen QSS3- und QSS4-Reihen umfassen acht Ereignisintervalle. C19R läuft über zehn Modelltage, die parallele Saite über vier Modellsekunden. Jede Reihe hat ihre eigene serielle Bezugszeit.

## Reproduktion

Im Verzeichnis dieser Anleitung mit Python 3.12 ausführen. Die Bibliotheksversionen sind festgehalten. Mit installierten Bibliotheken läuft die gesamte Auswertung offline.

```sh
python3 -m pip install -r requirements.txt
python3 auswerten.py --ausgabe /tmp/cp2-auswertung
diff -rq ergebnisse /tmp/cp2-auswertung/ergebnisse --exclude=CP2_Abbildungen.pdf
```

Im Zielverzeichnis enthält `abbildungen/` je eine SVG-, PDF- und 300-dpi-PNG-Fassung der vier Drucktafeln. In `ergebnisse/` steht zusätzlich der vierseitige Bildatlas `CP2_Abbildungen.pdf`. Die Originale der vier Messarchive und `vollgitter.json` liegen im übergeordneten Verzeichnis. Das Verzeichnis `historisch/` enthält die kleinen Intel-Einzelprotokolle. Quellen sind auf den untersuchten Buchstand und die Archivmitglieder zurückgeführt. [Quellstand und SHA-256](quellstand.json).

| CSV unter `ergebnisse/` | Inhalt |
|---|---|
| `einzelzeiten.csv` | Zeit, Uhr, Arbeiterzahl, Wiederholung und Herkunft je Konfiguration. |
| `kennzahlen.csv` | Eigene Bezugszeit, Anzahl, Median, Spannweite, Speedup, Effizienz, Wandmehrzeit, Arbeitersekunden und Karp–Flatt. |
| `diagnose_mpi.csv` | Rangkarte, gerichtete Paare, Halo-Nutzdaten, Prozesshülle und modellierter Speicherverkehr. |
| `diagnose_qss.csv` | Zeitreichweite, LP-Größen, logische CPUs, RHS-Aufrufe, Nachrichten und Poisson-Nutzlast. |
| `diagnose_pdes.csv` | Ereignisse, Freigaben, Wiederherstellungen und verworfene Arbeit. |
| `openmp_messpaare.csv` | Historische Ein-/Vier-Thread-Paare und kontrollierte Last. |
| `openmp_affinitaet.csv` | Unabhängige 1 024-Takt-Gegenprobe mit logischer CPU-Maske und Wartepolitik. |

Für die Skalierungskurven gilt `median(T1) / median(Tp)`. Die Spannen benutzen einen festen Ein-Arbeiter-Median. Beim OpenMP-Lastversuch wird jedes Laufpaar zuerst dividiert, anschließend wird der Median der fünf Quotienten gebildet. Bei einem Arbeiter bleibt Karp–Flatt leer. Bei superlinearem Speedup bleiben negative Faktoren erhalten. Die einzelnen D2Q9-MPI-Vollzeiten erlauben keine Streuungsschätzung.

Die Hardwarebezeichnung, tatsächlich protokollierte Affinitäten und Grenzen der Zuordnung zu physischen Kernen sind [in Kapitel 16](../../../kapitel/16.md#cp2-skalierung-auswertung) dokumentiert.

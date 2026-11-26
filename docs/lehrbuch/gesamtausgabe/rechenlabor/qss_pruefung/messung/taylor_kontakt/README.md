# Nachtrag zu v9.19: Taylor-Kontakte in QSS3 und QSS4

Die Druckfassung und ihre 1.513 historischen Konfigurationen bleiben unverändert.
Dieser Nachtrag ergänzt die Wiederholung der **120 betroffenen QSS3/4-Konfigurationen**.
Er ersetzt weder die historischen Tabellen noch die veröffentlichten Vollgitter-Felder.

| Reihe | Schlüssel | Vergleichbare Fehlerwerte | Numerisch geändert |
|---|---:|---:|---:|
| Basismatrix | 42 | 37 | 37 |
| Erweiterung | 48 | 36 | 30 |
| Auswahl | 30 | 24 | 24 |

Die [Rohdaten und ihre Prüfsummen](vergleich.json) vergleichen den alten und den
korrigierten Solver auf demselben Host mit denselben Schlüsseln und Optionen.
Bei C13 bleiben die beiden auffälligsten Änderungen im selben Status: Der auf
die Toleranz normierte Fehler in der Erweiterung ändert sich bei QSS3 von
53,41168 auf 57,51708 und bei QSS4 von 49,13282 auf 43,15992. Beide bleiben damit
außerhalb der Toleranz. Die zwei Statuswechsel betreffen Zeitlimits bei C01-A;
sie belegen keine Geschwindigkeitsverbesserung. Die Messreihen liefen parallel.

Die Modellregression prüft beide Verfahren mit automatischer und fest
vorgegebener Stützweite. Einen Gleitkommaschritt unter der exakten Schwelle
wird eine Kreuzung erkannt. An der Schwelle wird die Berührung bei
\(t=3/2\) erkannt. Einen Schritt darüber tritt kein Ereignis auf.
Die Rechnung garantiert nicht, dass ein beliebiges gerundetes Modell
eine analytische Doppelwurzel bewahrt.

## Reproduktion

1. Für die historischen Buchwerte den gemergten Stand v9.19 bei
   `b962c7a4587bc0d919d849805bb1622c13ab9c7b` auschecken.
2. Für die gezielte Gegenprobe Kontroll- und Kandidatenrevision aus
   [vergleich.json](vergleich.json) getrennt auschecken. Die Basismatrix benötigt
   die Quellen aus `Laborquellen.zip/rechenlabor/qss_pruefung/quellen`; dort jeweils
   `argesim_benchmarks/solvers/advanced_qss.py` der angegebenen Revision einsetzen.
   Mit `PYTHONPATH` auf das jeweilige Projekt, `OPENBLAS_NUM_THREADS=1` und
   `OMP_NUM_THREADS=1` die [Basismatrix](baseline_runner.py) mit Quellen- und
   Ausgabeverzeichnis und `--workers 2` starten. Für Erweiterung und Auswahl
   [run_targeted.py](run_targeted.py) mit dem Ausgabeverzeichnis aufrufen.
3. Aus dem Kandidatenprojekt
   `python -m unittest discover -s tests -p test_qss_high_order_contacts.py`
   ausführen.

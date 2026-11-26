# QSS-Verfahrensprüfung zur Gesamtausgabe v9.18

## Welcher Code wurde geprüft?

Der Buchstand v9.17 enthält die nativen ARGESIM-Implementierungen in Python. Die identischen Ausgangsdateien für `_polynomial.py`, `qss.py` und `advanced_qss.py` sind unter `vorher/` archiviert. Die Korrektur steht in `quellen/argesim_benchmarks/solvers/`. In den nativen Klein- und Vollgitteradaptern und im Projektteil der Messplanung wurden dieselben drei Dateien ersetzt. Eine Änderung an der gemeinsamen Polynomroutine erreicht auch die Lokalisierung von Ereignissen im hybriden Treiber. Die Wiederholung verwendet deshalb auch die klassischen Kontrollrechnungen. Die D2Q9-Streaming-Kollision, der separate C++-Gruppenkalender, AB2 und die bereits trainierten Operatorgewichte besitzen andere Rechenpfade.

1. **QSS3/4 und weitere Benutzer der gemeinsamen Wurzelsuche.** Die Suche isoliert die früheste positive Wurzel zwischen den Extremstellen in physikalischer Zeit. Horner-Auswertung und der lokale Maßstab der einzelnen Terme entscheiden bei Berührung über das Residuum. Eine Wurzel im Startpunkt kann neben einer weiteren positiven Wurzel existieren. Die große Restzeit bis zur Endzeit darf die frühe Wurzel nicht auslöschen.
2. **QSS1 und CQSS1.** Zeitnähe allein konnte bei sehr schnellen Komponenten einen Zustand an eine entfernte Zellgrenze versetzen. Die Ereignisgruppe berücksichtigt jetzt zusätzlich den im Zeitabstand möglichen Zustandsweg und das Rundungsmaß am Zustand.
3. **QSS2.** Eine negative quadratische Wurzel dicht vor dem Segmentstart ließ sich zuvor als Nulltermin auswählen. Zulässig sind reelle Kandidaten im Vorwärtsintervall. Der Test mit konstanter Beschleunigung prüft die erste positive Zeit unabhängig von der späteren numerischen Differentiation.
4. **Taylorableitungen der Familie höherer Ordnung.** Bei konstantem, großem rechten Vektor ist jede höhere Ableitung null. Bei der Differenzenbildung wird zuerst der Wert im Zentrum abgezogen. Der konstante Koeffizient wird direkt übernommen. Das verhindert künstliche Krümmung in der analytischen Geraden.

## Rechenstand der Veröffentlichung

Die 1.513 Vergleichszeilen und ihre Laufzeiten stammen vom Kalenderstand `d656b6f`. Dessen Polynomroutine liegt in `vorher/PR82_d656b6f/_polynomial.py`. Für eine Wiederholung exakt dieses Messstands kann man sie in einer separaten Laborkopie anstelle von `quellen/argesim_benchmarks/solvers/_polynomial.py` verwenden. Die veröffentlichte Solverfassung `c635504` skaliert winzige Koeffizienten vor der Auswertung mit einer gemeinsamen Zweierpotenz. Die gezielten Tests enthalten ein subnormales Polynom mit zwei Nullstellen, eine stets positive Parabel und den GitHub-Gegenfall mit der ersten Nullstelle bei rund 1e100. Bei gemischten Exponenten kann ein Koeffizient nach der Skalierung subnormal bleiben. In diesem Fall wertet der Solver die Vorzeichen als exakte dyadische Brüche aus. Die zugehörigen Gegenläufe sind separat unter `messung/gegenlauf_skalenfix.jsonl` dokumentiert.

### Vollständiger Gegenlauf auf dem überprüften Solver

Die vier Originalprotokolle wurden mit denselben Verfahren, Fallfenstern, Quanten, Wiederholungszahlen und Zeitlimits auf `c635504` erneut ausgeführt. Die Basismatrix umfasst 399 Einstellungen, die Erweiterung 456, die Auswahlstudie 520 und die RK23-Reihe 138. Unter den 1.513 Einstellungen liegen alle 120 QSS3/4-Konfigurationen der vier Reihen. Die CSV verknüpft beide Stände über Reihe, Fall, Verfahren und Einstellung. [Gepaarte Ergebnisse](messung/skalenfix_c635504/skalenvergleich.csv) · [Anzahlen und SHA-256-Werte der Quelldateien](messung/skalenfix_c635504/skalenvergleich.json)

Bei 1.378 Einstellungen blieb der Status gleich. Für 1.176 Paare liegt beidseitig ein numerischer Fehlerwert vor. Alle 1.176 Werte und alle beidseitig protokollierten Arbeitszähler stimmen überein. Die 135 Statuswechsel betreffen frühere Zeitüberschreitungen. Der neue Lauf meldet für 68 dieser Einstellungen einen bestandenen Versuch, für 43 eine verfehlte Genauigkeit, für 14 einen Solverfehler und für zehn eine abweichende Ereignisfolge. Bei QSS3/4 sind alle 92 beidseitig vorhandenen Fehlerwerte gleich, fünf Konfigurationen wechseln aus dem Zeitlimit. Die Zeitlimits messen die verstrichene Zeit und reagieren auf die Rechnerlast.

## Primärbelege und Wiederholung

Die Skripte verwenden Python, NumPy und SciPy. Matplotlib wird für Abbildungen benötigt. Der vollständige CP2-Lauf benötigt außerdem den im Kavitätenlabor angegebenen C++20-Compiler und für die Vollgitter-Poissongleichung FFTW. Die Umgebungsangaben in den JSON-Dateien beschreiben den vermessenen Rechner. Die ausgewiesenen Medianzeiten sind bei gleichzeitig laufenden Aufträgen entstanden. Vergleiche der schnellsten Konfiguration sind vom Zeitlimit und der Rechnerlast abhängig.

Vom hier entpackten Verzeichnis aus können die jeweiligen Reihen wie folgt gestartet werden. Die Originaleingaben und Quanten einschließlich der klassischen Kontrollen sind in den Studienprogrammen bzw. im Index festgelegt.

```bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTHONPATH="$PWD/quellen:$PWD/quellen/tests:$PWD/programme"
python -m unittest test_advanced_qss test_backward_and_log_qss test_hybrid_runtime test_mixed_qss test_qss_devs_trace test_qss_solver test_root_solver test_runtime test_solver_selection test_convergence test_cifasis_oracle test_qss_calendar_regressions
lauf="$PWD/mein_lauf"
mkdir -p "$lauf"
python programme/vertrag.py quellen "$lauf/vertragsproben.csv" > "$lauf/vertragsproben.json"
python programme/regression.py ../kavitaet_vollgitter > "$lauf/nullstellen.json"
python programme/baseline.py quellen "$lauf" --workers 6
python quellen/benchmarks/benchmark_solver_extension.py --output "$lauf/extension.csv" --repeat 3 --timeout 2
python quellen/benchmarks/benchmark_solver_selection.py --profile selection --output "$lauf/selection.csv" --repeat 3 --timeout 2
python quellen/benchmarks/benchmark_solver_selection.py --profile rk23 --output "$lauf/rk23.csv" --repeat 3 --timeout 2
python programme/gegenlauf.py v917 --output "$lauf/gegenlauf_v917.jsonl"
python programme/gegenlauf.py v918 --output "$lauf/gegenlauf_skalenfix.jsonl"
python programme/skalenvergleich.py --repeat-dir "$lauf"
```

`messung/revisionsvergleich.csv` verbindet alle 1 513 Konfigurationen über Fall, Verfahrensnamen und Einstellung. Die Basisreihe besitzt ein anderes Fallkollektiv und eigene Fehlergrößen. Die 520er-Reihe enthält acht C-Fenster sowie fünf weitere Testsysteme. Die acht Entscheidungen in Kapitel 18 verwenden ausschließlich die acht C-Fenster und deren 17 gemeinsame Einstellungen. Der erweiterte C05-Versuch und die vier QSS3/4-Vergleichsfälle mit 45 s je Integration sind als gesonderte Läufe mit einem Einmesslauf und einer Zeitmessung gekennzeichnet.

`messung/vertragsproben*.csv` enthalten 82 zusätzliche Aufrufe pro Solverstand. Geprüft wurden konstante Lösungen, gleichförmige Bewegung, zwei Quanten am gekoppelten gedämpften Oszillator und gezielte Grenzfälle. `messung/nullstellen.json` dokumentiert außerdem 25 fest vorgegebene, 400 aus bekannten Faktoren generierte Polynomfälle, die zusätzliche Startwurzelprobe und acht Integrationen. Eine bestandene Probe ist Evidenz für den geprüften Eingang. Insbesondere ersetzt sie keinen allgemeinen Nachweis der Stabilität oder Ordnung einer Implementierung.

`programme/kleinserie.py KLEINLABOR quellen/kleinserie.json` wiederholt alle Kleinserieneinstellungen im separaten Kavitätenlabor. Die Skripte `quantisierer.py`, `erweiterte_grenzen.py`, `kontrollfelder.py` und `zeiten.py` dort wiederholen die zusätzlichen Fall- und Zeitreihen. Nach `auswerten.py` und `pruefen.py` stehen die aus den gespeicherten Feldern neu berechneten Fehler bereit. `programme/kavitaet_neu.py ../kavitaet_vollgitter ROHDATEN LOGVERZEICHNIS --workers 9` erfasst die 19 Einzelkalender, 19 Galerkinläufe, 19 dynamischen Korrekturen und vier Verschiebungen des CQSS1-Rasters. Die Rohdaten lassen sich mit dem Wiederholungsskript des Vollgitterlabors erzeugen. Mit `segmentpruefung.py` und `gittertakte.py` lassen sich die tatsächlich abgeschlossenen QSS3/4-Segmente und die ersten vier Gittertakte separat auswerten.

Die fünf Vektorgrafiken in Kapitel 6 sind eigene Ableitungen aus den angegebenen Formeln und protokollierten Solverläufen. `programme/methodenbilder.py` erzeugt beide Druckformate und die Kurvendaten. QSS4 und mLIQSS3 bezeichnen die jeweiligen Projektausführungen. Die externen CIFASIS-Spuren sind archivierte Vergleichsdaten. Im Rahmen dieser Wiederholung wurde kein externer CIFASIS-Solver installiert und neu gestartet.

Die Originalarbeiten zu [QSS3](https://usuarios.fceia.unr.edu.ar/~kofman/files/lsd0502.pdf), [CQSS/BQSS](https://doi.org/10.1177/0037549711403645), [mLIQSS](https://doi.org/10.1177/0037549718766689) und [verallgemeinerten LIQSS-Familien](https://doi.org/10.1007/s40314-026-03858-3) dokumentieren die Verfahrensideen. Die Abbildungen 1 und 2 der Arbeit zu CQSS/BQSS zeigen am selben Beispiel die beiden Meldesignale und ihre stark unterschiedlichen Zeitskalen. Abbildungen 6.3–6.7 im Buch beziehen sich durchgehend auf die dort angegebenen Lehrmodelle.

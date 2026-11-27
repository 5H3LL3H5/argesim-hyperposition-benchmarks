# Physikalisches Vorwissen in neuronalen Operatoren

Rechenlabor zu Abschnitt 9.44 im Anschluss an den Vergleich in Abschnitt 9.43 in *Numerische Simulation dynamischer Systeme*. Die Ausgangsfelder, ursprünglichen Netzarchitekturen und Archivwerte stammen aus dem Merge-Commit `72d670b51c94c8366ca5f1e070fc4730c78d0d52`. Zum Ausführen genügt dieses entpackte Verzeichnis. [ARGESIM-PR 91](https://github.com/5H3LL3H5/argesim-hyperposition-benchmarks/pull/91)

**Lesen.** `chapter/Kapitel9.pdf` enthält die mathematische Herleitung, Tabellen, Lernkurven und drei Aufgaben mit Lösungen. `chapter/Kapitel9.md` ist die inhaltlich identische, editierbare Fassung. `results/` enthält die selbst erhobenen Messungen. `reference/messung_kapazitaet.json` enthält ausschließlich die historischen Werte.

**Wie lange dauert es insgesamt?** Die vollständige Wiederholung der Ausgangsstudie dauerte 12 min 39,33 s. Die Vergleichsmessungen mit den beiden Lattice-Boltzmann-Verfahren dauerten zusätzlich 3 min 18,47 s. Die Summe der beiden gemessenen Versuchsblöcke beträgt 15 min 57,81 s. Auf den Seiten 7–11 stehen die Zeiten einschließlich Prozessstart und Training sowie die Zeiten mit vorhandenen Gewichten. Die Diffusionsmessung umfasst 32 Aufträge auf 25 × 25 Knoten. Die Kavitätsmessung umfasst 24 Aufträge auf 17 × 17 bei 16 Takten. Die vier archivierten MPI-Gesamtzeiten für einen einzelnen 257er-Kavitätslauf bis Takt 350 000 stehen auf Seite 11. [Messgrenzen, Programmaufrufe und Primärquellen](runtime_benchmark/SOURCES.md) · [Alle 16 direkten Verfahrensvergleiche](results/runtime/total_jobs.csv)

## Schnell nachrechnen

Linux x86-64 und CPython 3.12 waren die Messumgebung. Im Paket liegen alle 42 trainierten Netzzustände. Nach Installation der Abhängigkeiten funktionieren Datenerzeugung, Training, Test und Auswertung offline. Ein vollständiger Durchlauf braucht keine Anmeldung bei einem Modell- oder Datendienst.

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --index-url https://download.pytorch.org/whl/cpu 'torch==2.8.0+cpu'
python -m pip install -r requirements-cpu.lock
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
python -m unittest -v
```

Die Kernrechnung für die 24 Parameter lässt sich mit NumPy und SciPy allein ausführen.

```python
from physics import Modal, fixed_split, score

train = fixed_split(96, 42201, 13)
model = Modal.fit(*train)
x_test, y_test = fixed_split(32, 42203, 25)
print(score(model.predict(x_test), y_test))
# u ≈ 2.5510e-8, v ≈ 2.5262e-8, boundary = 0
```

| Ziel | Aufruf im entpackten Verzeichnis |
|---|---|
| Direkte Fits und Physikkontrollen wiederholen | `python evaluate.py --part structured --output repeat-structured` |
| Alle gespeicherten Netze erneut auf zwölf Szenarien auswerten | `python evaluate.py --part neural --weights results/weights --output repeat-neural` |
| Zwei beispielhafte Trainingsepochen | `python neural.py --models FNO-small Strang-FNO --cases n8 --epochs 2 --output smoke-weights` |
| Vollständiges Training mit allen Seeds und erneute Auswertung | `./reproduce.sh repeat` |
| Tabellen, Grafiken und PDF aus dem vollständigen neuen Lauf erzeugen | `python report.py --results repeat` |
| Laufzeiten aller 16 Modell- und LBM-Vergleiche neu messen | `python -m runtime_benchmark.measure --out repeat/runtime` |

`reproduce.sh` schreibt in den gewählten Ausgabeordner. `report.py` erstellt die lesbare Fassung in `chapter/` und benötigt zusätzlich Pandoc mit Typst-Writer. Verwendet wurden Pandoc 3.1.11.1, das Python-Paket typst 0.15.2 und die Schriftfamilie Noto Sans/Serif. `python report.py --no-pdf` erzeugt Manuskript und Abbildungen auch ohne Pandoc. Die Grafiken sind datengetrieben. Der Kapiteltext enthält darüber hinaus die Interpretation und benannte Einzelbefunde des ausgelieferten Referenzlaufs.

Der Laufzeitvergleich und seine Regressionstests verwenden zusätzlich einen C++17-Compiler. Für eigene Kapitelwerte benötigt der Ordner `repeat/runtime` sowohl die Messung der Ausgangsstudie als auch die LBM-Messdateien. Ist dort kein Laufzeitordner vorhanden, verwendet der Renderer die mitgelieferten Laufzeitmessungen. Mit `--runtime-results` lässt sich ein vollständig gemessener Ordner ausdrücklich wählen.

## Welches Modell erhält welche Information?

| Name in den CSV-Dateien | Fit und Verhalten bei der Vorhersage |
|---|---|
| `FNO-small`, `UNO`, `CoDA-NO` | Modellbau und Randprojektion aus `reference/austausch.py`, FNO und UNO mit 1 034, CoDA-NO mit 1 051 reellen Gewichten. Die Eingabe enthält die zwei Anfangsfelder. Komplexe Gewichte zählen doppelt. |
| `Modal24` | Sechs Sinusanalysen und sechs unabhängige Ausgleichsprobleme mit je vier reellen Parametern. Die Materialdaten oder Referenzblöcke gehen nicht in den Fit ein. |
| `Generator3` | Schätzt zwei Diffusivitäten und die Austauschrate bei bekannter Trainingszeit mit beschränkter nichtlinearer Kleinste-Quadrate-Anpassung. Bei der Inferenz wird nur der angefragte Zeithorizont übernommen. Das Ziel entsteht per Eigenzerlegung, der gefittete Generator nutzt eine separate geschlossene Formel. |
| `Strang` / `Strang-fixed` | Ein vollständiger Strang-Schritt mit diskreter Sinustransformation auf allen aufgelösten Frequenzen. Die erste Kontrolle verwendet die Testparameter, die zweite hält alle vier Größen auf Nominalwerten. |
| `Strang-R24` | Strang-Schritt mit 24 aus den nominalen Trainingsresiduen geschätzten Koeffizienten. Die Korrektur wird bei Parameterwechsel unverändert angewandt. Auf fremden reinen Moden greift nur der Strang-Schritt. |
| `Strang-FNO` | Strang-Schritt und additiver FNO-Rest mit 1 034 trainierbaren reellen Gewichten. Die Rückskalierung nutzt zusätzlich einen aus den Trainingszielen berechneten RMS-Skalar. |
| `FNO-cond`, `Strang-FNO-cond` | Parameterfamilie mit je 1 050 trainierbaren Gewichten. Beide Netze erhalten dieselben vier zusätzlichen Kanäle. Der Hybrid berechnet zusätzlich den Strang-Schritt mit den gegebenen Werten. |

Die konditionierten Netze erhalten vier dimensionslose Parameterkanäle, je multipliziert mit dem räumlichen Profil der ersten Sinusmode. Ihr Training enthält 96 unterschiedliche Tupel. Die Parameter-Seeds 52201, 52202 und 52203 sind von den Koeffizienten-Seeds getrennt. Die Grenzen der vier Gleichverteilungen stehen im Kapitel und in `physics.family`.

## Versuchsplan und Dateiinhalte

| Experiment | Datensatz und Budget |
|---|---|
| Nominalvergleich `n96` | 96/24/32 Feldpaare, Anfangsamplituden-Seeds 42201/42202/42203. Je 40 Epochen und drei Initialisierungen 2027, 73 und 3917 für alle drei Originalnetze und Strang + FNO. Der Originalvergleich im Archiv enthält neun Netztrainings. |
| Datenbudget `n2`, `n8`, `n24` | Geschachtelte Trainingsmengen, ein Netzstart 2027, 40 Epochen, Adam mit Lernrate 0,003, höchstens 16 Beispiele je Batch. Validierungs- und Testdaten sind bei allen Budgets identisch. |
| Gleiche Schrittzahl `n8_steps` | Acht Felder, 240 Epochen zu je einem Update, Seed 2027. Der Nominalvergleich mit 96 Feldern führt ebenfalls 240 Updates aus. |
| Zielrauschen `noise5` | Alle vier Netze werden mit 5 % weißem Pixelrauschen erneut trainiert. Training und Netzstart sind mit `n96` (Seed 2027) gepaart. Saubere Validierung und Prüfung. |
| Direkte Fits | Zwölf Kombinationen aus Datenmenge und Rauschtyp/-stärke, jeweils drei Trainingsziehungen. Pixelrauschen und vollständig in sechs Moden liegendes Gaußrauschen haben je Kanal dieselbe erwartete innere RMS-Skalierung. Der Seed für die Störung ist der jeweilige Trainingsseed plus drei. |
| Eingangsrauschen `input5` | 5 % weißes Pixelrauschen nur auf den Anfangsfeldern des Trainings. Alle vier Netze werden mit Seed 2027 erneut trainiert. Für die direkten Fits wird zusätzlich modales Eingangsrauschen geprüft. |
| Parameterfamilie `family` | 96/24/32 gepaarte Felder und Parametersätze, drei Initialisierungen, zwei konditionierte Netze. |

Die zwölf Testfälle heißen `nominal`, `nominal13`, `pure_new`, `mixed_new`, `diff_swap`, `k_low`, `k_high`, `k_zero`, `t_short`, `t_long`, `t_zero` und `family_test`. Alle außer `nominal13` verwenden 25 × 25 Knoten. Im reinen neuen Modentest regt die Kopplungsprobe die erste neue Mode (3,2) an. Die übrigen Einzelparameterfälle verwenden (1,1). Für `family_test` wird keine gemeinsame Kopplungsprobe ausgewiesen, da dort jedes Beispiel andere Parameter hat.

| Datei | Einheiten oder Inhalt |
|---|---|
| `results/neural.csv`, `results/structured.csv` | Eine Zeile je Fit, Seed und Testszenario. `u`, `v` und `response` sind **dimensionslose Verhältnisse**. Im Kapitel stehen Prozentwerte. `response_abs_l2` ist die unnormierte diskrete Norm des Fehlers der Kopplungsantwort. `boundary` ist der größte absolute vorhergesagte Randwert. |
| `results/*_samples.csv` | Jeweils 32 individuelle relative Fehler pro Modell, Seed, Trainingsfall und Szenario. `sample` ist der innerhalb des jeweiligen Tests gepaarte Index. |
| `results/paired_intervals.csv` | Paarweise Differenz der mittleren Kanalfehler in Prozentpunkten. 10 000 Bootstrapziehungen der 32 Testfelder nach Mittelung über die drei Netzinitialisierungen. Positive Werte bedeuten einen Vorteil für den Kandidaten. |
| `results/blocks.json` und `results/generator_fits.csv` | Alle gelernten Blöcke und separat die drei geschätzten Materialwerte. `relative` in `blocks.json` ist der skalare relative Fehler des Eintrags (u,v) der ersten Mode. |
| `results/weights/` | Pro Netzlauf ein Tensor-Checkpoint und ein JSON mit Parameterzahl, Updatezahl, gewählter Epoche, Lernzeit, kleinstem Validierungs-MSE und Residualskala. Laden über `Network` mit `weights_only=True`. |
| `reference/nominale_felder.npz` | Vollständige nominale Ein- und Ausgabefelder, Float32. Schlüssel `train_x/y`, `validation_x/y`, `test13_x/y` und `test25_x/y`, jeweils als getrennte Arrays mit Suffix `_x` oder `_y`. |
| `results/environment.json`, `requirements-cpu.lock` | Messumgebung, Threadkonfiguration und genaue Paketversionen. `SHA256SUMS` deckt die ausgelieferten Dateien ab. |

`train_s` bezeichnet Sekunden für den Fit einschließlich Validierung, soweit das Modell sie nutzt. Datenherstellung, Modellkonstruktion, Optimizerkonstruktion und Dateispeicherung sind ausgenommen. `latency_ms` ist pro Modell und Seed ein eigener Warmmesswert bei Batchgröße eins auf dem nominalen 25er-Gitter. Derselbe Wert erscheint in allen Szenariozeilen dieses Fits. Gezählt werden drei Aufwärmaufrufe und der Median von 21 anschließenden Aufrufen einschließlich Randbehandlung, Fourier-/Sinustransformationen und ggf. Parameterkodierung. Er ist keine Latenzmessung für wechselnde Koeffizienten oder einen Kaltstart.

**Numerische Reproduktion.** Die Tests prüfen Rangverlust, Gittertransfer, Entkopplung, Energie und Halbgruppeneigenschaft des Referenzproblems, Splittingordnung, Rauschprotokoll, unveränderte Quelldateien und die veröffentlichte Gegenrechnung. Ein separater DOP853-Lauf und eine Padé-Matrixexponentialfunktion kontrollieren die Referenzwerte. Das Labor prüft darüber hinaus Parameterzahlen, Randbedingungen und gespeicherte Modellzustände. Die zeitlichen Messungen hängen von CPU, Softwarestand und Auslastung ab.

Die beiden Druckabbildungen entstehen zusätzlich mit `python report.py --vector-dir druckbilder` als SVG und PDF.

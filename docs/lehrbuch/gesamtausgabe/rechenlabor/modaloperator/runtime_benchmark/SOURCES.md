# Gesamtlaufzeiten und Lattice-Boltzmann-Vergleiche

## Welche Frage beantwortet welche Uhr?

| Datei unter `results/runtime/` | Messgrenze |
|---|---|
| `original_total.json`, `replication.log` | Äußere Stoppuhr für die vollständige Ausgangsstudie mit ihren ursprünglichen Tests, 42 neu trainierten Netzen, Auswertung und ursprünglichem Kapitel. Unterzeiten für Rechenlabor und Buchsatz. |
| `total_jobs.csv` | 16 Vergleiche. Zeilen sind Verfahren innerhalb derselben Aufgabe. Sekunden pro **gesamtem** Auftragspaket einschließlich Kaltstart bzw. Millisekunden pro warmem Feldpaar sind separat benannt. |
| `timings.json` | Neun rohe warme Blockzeiten je Vergleich, die Kaltstartphasen, C++-Compiler und Optionen, gemeinsame Übersetzungszeit und äußere Dauer des gesamten Zusatzversuchs. |
| `lbm_refinement.csv` | D2Q5-Fehler gegen die analytische Lösung bei vier Gitterweiten und acht identischen Ausgangsfeldpaaren. |
| `break_even.csv` | Aus gemessenen Zeiten errechnete Stückzahlschwellen für einen dauerhaft laufenden Prozess. |

**Eingaben und Vergleichsmaß.** Bei der Diffusion sind es 32 getrennte Aufträge für zwei Temperaturfelder auf 25 × 25 Knoten. Sie verwenden dieselben Float32-Anfangsfelder, die im Ausgangsversuch aus sechs Sinusmoden erzeugt wurden. Der D2Q5-Kern rechnet in Float64. Im Nominalfall sind die Parameter für alle Aufträge gleich. Für `family` kennt jedes Verfahren den jeweiligen Parametersatz. Die analytische Referenz wird im äußeren Prozess ausgewertet. Beim kleinen Kavitätsversuch sind es 24 Dichtefelder, 17 × 17 und jeweils exakt 16 Takte bei Re = 1000. Die Metrik ist hier der mittlere relative Vektorfehler der beiden Geschwindigkeitskomponenten im Inneren gegen die ursprüngliche D2Q9-Implementierung. Bei der Diffusion wird der relative Fehler zunächst pro Feld und Kanal bestimmt und danach arithmetisch gemittelt.

**Kaltstart.** Für jedes Verfahren startet der Treiber einen eigenen neuen Python-Prozess. `fresh1_s` reicht vom Start bis zum ersten Ergebnis im Speicher, `freshN_s` bis zum Ende des Prozesses nach allen Aufträgen, Dateiausgabe und Ausführung des Shutdown-Codes. Beide enthalten bei lernenden Verfahren die Erzeugung der Trainings- und gegebenenfalls Validierungsdaten, Anpassung, Speichern und Laden des Modells. `ready1_s` und `readyN_s` verwenden einen separaten frischen Prozess mit vorhandenem Modell. Für die Netze stammen die fertigen Gewichte aus der veröffentlichten bzw. mitgelieferten Studie, für die drei strukturierten Fits aus dem frisch gefitteten Zustand. Für Verfahren ohne Fit führen beide Prozesse denselben Algorithmus aus. Die LBM-Kerne sind beim Start der Prozesse bereits übersetzt. `build_s` beziffert die einmaligen gemeinsamen Baukosten. Die Zeiten schließen die Importe des jeweiligen Python-Einstiegs ein. Eingabedateien sind vorhanden. Installation, Validierung der **Test**ergebnisse und Nachbearbeitung des Kapitels liegen außerhalb der einzelnen Anwendungsaufträge.

**Warmmessung.** Ein dritter Prozess lädt das Modell bzw. die native Bibliothek, durchläuft zweimal das vollständige Auftragsbündel und dann neun gemessene Blöcke. Je Block werden die 32 bzw. 24 Aufträge nacheinander mit Batchgröße eins abgearbeitet. `warmN_s` ist der Median der neun gesamten Blöcke. `warm_ms_each` ist dieser Median, geteilt durch die Auftragsanzahl und in Millisekunden. Die vorgewärmten Eingaben und das ausgegebene Gesamtarray liegen im Arbeitsspeicher. Die beiden Kaltzeiten je Methode sind einzelne Messungen. Die Float32-Ausgabe der NumPy-Kavitätsreferenz erklärt Rundungsabstände des nativen Float64-Kerns.

**Amortisation.** `fresh_fixed_s` ist die Zeit vom Start bis unmittelbar vor dem ersten Vorwärtsaufruf. `fresh_prepare_s` beginnt erst nach dem Laden der Testeingaben und der Erzeugung der Parameterobjekte. Die erstgenannte Größe geht als A in das Modell T(N) = A + Nℓ ein. Aus der positiven marginalen Einsparung ℓ(LBM) − ℓ(Kandidat) folgt die kleinste ganze Auftragszahl mit strikt kleinerer modellierter Gesamtdauer. Es handelt sich um eine Extrapolation für einen kontinuierlich laufenden Prozess. Die leere Spalte kennzeichnet eine nichtpositive marginale Ersparnis.

## Experiment wiederholen

Alle Befehle sind aus dem entpackten Verzeichnis `ARGESIM_Operatorenlabor` auszuführen. Erforderlich sind die in der obersten README beschriebenen Python-Pakete sowie ein C++17-Compiler mit GCC-kompatiblen Optionen. Zum erneuten Setzen des PDF werden Pandoc mit Typst-Writer und Typst benötigt.

~~~sh
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
python -m unittest -v
mkdir -p repeat/runtime
unzip -oq runtime_benchmark/archived/study_before_runtime.zip -d repeat/source
python -m runtime_benchmark.time_original \
  repeat/source/ARGESIM_Operatorenlabor repeat/runtime/original_total.json
python -m runtime_benchmark.measure --work repeat/runtime-work --out repeat/runtime
python report.py --results repeat/source/ARGESIM_Operatorenlabor/repeat-clock --runtime-results repeat/runtime
~~~

`time_original` schreibt die äußere Stoppuhr und die Unterprozessprotokolle nach `repeat/runtime/`. Die Programmsourcen, Referenzeingaben und publizierten Gewichte werden vor Beginn der Messung mit dem mitgelieferten Ausgangsarchiv abgeglichen. `measure` übersetzt beide nativen Kerne einmal und verwendet 48 getrennte Prozesse für 16 Verfahrensvergleiche. Das Arbeitsverzeichnis enthält die Testeingaben, neu angepasste Gewichte, Einzelausgaben und Unterprozessprotokolle. Ohne `--work` wird dieses Verzeichnis temporär angelegt. Für die schnelle Darstellung des mitgelieferten Standes genügt `python report.py`.

Die Vollgitter-MPI-Messungen auf 257 × 257 Knoten werden aus den Originalprotokollen übernommen. Der oben beschriebene Ablauf misst die beiden kleineren Direktvergleiche und die Ausgangsstudie auf dem eigenen Rechner. Die neuen Einprozesszeiten auf Intel Xeon und die archivierten MPI-Zeiten auf AMD EPYC haben unterschiedliche Hardware und Arbeitslasten.

## Quellen und Präzisionsvertrag

- Ausgangsstudie zu den zwei Diffusionsfeldern am Merge-Commit `72d670b51c94c8366ca5f1e070fc4730c78d0d52`. [PR 91](https://github.com/5H3LL3H5/argesim-hyperposition-benchmarks/pull/91)
- Die D2Q5-Implementierung für zwei getrennte Diffusionskoeffizienten mit symmetrischer Austauschreaktion, Odd-Extension am festen Rand und Gitterstudie ist im vorliegenden Paket enthalten. Die Grundformel für den D2Q5-Diffusionskoeffizienten und eine Anwendung der Reaktionsaufspaltung sind beschrieben in *Lattice Boltzmann method for simulation of diffusion magnetic resonance imaging physics in multiphase tissue models*. [Physical Review E 102, 043305](https://doi.org/10.1103/PhysRevE.102.043305)
- `cp2_reference.py` enthält die für den Versuch erforderliche Dichteerzeugung, CP2-Randbehandlung, D2Q9-Referenz und affine Anpassung. `cp2_network.py` enthält die Architektur und das Training des vektorwertigen Residual-FNO. Das Archiv `cavity-checkpoint.npz` ist der veröffentlichte Modellzustand, Git-Blob-SHA1 `2cc0cef8ef92c0a0409acbedb5bf39f7aa7b39b8`. Sein Vertrag lautet 17 × 17 Knoten, 16 Takte, beide Geschwindigkeitskomponenten. `cavity_accuracy.json` enthält die Referenz des Residualversuchs, `cp2-operators.json` auch einen früheren Versuch mit einer anderen Zielgröße. [CP2-Genauigkeitsstudie](https://github.com/5H3LL3H5/argesim-hyperposition-benchmarks/blob/72d670b51c94c8366ca5f1e070fc4730c78d0d52/argesim_benchmarks/experiments/cp2_accuracy.py) · [Residual-FNO](https://github.com/5H3LL3H5/argesim-hyperposition-benchmarks/blob/72d670b51c94c8366ca5f1e070fc4730c78d0d52/argesim_benchmarks/experiments/cp2_residual_fno.py) · [Gespeicherter Zustand](https://github.com/5H3LL3H5/argesim-hyperposition-benchmarks/blob/72d670b51c94c8366ca5f1e070fc4730c78d0d52/docs/lehrbuch/studienbuch/material/cp2_genauigkeit/kavitaet.npz)
- Der native D2Q9-Kern übernimmt die CP2-Kollision und die publizierten Gitterrandregeln. Sein erster Kollisionsschritt verarbeitet das tatsächliche variable Dichtefeld vor dem ersten Streaming. Regressionstests vergleichen beide Geschwindigkeitskomponenten mit der unabhängigen NumPy-Fassung. Das zusätzliche parametrisierte FNO prüft die Gitter- und Zeitschranken beim Anwenden. [C++-Referenzkern](https://github.com/5H3LL3H5/argesim-hyperposition-benchmarks/blob/72d670b51c94c8366ca5f1e070fc4730c78d0d52/scripts/cp2_accuracy/cavity_reference.cpp) · [Parametrisiertes FNO](https://github.com/5H3LL3H5/argesim-hyperposition-benchmarks/blob/72d670b51c94c8366ca5f1e070fc4730c78d0d52/argesim_benchmarks/experiments/cp2_parameter_fno.py)
- `archived/full-mpi-{1,2,4,8}.json` und `full-platform.json` sind bytegenaue Kopien von `mpi/log-{1,2,4,8}.json` und `platform.json` aus `messarchive/Skalierung_Messdaten.zip` des Quellenpakets zu Kapitel 16. SHA-256 des äußeren Quellenpakets `bb1c6eb0b91a1d2411d5c05f0e1b02073f13caa65d7c861ac00de2dfe1788d3a`. Messstand `5e73ade08e753223c59619118f23d24036bdc029`. [Originalmessungen zur PDES-Partitionierung](https://github.com/5H3LL3H5/argesim-hyperposition-benchmarks/tree/5e73ade08e753223c59619118f23d24036bdc029/docs/lehrbuch/gesamtausgabe/rechenlabor/pdes_partitionierung)


- Die gespeicherte Methodenmatrix dokumentiert sieben Vollgitterzeitpunkte, CPU-Zeit und maximalen lokalen Geschwindigkeitsfehler relativ zur Deckelgeschwindigkeit. Der SHA-256-Wert von `archived/vollgitter_methoden.csv` lautet `fdef23139f9475eff33faf42385353c91540a4a2fad23847abd07d61c103ff72`. [Methodenmatrix Kapitel 16](https://github.com/5H3LL3H5/argesim-hyperposition-benchmarks/blob/9a2442f7594658dbbcf96c7911dea42d3f0dc5cd/docs/lehrbuch/gesamtausgabe/rechenlabor/kavitaet_vollgitter/daten/methodenmatrix_voll.csv)

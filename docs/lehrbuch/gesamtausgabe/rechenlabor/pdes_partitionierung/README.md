# PDES und die CP2-Kavität auf 257 × 257 Knoten

Zum Nachvollziehen der [Lookahead-Rechenprobe in Kapitel 6](../../kapitel/06.md#pdes-vorausschau) und des [Vollgittervergleichs in Kapitel 16](../../kapitel/16.md#cp2-voll-direktvergleich). Die Experimente verwenden die Solver aus [eb1e5519](https://github.com/5H3LL3H5/argesim-hyperposition-benchmarks/tree/eb1e5519c446d4b226006e30cadda6fda9d3dd76).

## Welche Daten beantworten welche Frage?

| Datei | Messung und Prüfumfang |
| --- | --- |
| [Laufzeiten und Fehler auf dem Vollgitter](vollgitter.json) | Sieben vollständige Läufe bis 136,71875. Kumulierte Kernzeiten und SHA-256 für 37 Ausgaben je Lauf, Feldvergleiche an sieben gemeinsamen Prüfzeiten, CPU-Bindung, Compiler, Toleranzen und Quellprüfsummen. |
| [DOP853-Prüffelder](DOP853_Prueffelder.zip) | Sieben ungerundete Felder des klassischen Runge-Kutta-Verfahrens. Jede Datei enthält 255 × 255 innere Werte des Zustands z = hω, als Little-Endian-float64, zuerst Zeile, dann Spalte. |
| [PDES-Versuche und Programme](PDES_Partitionierung_Messpaket.zip) | Unveränderte Veröffentlichung mit Quelltext, Tabellen, 1/4/8-Prozessläufen und Kontrollfeldern. C19R über zehn Tage, Saite parallel über vier und seriell im Nennfall über 30 Sekunden, QSS3/4-Vollgitterpräfixe über acht bzw. 32 Segmente. Die Rohdaten unterscheiden die Übereinstimmung mit der seriellen Rechnung und den Vergleich mit unabhängigen physikalischen Referenzen. |
| [Kontrollierte OpenMP-Vollversuche](CP2_D2Q9_Ursache_Slowdown_257.zip) | Zwei zusätzliche vollständige Paare auf einer und vier gebundenen CPUs, inklusive Lastgegenprobe für den anders gelagerten historischen Slowdown. |
| [Serielles QSS3/4-Phasenprofil](CP2_Kavitaet_257_QSS_Profil_eb1e551.zip) | Drei instrumentierte Läufe je Ordnung und separate uninstrumentierte Zustandskontrolle über acht Segmente. Wurzelsuche, Minimumsuche, Polynome und Taylor-Auswertung sind getrennt ausgewiesen. |

## Zeit und Genauigkeit gemeinsam lesen

Das normierte Geschwindigkeitsfeld enthält beide Komponenten an allen 255 × 255 inneren Orten. Für jede Prüfzeit k bilden wir die euklidische Norm des Vektorfeldfehlers, geteilt durch die Norm der ausdrücklich genannten Referenz. Erst danach wird das Maximum über die sieben Zeiten genommen. Zusätzlich enthält `max_vector_U` den größten Betrag des lokalen Fehlervektors bezogen auf die Deckelgeschwindigkeit. Somit können DOP853 relativ zu D2Q9 und D2Q9 relativ zu DOP853 verschiedene relative Werte ergeben. Zur unabhängigen zeitlichen Kontrolle des Wirbelmodells dienen DOP853 und AB2 mit zwei bzw. vier Takten. Der Unterschied zwischen dem Wirbelmodell und dem kinetischen Modell schließt die unterschiedlichen Raum- und Randdiskretisierungen ein.

D2Q9, AB2 und Gruppen-QSS führen die aus dem Bucharchiv entnommenen C++-Kerne aus. DOP853 nutzt SciPy mit derselben räumlichen rechten Seite wie die komponentenweisen QSS-Solver. DOP853 wählte 11.218 Schritte und benötigte einschließlich dichter Ausgabe 135.074 Auswertungen der rechten Seite. Die 37 D2Q9-Felddateien aus serieller und OpenMP-Ausführung stimmen einschließlich Dichte byteweise überein. Die Tabelle gibt für jeden Integrator eine gemessene Kern-Wandzeit an, ausgenommen Dateiausgabe. CPU-Zeit, Laufzeit der C++-Programme einschließlich Prozessstart und Ausgabe sowie beim Python-Lauf die Gesamtdauer von Solverinitialisierung bis zur letzten Ausgabe stehen in den Rohdaten. Die C++-Läufe waren untereinander sequenziell mit Affinität 0 bzw. 0–3. DOP853 durfte auf CPU 8 gleichzeitig laufen. Zur Messwiederholung sollten Hardware und laufende Last protokolliert werden.

## Den Vergleich wiederholen

Für die Wiederholung werden Linux, mindestens vier im Affinitätsmaskensatz verfügbare CPUs, GCC mit C++20 und OpenMP, libfftw3.so.3, NumPy und SciPy benötigt. Das Arbeitsverzeichnis enthält nach dem Lauf auch die 37 unkomprimierten Felder jedes Verfahrens. Die sieben Prüfzeiten entsprechen den Takten 256, 4096, 16384, 65536, 131072, 262144 und 350000. Die Befehle starten im Repository-Stamm. Im entpackten vollständigen Offline-Labor genügt es, die Variable `labor` auf `rechenlabor/pdes_partitionierung` zu setzen. Beide Varianten wählen geeignete CPUs aus der Prozessaffinität.

```bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
labor=docs/lehrbuch/gesamtausgabe/rechenlabor/pdes_partitionierung
arbeit=$(mktemp -d)
python "$labor/vollgitter.py" prepare "$arbeit" --repo .
for methode in ab2-s4 lbm4 gqss1 ab2-s2 lbm1 gqss2 dop853
do
  python "$labor/vollgitter.py" "$methode" "$arbeit" --repo .
done
python "$labor/vollgitter.py" evaluate "$arbeit" --repo . --output "$arbeit/vollgitter.json"
```

Mit `--cpus 0 1 2 3` bzw. einer einzelnen zugänglichen CPU lassen sich Worker explizit binden. Für einen Vergleich mit der vorliegenden Messung verwendet man die protokollierten Parameter und beachtet die unterschiedliche Maschinenlast. Die Prüfsumme des gesamten Quellarchivs gehört zur gemessenen Revision. Die Prüfsummen der drei einzelnen nativen Kerne erlauben den direkten Vergleich nach Änderungen an anderen Laborprogrammen.

`python "$labor/nachweis.py"` prüft ohne erneute Simulation die Vollständigkeit der Zeitreihen, die sieben DOP853-Felder, die LBM-Gleichheit, die gedruckte Fehlertabelle und sämtliche internen SHA-256-Werte des PDES-Pakets. `python "$labor/partitionen_zeichnen.py" /tmp/pdes_c19r.svg` erzeugt Abbildung 6.9 aus den gezählten Ereignissen.

[Originaldefinition von CP2 auf S. 55](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/CP/CP2-definition.pdf) · [Quellen und klassische Referenz des früheren Kavitätenlabors](../kavitaet_vollgitter/README.md)

## Vollständige MPI-Reihe und QSS dritter und vierter Ordnung

Die [Rohdaten der Skalierungsreihe](Skalierung_Messdaten.zip) enthalten vier D2Q9-Endmessungen bei 350 000 Takten, 40 vollständige C19R-Läufe, 24 kurze LP-Kontrollläufe und zwei vollständige Gruppen-QSS-Bahnen. Für beide Gruppenmethoden stehen die [Wirbelfelder an sieben Prüfterminen](Gruppen_QSS34_Prueffelder.zip) bereit. Die [sieben D2Q9-Referenzfelder](D2Q9_Prueffelder.zip) enthalten Dichte und beide normierten Geschwindigkeitskomponenten. Im kompakten Labor liegen die Zeitreihen und Prüfsummen. Für Feldvergleiche und die Wiederaufnahme ergänzt man die beiden verlinkten Feldarchive und den Fortsetzungspunkt im selben Verzeichnis. Das vollständige Offline-Labor enthält alle drei Archive. Zusammen mit den DOP853-Prüffeldern lassen sich alle Feldfehler aus den veröffentlichten Zahlen neu berechnen. Die Quellen der MPI-Kerne stehen im separat verlinkten Partitionspaket.

| Versuch | Arbeitsteilung und zeitlicher Umfang |
| --- | --- |
| CP2, D2Q9 | 1, 2, 4 und 8 MPI-Prozesse. Jeweils 350 000 Takte auf 257 × 257 Knoten. Der Eindomänen-MPI-Lauf ist die Basis der MPI-Speedups. |
| C19R, QSS1 | 1, 2, 4 und 8 LPs in ebenso vielen MPI-Prozessen. Nominaler Zehntagesfall, fünf Wiederholungen je Protokoll und LP-Zahl, acht Beobachtungen. |
| CP2, komponentenweises QSS3 und QSS4 auf mehreren LPs | 1, 2, 4 und 8 Prozesse mit jeweils eigenem LP. Drei Wiederholungen der ersten acht Intervalle. Jeder Lauf wurde mit der seriellen Referenzspur verglichen. |
| CP2, Gruppen-QSS3 und Gruppen-QSS4 | Ein Prozess, eine Vektorgruppe, 65 025 innere Wirbelwerte. Vollständige Kern- und Gesamtzeiten, 37 Ausgaben, sieben ungerundete Prüffelder je Verfahren. |
| CP2, fortsetzbare komponentenweise Langläufe | Zwei Einzelrechnungen auf dem Vollgitter mit dem Quantum 0,001 und Zielzeit 136,71875. Fortschritt, Status und Anzahl erreichter Prüfzeiten stehen je Ordnung im Paket. |

Die erste MPI-Serie und die beiden auf CPU 0 gemessenen Gruppenläufe enthalten je einen Zeitwert pro Konfiguration. Die Rohdaten dokumentieren CPU, Affinität, Compiler, Rundungsoptionen und Softwareversionen. Die separat geprüfte Wiederholung der Gruppenläufe ergab an allen sieben Terminen bytegleiche Wirbelzustände. Die komponentenweisen Anlaufzeiten mit mehreren LPs beziehen den Prozessstart ein. Die beiden langen Einzelrechnungen teilten sich bei der ersten Sicherung eine logische CPU. Ihre bis dahin verstrichene Wandzeit dient der Fortschrittskontrolle.

Die Befehle beginnen im Repository-Stamm. Für den MPI-Neulauf werden Open MPI mit Entwicklungskopfdateien, GCC mit C++20, FFTW3, Python mit NumPy und SciPy sowie acht zugängliche CPUs benötigt. Die Prüfung der gesicherten Zeiten und Hashes benötigt allein die Python-Standardbibliothek.

```bash
lab=docs/lehrbuch/gesamtausgabe/rechenlabor/pdes_partitionierung
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
python "$lab/skalierung_pruefen.py"
python "$lab/skalierung_pruefen.py" --fields .
work=$(mktemp -d)
python "$lab/skalierung.py" prepare . "$work"
python "$lab/skalierung.py" lbm . "$work"
python "$lab/skalierung.py" c19 . "$work"
python "$lab/skalierung.py" prefix . "$work"
python "$lab/skalierung.py" groups . "$work"
python "$lab/qss_gegenprobe.py" .
```

Das [Protokoll des späteren Fortsetzungspunkts](Einzelkalender_Stand.json) enthält die erreichten Modellzeiten und den Feldvergleich an den bereits erreichten Prüfterminen.

Der [Fortsetzungspunkt für beide Ordnungen](QSS34_Fortsetzung.zip) umfasst die kontinuierlichen und die quantisierten Polynome, Modellzeit, Arbeit, letzte Schrittweite und Ausgabeposition. Jede Sicherung ersetzt die letzte vollständig geschriebene Datei atomar. Das folgende Beispiel setzt die Rechnung bis zur Zielzeit fort. Ein SIGTERM oder SIGINT sichert den nächsten bestätigten Zustand. Die Laufzeit wird über die ausgeführten Rechenabschnitte addiert. Die Dauer zwischen zwei Ausführungen zählt separat zur Kalenderzeit des gesamten Auftrags.

```bash
python -m zipfile -e "$lab/QSS34_Fortsetzung.zip" "$work"
python "$lab/qss_langlauf.py" . "$work/qss3" --order 3 --resume
python "$lab/qss_langlauf.py" . "$work/qss4" --order 4 --resume
```

Der Workflow **CP2 QSS3-4 Langlauf** führt die beiden Ordnungen unabhängig aus. Ein Rechenfenster sichert nach höchstens drei Stunden Rechenzeit seinen Fortsetzungspunkt. Der Auftrag in `.github/cp2-qss34-run.json` verweist für die Fortsetzung auf die Nummer des abgeschlossenen Workflow-Laufs. Ein Endfeld-Artefakt wird erst geschrieben, wenn alle sieben Referenzzeitpunkte erreicht sind. Der Vergleich mit DOP853 muss auf den gespeicherten Feldern erfolgen. Die Laufzeiten der vektoriell gruppierten Methoden und der kurzen Parallelversuche haben eigene Einträge.

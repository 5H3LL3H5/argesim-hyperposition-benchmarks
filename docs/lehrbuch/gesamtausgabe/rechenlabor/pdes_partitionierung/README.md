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

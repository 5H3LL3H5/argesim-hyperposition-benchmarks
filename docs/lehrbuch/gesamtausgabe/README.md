# Numerische Simulation dynamischer Systeme

Christian Stenzel · Gesamtausgabe · Revision v9.22

## Parallele QSS und Kavität im Vollgitter

[PDES-Grundbegriffe und Amdahls Gesetz](kapitel/06.md#pdes-grundbegriffe) · [Ein bis acht logische Prozesse](kapitel/06.md#pdes-lp-messung) · [Vier vollständige MPI-Läufe](kapitel/16.md#cp2-mpi-skalierung) · [Gruppen-QSS3 und Gruppen-QSS4 bis zum Endfeld](kapitel/16.md#cp2-gruppen-hoehere-ordnung) · [Komponentenweise Langläufe](kapitel/16.md#cp2-komponenten-langlauf)

Die Revision umfasst 18 Fachkapitel und 92 nummerierte Abbildungen. Die neuen Abschnitte verbinden die Entstehung einer Grenzmeldung mit einer gemessenen Laufzeit. [Kapitel 6 mit Aktivitätskarte und Rechenprobe](kapitel/06.md#pdes-vorausschau) · [Sieben vollständige Kavitätsläufe mit zwei Referenzfeldern](kapitel/16.md#cp2-voll-direktvergleich) · [Komponentenweise QSS3/4 im Anlauf](kapitel/16.md#pdes-kavitaet) · [Primärdaten und Versuchsanleitung](rechenlabor/pdes_partitionierung/README.md)

## Nachtrag zur QSS3/4-Taylor-Kontaktprüfung

Die veröffentlichte Messreihe v9.19 bleibt als historischer Stand erhalten. Der [Nachtrag mit 120 Vergleichsfällen und Rohdaten](rechenlabor/qss_pruefung/messung/taylor_kontakt/README.md) dokumentiert getrennt, welche Ergebnisse sich durch den korrigierten Taylor-Stencil ändern.

## Kontaktprüfung und Messreihen v9.19

Die Druckfassung v9.19 hatte 493 Seiten, 18 Fachkapitel, vier Anhänge und 91 nummerierte Abbildungen. Die vier Messreihen umfassen 1.513 überprüfte Konfigurationen. Im Vergleich mit dem Skalierungsfix stimmen die 96 beidseitig vorliegenden QSS3/4-Fehlerwerte überein. Die neue Abbildung 6.8 erklärt, wann ein beinahe verschwindender Abstand tatsächlich eine Bandberührung bedeutet. [Aktuelle Primärdaten und Vergleich](rechenlabor/qss_pruefung/messung/kontakt_v919) · [Verfahren, Bild, Vertragsproben und Einzelbefunde](rechenlabor/qss_pruefung/messung/kontakt_v919/methodenregister.csv)

## Archivierte Vollgitterstudie v9.17

Die Ausgabe v9.17 umfasst 485 Druckseiten und 85 nummerierte Abbildungen. Der Vergleich auf 257 × 257 Knoten und über 350 000 Takte ist in den Kapiteln 6, 7, 8, 9, 16, 18 und Anhang D integriert. Die neuen Methodenmatrizen bewahren auch früh beendete Läufe. Das vollständige Rechenlabor enthält C++20-Kerne, Python-Kalender, Modellgewichte und prüfbare Rohfelder.

[Studie in Kapitel 16](lehrbuch_numerische_simulation.md#cp2-voll-vertrag) · [Messdaten und Wiederholung](rechenlabor/kavitaet_vollgitter/README.md)


Das vollständige Manuskript ist `lehrbuch_numerische_simulation.md`. Der mathematische Einstieg steht in `kapitel/Grundlagen.md`. Dort beginnen der Kernweg und die Vertiefung mit Aufgaben und separaten Lösungsseiten. Jedes der 18 Fachkapitel beginnt mit einer Leitfrage und endet mit der Antwort, einer Rekapitulation und einem Forschungsabschnitt. Die Einleitung führt zur Messplanung in Kapitel 17 und zur Synthese in Kapitel 18. Die Einzelkapitel, der Referenzkatalog und die Nachweisanhänge stehen unter `kapitel/`. Beim Verschieben des Manuskripts die relativen Ordnerpfade zu den Abbildungen erhalten. Die separat angebotene Master-Datei v9.16 trägt die SVG-Abbildungen im Dokument.

## Druckfassung v9.16

Der Satz umfasst 473 Buchseiten. Der [Maßnahmenkatalog](daten/massnahmen_v9_16.csv) nennt die Seiten der Vorauflage v9.15, des ersten v9.16-Abzugs und der Druckfassung. In Kapitel 4 steht der RK4-Nachweis für die Bindungsmode, in Kapitel 6 der ausgeführte Versionskalender. Die Maxima der Kavität sind über vier Wände aufgelöst. Kapitel 15 rechnet die Quellenwirkung am stromabwärtigen Sensor vor. Kapitel 18 ordnet alle 57 gedruckten Profiltreppen den 456 historischen Läufen zu.

[Geprüfte LaTeX-Bausteine](druck/Druckbausteine_v9_16.tex) · [Druckfahnenprotokoll](druck/Druckfahnenprotokoll_v9_16.pdf) · [Wiederholung und Messdaten](rechenlabor/revisionspruefung/README.md)

## Überarbeitung v9.16

Die [27 Maßnahmen](daten/massnahmen_v9_16.csv) sind nach Bearbeitungsphase geordnet. Jede Zeile führt von der Druckseite der Vorauflage zur neuen Stelle und nennt die Entscheidung und ihren Beleg. G.3 bereitet die Radau-Knoten durch eine ausgerechnete Interpolationsquadratur vor. G.7 führt die Randspur vor ihrer Verwendung an der Saite ein. Kapitel 18 dokumentiert eine ergänzende C05-Reihe mit unverändertem Fehler- und Zeitbudget. Die Zahlen zu Abb. 9.4 wurden aus dem gespeicherten Geschwindigkeitsfeld erneut berechnet. [Rechenwege und Abhängigkeiten](rechenlabor/revisionspruefung/README.md) · [Aktuelles Messregister](daten/messregister.csv)

## Frühere Überarbeitung v9.15

Die 40 fachlich bestätigten Arbeitsaufträge stehen mit den Druckseiten der damaligen Ausgabe in [der Umsetzungsliste](daten/aenderungen_v9_15.csv). Die Entscheidungen über alle 34 strittigen Aussagen des Zweitgutachtens bleiben einzeln nachzulesen. Die Begutachtung bezog sich auf die damalige Seitennummerierung. Bei den Grundlagen steht die neue Fühlergrafik jetzt zuerst. Dadurch wird die vorige periodische Aliasing-Abbildung G.4 in v9.15 zu G.5.

- [Messregister für die 80 Tabellen und die zentralen Experimente](daten/messregister.csv)
- [Erst- und Zweitgutachten im Abgleich](daten/abgleich_erst_zweit_v9_14.csv)
- [Reichweite der acht ergänzenden Prüfungen](daten/pruefumfang_v9_15.csv)
- [Operatoren nach Eingabe, Ausgabe, Referenz, Basismethode, Testbereich und Budget](daten/operatorvergleiche.csv)
- [Alle 28 offiziellen Aufgabenfamilien bzw. Teilaufgaben und ihre Lehrvarianten](daten/messauftraege.csv)
- [Wiederholungsbefehle für die neuen Experimente](rechenlabor/revisionspruefung/README.md)

Zum Neusatz ab Paketwurzel `python3 druck/setzen.py` starten. Anschließend zweimal im Ordner `druck` den Befehl `xelatex -halt-on-error buch.tex` ausführen. Erforderlich sind Pandoc, XeLaTeX, Noto Serif, Noto Sans Display, DejaVu Sans Mono und Latin Modern Math. Die Vorlage verwendet die mitgelieferten Vektor-PDFs. Der Bildatlas wird ab Paketwurzel mit `python3 rechenlabor/bildpruefung/buchatlas.py druck/buch.pdf --register-aktualisieren --atlas bildatlas.pdf` erzeugt.

## Historischer Ausbau der dynamischen Operatorversuche in v9.14

Kapitel 9 (S. 233–234) vergleicht zehn Populationsverläufe bis t=100. Kapitel 16 (S. 337–339) prüft acht vollständige Kavitätsfelder bei wechselndem Deckel und alle sieben Kerne auf beiden Aufgaben. Das [Rechenlabor CP-Dynamik](rechenlabor/cp_dynamik/README.md) enthält Einzelabfragen, Referenzen, Abbildungen, trainierte Gewichte und Skripte. Die drei neuen Abbildungen bringen den Bestand auf 82.

## Abbildungen und Prüfdaten der Revision v9.13

Die 92 Abbildungen der Gesamtausgabe v9.22 sind im [seitenbezogenen Verzeichnis](rechenlabor/bildpruefung/abbildungsverzeichnis.csv) erfasst. Die Revision v9.13 ergänzte neun Grafiken in den Kapiteln 10 bis 16 und 18. Die fünf neuen Abbildungen der Revision v9.18 stehen in Kapitel 6. Die [Versuchsanleitung](rechenlabor/bildpruefung/README.md) beschreibt die Neuberechnung, den Vergleich mit archivierten Feldern und die Leistungsprofile. Der [Prüfbericht](Pruefbericht_Gesamtlehrbuch.md) ordnet die gemeldeten Befunde der gedruckten Seite zu.

## Rechenlabor

Aus dem entpackten Verzeichnis startet `python3 pruefen.py` alle 33 Python-Prüfprogramme mit aktiven Assertions. Python 3.12 und die Standardbibliothek genügen. `beispiele/` enthält die Modelle von Teil I sowie die ergänzenden Gegenproben. `rechenlabor/kapitelvergleich.py` enthält die 17 Gegenproben der vorigen Gliederung. Seine letzte Probe gehört jetzt zur Synthese in Kapitel 18. `rechenlabor/kapitelproben.py` verwendet die historischen Arbeitsblattnummern 1 bis 13. `rechenlabor/methodenlabor.py` rechnet unter anderem die CP2-Saite mit Störmer–Verlet. `rechenlabor/rk4_vertrag.py` prüft den skalaren Integratorvertrag bis zum Endwert. `rechenlabor/auditproben.py` rechnet die ergänzten Beispiele aus Revision v9.1 nach. Dazu gehören der klassische RK4-Schritt, die QSS2-Wurzel, die D2Q9-Skalierung und die Stabilitätsgrenze von Dormand–Prince im schnellen C05-Modus. `rechenlabor/grundlagen.py` prüft die Handrechnungen im mathematischen Grundlagenteil.

Der C++20-Vertrag hat einen eigenen Einstieg. Beide Befehle werden im Stammordner ausgeführt.

```sh
c++ -std=c++20 -O2 -Wall -Wextra -Werror -pedantic rechenlabor/rhs_vertrag.cpp -o rhs_vertrag
./rhs_vertrag
```

## Transfer auf 28 Messaufgaben

Die Revision v9.12 enthält 19 zusätzliche Abbildungen, darunter zwei C04-Ereignisbilder, den Prioritätskonflikt von C10 und die vollständige Matrix mit sieben Kernen. Die Messaufträge, ihre Grenzen und alle ausführbaren Prüfpfade stehen im [Rechenlabor](rechenlabor/transferatlas/README.md). Die Einzeldaten für 196 Kombinationen enthalten Rohfehler, direkte Freigaben und Ersatzrechnungen.

## Aktionswahl und dualer Fehlernachweis

Die Abschnitte 9.27–9.32 gehen von der einzelnen Sensoranfrage über die Herleitung der Schranke zur Messung der Kosten. Im Ordner `rechenlabor/physik_residual/entscheidung/` liegen ausführbare Einzelaufrufe für C19R und CP2/3, trainierte Gewichte, unabhängige Referenzrechnungen und die C++20-Fassung des Prüfers. Die dortige [Anleitung](rechenlabor/physik_residual/entscheidung/README.md) enthält alle Aufrufe für Training, Gegenproben und eigene Sensorwerte. Die Datei `messung/einzellaeufe.json` enthält für jede Anfrage Entscheidung, Ergebnis und unabhängigen Vergleich. Die CPU-Zeiten sind getrennt dokumentiert.

## Physik-Residual-Operator in Kapitel 9

Die Abschnitte 9.17 bis 9.26 verbinden die vier Versuche der Begleitstudie mit einer neuen Schrittprüfung in C15, einem C19R-Versuch mit Messfehlergrenzen sowie der gemeinsamen Fluss- und Wandprojektion für CP2/2. Das Verzeichnis `rechenlabor/physik_residual/v98/` enthält die Begleitstudie als PDF, ihre vier Vergleichsversuche, deren Eingaben und das zugehörige Ergebnisprotokoll. Die neuen Versuche verwenden zusätzlich die C19R-Quadratur aus Kapitel 17 und die bereits im Buch archivierten Kavitätsfelder.

Die Befehle laufen vom entpackten Buchordner aus. Die Buchmessung verwendet Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0 und für die Abbildungen Matplotlib 3.10.8.

~~~sh
OPENBLAS_NUM_THREADS=1 python3 -B rechenlabor/physik_residual/v98/studie.py --out begleitstudie
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 -B rechenlabor/physik_residual/vergleich.py --out residual_ergebnisse --mit-zeiten
python3 -B rechenlabor/physik_residual/zeichnen.py
~~~

`physik_residual.json` enthält die Einzelmessungen, die ausgelösten klassischen Schritte, die zertifizierten Schranken und die unabhängigen Vergleichswerte. Die Laufzeiten stehen getrennt in `laufzeiten.json`. Der Ordner `rechenlabor/physik_residual/messung/` enthält die Buchmessung. Die angegebenen Ausführungszeiten sind an den Rechner und diese Implementierungen gebunden.

## Messplanung aus Kapitel 17

Ein Versuch je C-Familie und jede der sechs CP-Teilaufgaben verwenden denselben Planer für gleichmäßige, feste zielgerichtete und adaptive Ablesungen. Bei C19R übernimmt die kontinuierliche Green-Kern-Schranke die Fehlerprüfung. `messung/messplanung.csv` enthält die 28 Ergebnisse. Das ausführliche JSON im selben Ordner dokumentiert Referenzwerte, Messauflösung, Ablesepfade und unentscheidbare Paare. Die Wirkung der vier zusätzlichen Kanäle steht je Aufgabe unter `with_extra`. `projektdateien.json` weist die Git-Blob-Kennungen der mitgelieferten Projektdaten und -module aus.

Die Befehle laufen aus dem entpackten Ordner. Für den Vergleich wurden Python 3.12.14, NumPy 2.3.5 und SciPy 1.17.0 verwendet. `--case C10` oder `--case CP1/A` begrenzt die Rechnung auf eine Aufgabe. Ohne `--case` laufen alle 28 Aufgaben.

~~~sh
python3 -m pip install numpy==2.3.5 scipy==1.17.0
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 \
  rechenlabor/messplanung/vergleich.py --out messausgabe
~~~

`python3 rechenlabor/messplanung/zeichnen.py` liest die gespeicherte Messung und zeichnet die C19R-Abbildung neu. Dafür wurde Matplotlib 3.10.8 verwendet. Mit `--source` lässt sich auch ein neu erzeugtes JSON angeben.

## FNO-Vergleiche aus Anhang C

Der eigenständige Einstieg für C19R und C18 ist `rechenlabor/fno_benchmarks/vergleich.py`. Für die Buchmessung wurden Python 3.12.14, NumPy 2.3.5 und SciPy 1.17.0 verwendet. Die Befehle laufen vom Stammordner aus.

~~~sh
python3 -m pip install numpy==2.3.5 scipy==1.17.0
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 \
  rechenlabor/fno_benchmarks/vergleich.py --out fno_ergebnisse
~~~

Mit `--case c19r` oder `--case c18` läuft nur der gewählte Vergleich. Die Ergebnisdateien enthalten die Gewichte, Ausgaben, Testeingaben und Referenzen. Die Messung im Buch lässt sich unter `rechenlabor/fno_benchmarks/messung/` einsehen. Für die zwei Druckabbildungen verwendet `rechenlabor/fno_benchmarks/zeichnen.py` diese gespeicherten Messungen mit Matplotlib.

Das mitgelieferte C18-CSV stammt aus der Rekonstruktion der vier Kurven in den Abbildungen von Belič. Der CSV-Hash ist `36ca0ab924cb98d34cd285a2147b358cc941452c6c5c7fafbeb7ae6dd1c75a42`. Die zugrunde liegende PDF-Ausgabe ist im Projekt mit ihrem Hash dokumentiert. Für eigene Originalaufzeichnungen geben Sie `--training train.csv --validation test.csv` an. Die Dateien benötigen `time_s,thickening,force` und ein 100-Hz-Raster. [Datennachweis C18](https://github.com/5H3LL3H5/argesim-hyperposition-benchmarks/blob/main/docs/C18_FIGURE_RECONSTRUCTION.md)

`c18_projektvergleich.json` dokumentiert einen separaten Lauf mit den bestehenden linearen, statischen und rekurrenten Projektmodellen auf exakt demselben CSV. Im Benchmark-Repository ist dieser Lauf über `python -m argesim_benchmarks run C18 all --kwargs-json '{"use_digitized":true}'` zugänglich. Die Blob-Kennungen im JSON identifizieren die dabei verwendeten Dateien.

## FNO-Transfer aus Anhang D

Sechs eigenständige Experimente verwenden dieselben Referenzen wie Anhang D. Für den Lauf genügen NumPy 2.3.5 und SciPy 1.17.0 unter Python 3.12. Matplotlib wird zusätzlich zum Neuzeichnen benötigt.

~~~sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 \
  rechenlabor/fno_transfer/labor.py --out transfer_ergebnisse
~~~

Mit `--case c05`, `c07`, `c09`, `c13`, `c15` oder `cp1` läuft jeweils ein Fall. In `transfer.json` stehen die Budgets, Zeitmessungen, Referenz-Blobs und Prüfergebnisse. Die NumPy-Datei pro Versuch enthält eine Auswahl der Felder, Zustände oder trainierten Gewichte. Die für das Buch gespeicherten Messungen sind unter `rechenlabor/fno_transfer/messung/` abgelegt. Das Diagrammskript `rechenlabor/fno_transfer/zeichnen.py` verwendet diese Dateien.

`rechenlabor/fno_transfer/katalog.json` erfasst C01–C22 einschließlich C17R und C19R sowie die je drei CP-Aufgaben. Er gibt an, welche Messaufgabe einer Familie tatsächlich getestet wurde. Die C05- und C09-Funktionen in den Referenzdateien stammen direkt aus den im JSON gepinnten Projekt-Blobs. Die übrigen Gleichungen werden in der Studie aus den Modellparametern der jeweiligen Aufgaben aufgestellt.

## Alternative Operatoren aus Kapitel 9 und 16

Unter `rechenlabor/cp2_operatoren/` verwenden beide Benchmarks dieselbe PyTorch-Klasse
`HybridNeuralOperator`. Die Namen `fourier`, `laplace`, `wavelet`, `hankel`,
`radon`, `wavelet_laplace` und `fourier_mellin` wählen die Transformation.
Die Gewichte mischen drei Transformationsgruppen. Der getrennte Physikanteil kommt
von d’Alembert beziehungsweise aus dem affinen D2Q9-Grundfeld. Die kleinen
Versuchsarchitekturen dienen dem Vergleich unter gleicher Zahl von Korrekturgewichten.

Das Protokoll verwendet Python 3.12, PyTorch 2.15.0+cpu, NumPy 2.3.5 und SciPy 1.17.0.
`psutil` erfasst den Prozessspeicher, Matplotlib erzeugt die Abbildungen.
Ein C++20-Compiler baut die Referenzen aus `cp2_referenz.cpp`.

~~~sh
python3 -m pip install numpy==2.3.5 scipy==1.17.0 psutil matplotlib
python3 -m pip install torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python3 rechenlabor/cp2_operatoren/test_operatoren.py
python3 rechenlabor/cp2_operatoren/cp2_saite_benchmark.py --out saite
python3 rechenlabor/cp2_operatoren/cp2_lbm_cavity_surrogate.py --out kavitaet \
  --reference rechenlabor/cp2_operatoren/messung
~~~

Der mitgelieferte Referenzordner enthält rohe Geschwindigkeitsfelder. Auf Gittern
oberhalb von (65^2) genügt zur Neuauswertung der Kalibrierung jeweils das Endfeld.
Ohne `--reference` berechnet das Rechenlabor alle D2Q9-Referenzen neu. `--coarse`
beschränkt den Lauf auf die Re-Variation bei (65^2). `--device cuda` ist eine
Option für Rechner mit installierter CUDA-fähiger PyTorch-Ausgabe.

Die JSON-Dateien enthalten zu jedem Modell die Budgets, Einzeltests, Zeiten,
Speicherwerte und Kalibrierläufe. Die NumPy-Dateien enthalten die trainierten
Koeffizienten und eine Auswahl der Felder. Zum Neuzeichnen beide NumPy-Dateien in
einem Ordner bereitstellen und `python3 rechenlabor/cp2_operatoren/zeichnen.py --messung ORT`
ausführen. Die D2Q9-Rechnung verwendet dieselbe angegebene Deckelgeschwindigkeit
und Reynolds-Zahl für die Referenz jedes Feldes.

## Vergleich aller sieben Operatoren

Kapitel 9 führt in Abschnitten 9.12 bis 9.16 durch den Prüfaufbau, die zehn Teilaufgaben und die gerechnete Gegenprobe. Anhang D enthält die Messmatrix.

Die zehn dokumentierten ARGESIM-Teilaufgaben lassen sich in einem Lauf auswerten.
Der Einstieg liegt unter `rechenlabor/operator_vergleich/`. Die Abhängigkeiten
entsprechen dem CP2-Abschnitt weiter oben. Das Ergebnis enthält die CSV-Matrix,
ein JSON mit den Einzelfehlern, Felder und angepasste Koeffizienten.

~~~sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 \
  rechenlabor/operator_vergleich/vergleich.py --out operator_messung
~~~

Mit `--case C07` kann jede Aufgabe einzeln geprüft werden. Für CP2 startet der
Lauf die vorhandenen Prüfprogramme und bezieht die D2Q9-Eingabefelder aus dem
mitgelieferten Referenzordner. Für die linearen Faltungen werden zusätzlich
die kompakte und volle Auslese verglichen. Die Messdaten von v9.7 liegen unter
`rechenlabor/operator_vergleich/messung/`.

## Versuchsstand und Rohdaten

`daten/qss-extension.csv` enthält die 456 aktuell vermessenen Einstellungen. Das CSV-Feld `case=C21` bezeichnet hier den Ball. Die anderen Studienfenster stehen in eigenen CSV- oder JSON-Dateien. `rechenlabor/cp2_genauigkeit/` enthält gespeicherte Gitter- und Saitenmessungen. `rechenlabor/cp2_feldlabor/` enthält die Archivmetriken für das ursprüngliche FNO. Die vollständigen historischen Solver-, Trainings- und Rohfeldversuche sind über den in den Kapiteln genannten Versionsstand erreichbar. `daten/quellrevisionen.json` dokumentiert 34 über Git-Blobs identifizierte Text-, Bild- und Datenquellen. Die zur unveränderten Ausführung des Autorenlabors zusätzlich im Laborordner vorhandenen zwei Datendateien sind bytegleich mit den Exemplaren unter `daten/`.

Die erneute Auswertung von Archivzahlen ist im Prüfbericht von den hier neu ausgeführten numerischen Versuchen getrennt. `pruefprotokoll.txt` enthält die Ausgabe der Python-Prüfprogramme und den Befund zum C++20-Programm. `Pruefbericht_Gesamtlehrbuch.md` führt die Kapitel mit Seiten und Prüfgrenzen auf.

## Abbildungen und Drucksatz

Unter `abbildungen/` stehen die 90 verwendeten SVG-Abbildungen und die Satzvorgaben. Die Vektorgrafiken für die Druckausgabe sind zusätzlich im Ordner `druck/` als PDF hinterlegt. Die dortige `buch.tex` ist die gesetzte Quelle des Gesamtbuchs. Sie lässt sich mit XeLaTeX zweimal im Verzeichnis `druck/` übersetzen. Erforderlich sind eine TeX-Live-Installation mit den in der Präambel benannten Paketen und die Schriften Noto Serif, Noto Sans Display, DejaVu Sans Mono und Latin Modern Math.

Nach Änderungen am bestehenden Markdown-Manuskript erzeugt `python3 druck/setzen.py` mit Pandoc 3.1 eine neue TeX-Fassung. Die Tabellenbreiten der vorliegenden Ausgabe sind für ihre jeweiligen Spalten gesetzt. Bei geänderten Tabellen oder Abbildungen die Zuordnung am Dateiende prüfen. Der reine Rechenweg ist unabhängig vom Drucksatz.

`python3 abbildungen/zeichnen_v91.py` erzeugt die vier ergänzten SVG-Grafiken mit Matplotlib. Inkscape kann daraus die hinterlegten PDF-Grafiken neu exportieren. `python3 abbildungen/zeichnen_grundlagen.py` erzeugt die vier Bilder für Normen, Taylorentwicklung, Nullstellensuche und Aliasing. Die Tabellenbreiten der zusätzlichen Raumverfahrensübersicht sind an ihren Spaltenüberschriften verankert.

[Fixierter Projektstand](https://github.com/5H3LL3H5/argesim-hyperposition-benchmarks/tree/16f0f2528fcf77f16898ecd74ad952be2c09eac2) · [Offizielle ARGESIM-Aufgabensammlung](https://www.argesim.org/benchmarks)

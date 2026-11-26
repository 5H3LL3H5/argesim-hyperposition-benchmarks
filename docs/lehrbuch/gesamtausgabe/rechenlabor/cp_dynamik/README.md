# CP1/B und CP2/2 · Dynamik aus Anfangswerten und Randantrieben

Zwei Lehrversuche vergleichen vollständige Populationsbahnen und zeitabhängige Geschwindigkeitsfelder. Kapitel 9, S. 233–234, leitet die Populationsrechnung her. Kapitel 16, S. 337–339, zeigt die Geschichte eines Richtungswechsels in der Kavität und vergleicht sieben Transformationskerne. Alle Ausgaben nutzen die mitgelieferten Gewichte. Ein neuer Referenzlauf ist erst für die Berechnung eines tatsächlichen Fehlers nötig.

## Eine eigene Vorhersage

Die Befehle erwarten den aktuellen Ordner im entpackten Paketstamm. Python, NumPy und SciPy genügen zur Auswertung gespeicherter Gewichte. Jeder Befehl schreibt eine NPZ-Datei. Der Zeitverlauf und die benannten physikalischen Achsen stehen in derselben Datei.

~~~sh
python3 rechenlabor/cp_dynamik/vorhersage.py population --v1 1.08 --z2 0.94 --ausgabe bahn.npz
python3 rechenlabor/cp_dynamik/vorhersage.py kavitaet --deckel 0.8 0.8 0.8 0.8 -0.8 -0.8 -0.8 -0.8 --ausgabe felder.npz
python3 rechenlabor/cp_dynamik/vorhersage.py kavitaet --verfahren hankel --deckel 0.5 0.5 0.8 0.8 -0.8 0 0 0 --ausgabe hankel.npz
~~~

Für die Populationen liefert `population[t,i]` 401 Zeitstände von null bis hundert für zehn Arten. Die Namen stehen in `namen`. Für die Kavität hat `geschwindigkeit_durch_U[intervall,y,x,komponente]` die Form (8, 33, 33, 2). Die Komponenten stehen in der Reihenfolge x, y. Die Zeile y=0 liegt unten, die Abtastorte sind Zellmitten. Die Zeitpunkte folgen aus `t_stern`. Eine Null am Eingang hält den Deckel im zugehörigen Intervall an. Jede Datei enthält den Wahrheitswert `im_trainingsbereich`. Er beschreibt nur die Lage der Eingabe im parametrisierten Bereich.

Beide Programme akzeptieren als `--verfahren` die sieben Schlüssel `fourier`, `laplace`, `wavelet`, `hankel`, `radon`, `wavelet_laplace` und `fourier_mellin`. Für die Populationen stehen außerdem `affin` und `rbf_pod` (Standard) zur Wahl. Für die Kavität stehen `linear`, `quadratisch` und `pod_netz` (Standard) bereit.

## Annahmen, Eingänge und Gegenproben

**CP1/B.** Zwei von zehn positiven Anfangswerten variieren. Für die 64 Trainings-, 16 Validierungs- und 16 Innenfälle liegen die erste Beutepopulation in [0,8; 1,25] und der letzte Räuber in [0,9; 1,1]. Der nominelle Start mit zehn Einsen und acht Außenfälle werden gesondert geprüft. Die Außenfälle kombinieren v1 aus {0,45; 0,60; 1,55; 1,80} mit z2 aus {0,72; 1,32}. Die Koeffizienten der ODE kommen aus dem vorhandenen CP1/B-Projektmodell. Die Referenz verwendet DOP853 mit relativer Toleranz 2·10⁻¹¹ und absoluter Toleranz 2·10⁻¹³. Eine unabhängige Radau-Rechnung prüft die nominelle Bahn. Die veröffentlichten zehn Endwerte bilden eine weitere Kontrolle. [ARGESIM CP1, Aufgabe B](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/CP/CP1-definition.pdf)

Bei jeder Testbahn gehen vier Quotienten in das Maximum S ein. Ihre Budgets sind 1 % relativer Frobeniusfehler, 0,10 Einheiten für den größten absoluten Fehler an allen 401 Zeitpunkten, 0,02 Einheiten für den größten Fehler der zehn Endwerte und 0,06 Einheiten für z2(10). Die Positivität folgt aus der logarithmischen Darstellung. Das Archiv enthält für jede geprüfte Eingabe beide Vergleichsrechnungen sowie die Referenz.

**CP2/2.** Ein Antrieb enthält acht stückweise konstante Vielfache der Bezugsgeschwindigkeit U=0,055. 64 Trainingsantriebe, 16 Validierungsantriebe und 16 Innenfälle verwenden Faktoren in [−1, 1]. Vier gezielte Profile ergänzen Gleichlauf, Umkehr, Stopp und wiederholten Wechsel. Die acht Außenfälle haben jeweils eine größte Deckelgeschwindigkeit von 1,6 U. Die Viskosität folgt aus der auf U bezogenen Reynolds-Zahl 100. Das Original beschreibt den Lauf bei Reynolds-Zahl 1000 und konstantem Deckel. Im Zeitversuch lösen wir eine ergänzende Familie auf 33×33 Zellen. Achtmal 66 D2Q9-Schritte ergeben t*=0,88. Ein 65er-Gitter bei achtmal 130 Schritten deckt denselben dimensionslosen Zeitraum ab. Die räumliche Gegenprobe betrifft genau das Umkehrprofil. Der relative Unterschied von 9,95 % nach Rückübertragung auf die groben Zellmitten ist eine Messung der Gitterabhängigkeit. [ARGESIM CP2, zweiter Teilversuch](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/CP/CP2-definition.pdf)

Der Referenzkern aktualisiert die neun kinetischen Populationen. Das schnelle Modell gibt nach jedem Intervall die zwei makroskopischen Geschwindigkeitskomponenten aus. Das Budget umfasst 2 % relativen Raum-Zeit-Fehler und einen maximalen Vektorfehler von 0,05 U. Die drei Modelle bestehen bei 16 Innenfällen, vier besonderen Profilen und acht Außenfällen jeweils 1/1/0 (linear), 16/4/8 (quadratisch) und 16/4/8 (quadratisch mit neuronalem Residuum). Das Gewicht des Residuums wurde auf 16 unabhängigen Validierungsfällen gewählt. Der Optimierer erreichte den vorgegebenen Grenzwert von 220 Iterationen. Sein Abbruchgrund steht im Ergebnisprotokoll. Die kleinste und stärkste Anregung sind mit derselben Referenzgeschwindigkeit normiert. Gleichlauf, Ruhe und gleiche Vorgeschichten bis zu einer späteren Antriebsänderung besitzen eigene Gegenproben.

## Was die sieben Kernvarianten messen

Alle sieben verwenden die exakt archivierten 64×24-Transformationsmatrizen aus `operator_vergleich/messung/c18.npz`. Die Matrizen bilden einen Signalverlauf in drei Bändern auf dieselben acht Ablesepositionen ab. In CP1/B erhält jeder Kern die ersten 64 Abtastungen der **berechneten affinen** Grundbahn in logarithmischen Koordinaten für alle zehn Arten. Diese Daten hängen ausschließlich von den beiden Anfangswerten ab. Die Ausgabe ist eine Korrektur der POD-Koeffizienten für die volle Zeitachse. In CP2/2 erhält der Kern je Intervall die letzten acht Deckelfaktoren (mit Nullen vor dem Start), jeweils an acht Punkten gehalten, und korrigiert die linearen POD-Koeffizienten. Spätere Antriebe sind im Eingang eines früheren Felds unzugänglich.

Die Auslese enthält einen linearen Anteil und 96 Tanh-Merkmale mit fixierten, gleich initialisierten verborgenen Gewichten. Die Ausgangsgewichte werden per regularisierter Kleinstquadratrechnung aus 64 Trainingsfällen geschätzt. Die 16 Validierungsfälle wählen die Regularisierungsstärke. Die sieben Einträge bezeichnen die hier diskretisierten Kernvarianten des Buchs. Insbesondere arbeitet auch die Radon-Variante auf der eindimensionalen Zeitkoordinate. Bei CP2 bleibt die räumliche POD-Basis in jedem Vergleich dieselbe. Die sieben Kerne teilen die lineare Grundrechnung. Das speziell angepasste POD-Netz nutzt zusätzlich den quadratischen Volterra-Term.

| Kern | CP1/B innen (16) | Nominal (1) | Außen (8) | CP2/2 innen (16) | Sonderprofile (4) | Außen (8) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Fourier | 16 | 1 | 0 | 12 | 2 | 0 |
| Laplace | 16 | 1 | 0 | 15 | 1 | 0 |
| Wavelet | 16 | 1 | 0 | 15 | 3 | 1 |
| Hankel | 16 | 1 | 0 | 16 | 4 | 0 |
| Radon (1D) | 16 | 1 | 0 | 16 | 3 | 0 |
| Wavelet–Laplace | 16 | 1 | 0 | 15 | 2 | 0 |
| Fourier–Mellin | 16 | 1 | 0 | 13 | 0 | 0 |

Der Score verwendet die bekannte Referenz bei der nachträglichen Auswertung. Für eine neue Anfrage ohne Referenz liefert die Inferenz den Schätzwert. Die gemessenen Fehler sind Aussagen über die genannten Stichproben.

## Nachrechnen und Abbildungen zeichnen

Für die Referenzen werden Python, NumPy, SciPy und ein C++20-Compiler benötigt. Für die Grafiken kommt Matplotlib hinzu. Der C++-Code für die Kavität liegt in `rechenlabor/cp2_operatoren/cp2_referenz.cpp`. Der Modus `history` unterstützt beliebige Folgen stückweise konstanter Deckelgeschwindigkeiten bei fester Viskosität. Das trainierte Modell verwendet acht Intervalle. Training, Validierung und Test verwenden disjunkte, mit festen Seeds erzeugte Eingaben. Die Single-Thread-Einstellung gilt für die gemessenen CPU-Zeiten.

~~~sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
python3 -B rechenlabor/cp_dynamik/populationen.py
python3 -B rechenlabor/cp_dynamik/kavitaet.py
python3 -B rechenlabor/cp_dynamik/kernvergleich.py
python3 -B rechenlabor/cp_dynamik/test_dynamik.py
python3 -B rechenlabor/cp_dynamik/zeichnen.py
~~~

**Dateien und Zeitmessung.** Im Ordner `messung` liegen getrennt Referenzbahnen bzw. -felder, trainierte Gewichte, Einzelmessungen, zusammengefasste Fehler und Laufzeiten. Die Dateien `*_kerne_einzel.csv` enthalten zusammen 371 Prüfungen, die Dateien `*_einzel.csv` ohne das Wort »kerne« 134 weitere Prüfungen der Grundmodelle. Die sieben Kernelvorhersagen lassen sich für jede Testeingabe aus den archivierten Gewichten erzeugen. `*_kerne_aufwand.csv` nennt für jeden Kern Medianlatenz, Zahl der angepassten Ausgabegewichte, Array-Speicher aller gemeinsam geladenen und kernspezifischen Gewichte in Bytes sowie die gemessene Trainingszeit. Diese Speichergröße erfasst die Modellarrays im Arbeitsspeicher. Alle Timings stammen von der CPU. Die gemeinsame Vorbereitung umfasst Referenzen für Training und Validierung und die komplette gemeinsame Modellanpassung. Der zusätzliche Aufwand eines Kerns umfasst seine Anpassung und die Wahl der Regularisierung.

Die Zeit einer Abfrage umfasst alle Ausgaben eines Falls. Gezählt wird der Median je Eingabe, dann der Median über dieselben fünf unbekannten Innenfälle. D2Q9 erfasst Integration und Dekodierung der Geschwindigkeiten ohne Dateizugriffe. Der Python-Code misst die Modellauswertung mit bereits geladenen Gewichten. Die Amortisation ist die erste ganze Anzahl von Anfragen, für die Vorbereitung plus wiederholte Inferenz schneller als die Einzelrechnungen sind. Das setzt passende Eingaben und akzeptable Fehler voraus. Die nichtlinearen Modelle mit trainiertem RBF-Zweig bei CP1/B und mit quadratischem Grundmodell und Netzrest bei CP2/2 amortisieren sich in diesem Lauf ab 84 bzw. 146 Anfragen. Für einen Einzelauftrag fallen die Vorbereitungskosten nur an, wenn noch kein trainiertes Modell vorliegt.

## Stand der Forschung

Lu und Mitautoren untersuchen unter anderem POD-basierte Operatorarchitekturen. Die hier gewählte Basis dient dazu, bei gleichem Darstellungsraum den Beitrag der nichtlinearen Abbildung messbar zu machen. [Lu u. a., Computer Methods in Applied Mechanics and Engineering (2022)](https://doi.org/10.1016/j.cma.2022.114778)

Corbetta und Mitautoren untersuchen eine gelernte Kollision innerhalb eines LBM-Solvers. Xue und Mitautoren gehen 2026 einen Schritt weiter und lernen Zeitsprünge für die kinetischen Verteilungen unter Momenten- und Symmetriebedingungen. Diese Ausgaben wären ein Ausgangspunkt für eine Fortsetzung der kinetischen Dynamik. Das vorliegende Lehrmodell liefert direkt die messbaren Geschwindigkeiten im untersuchten Zeitfenster. [Corbetta u. a. (2023)](https://doi.org/10.1140/epje/s10189-023-00267-w) · [Xue u. a., Nature Communications (2026)](https://doi.org/10.1038/s41467-026-75730-1)

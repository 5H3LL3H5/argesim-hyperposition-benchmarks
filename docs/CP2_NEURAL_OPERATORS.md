# Python-Praktikum: vom Modell zum gelernten Feld

Welchen Teil einer Simulation kann man durch eine Python-Funktion austauschen? Beim Heizstab liefert eine Funktion die momentane Temperaturänderung. Bei einer gespannten Saite wollen wir eine ganze Anfangsform übergeben und zwei spätere Formen zurückbekommen. Diese Aufträge haben verschiedene Eingaben, Ausgaben und Referenzen.

## Eine Modellfunktion an mehrere Solver übergeben

Im Kernpaket bezeichnet `Rhs = Callable[[float, Sequence[float]], Sequence[float]]` die rechte Seite einer expliziten ODE. Ein Funktionsobjekt kann in Python übergeben, gespeichert und später aufgerufen werden. Das Komma in `(0.0,)` macht aus einer Zahl einen Zustandsvektor der Länge eins.

```python
from argesim_benchmarks.ivp import InitialValueProblem
from argesim_benchmarks.runtime import solve_ivp

def heizstab(t, zustand):
    theta, = zustand
    return ((10.0 - theta / 4.0) / 120.0,)

problem = InitialValueProblem(heizstab, 0.0, (0.0,), 60.0)
for name in ("euler", "rk4"):
    lauf = solve_ivp(problem, name, options={"step": 60.0})
    print(name, lauf.final_state[0], lauf.stats.rhs_evaluations)
```

Die Bilanz lautet 120 dθ/dt = 10 − θ/4. Ihr Gleichgewicht liegt bei 40 K Temperaturüberschuss. Nach einer Minute liefert Euler 5 K mit einem Modellaufruf, RK4 4,700114 K mit vier, die exakte Lösung 4,700124 K. `heizstab` bezeichnet die aufrufbare Funktion. `heizstab(0.0, (0.0,))` berechnet bereits eine Steigung. Wer im Modellaufruf eine globale Uhr weiterschaltet, verfälscht Zwischenstufen und verworfene Versuche eines adaptiven Solvers.

## Zwei Feldversuche

| Versuch | Von Studierenden veränderte Eingabe | Ausgabe und Kontrolle |
|---|---|---|
| CP2/3, gespannte Saite | Anfangsauslenkung entlang einer 0,5 m langen Saite, Anfangsgeschwindigkeit null | Zwei Profile bei 5 und 8 s. Trainingsfelder aus acht Sinusmoden. Eigener Test am CP2-Dreieck gegen die d’Alembert-Lösung und den vorhandenen impliziten Newmark-Solver. Wellengeschwindigkeit 0,06 m/s gemäß der korrigierten Studie. |
| CP2/2, bewegter Deckel | Glatte Anfangsdichte nahe eins, Flüssigkeit anfangs in Ruhe | Geschwindigkeitsbetrag geteilt durch Deckelgeschwindigkeit nach 16 Schritten auf 17 × 17 Zellen. Referenz ist das vorhandene D2Q9-BGK-Modell. Die feste CP2-Anfangsdichte eins ist ein eigener Prüffall. Der Definitionslauf umfasst 257 × 257 Zellen und 350.000 Schritte. |

D2Q9 transportiert neun gerichtete Populationen. Kollision entspannt sie zum lokalen Gleichgewicht, anschließend wandert jede gerichtete Population in die passende Nachbarzelle. Bei der Saite folgt jede Sinusmode einem bekannten Zeitfaktor. Ein Fourier Neural Operator (FNO) lernt aus vielen Paaren von Ein- und Ausgabefeldern, wie er räumliche Frequenzen verknüpfen soll. Die Implementierung verwendet die Klasse `neuralop.models.FNO` des Pakets `neuraloperator`.

## Training wiederholen und ein eigenes Feld auswerten

Aus dem Repository-Stamm in einer Python-Umgebung:

```sh
python -m pip install -e '.[operators]'
lab=argesim_benchmarks.experiments.cp2_operators
python -m "$lab" train rope --out ergebnisse/saite
python -m "$lab" train cavity --out ergebnisse/kavitaet
python -m "$lab" predict ergebnisse/saite/rope-weights.npz \
    ergebnisse/saite/rope-501-input.npy profil.npy
python -m unittest discover -s tests -p test_cp2_operators.py -v
```

`train` erzeugt pro Fall die Gewichte, die Referenzfelder, die Felder des FNO, die Ausgangsdaten des festen Prüffalls und die Messwerte. `predict` verwendet gespeicherte Gewichte. Für die Saite erwartet es einen physikalischen Auslenkungsvektor in Metern auf äquidistanten Knoten einschließlich der festen Enden; es gibt ein Array (2, Anzahl Knoten) in Metern zurück. Für die Kavität erwartet es positive Anfangsdichten als Array (17, 17), die letzte Zeile liegt am Deckel. Ausgabe ist (1, 17, 17) mit dimensionslosem Geschwindigkeitsbetrag. Die numerischen Gewichte sind NumPy-Archive, die ohne Pickle geladen werden.

## Was hat der Versuch ergeben?

Je Fall wurden 96 vollständige Anfangsfelder zum Training, 16 zur Wahl der Epoche und 24 zur einmaligen Testauswertung erzeugt. Die drei Zufallsfolgen sind getrennt. Der feste CP2-Fall wird zusätzlich ausgewertet. Für das Trainingsmittel als einfache Vergleichsvorhersage wird an jedem Ort und je Ausgabe ausschließlich über die 96 Trainingszielfelder gemittelt. Für die Saite zählt jedes Testfeld und jeder Ausgabetermin gleich, für die Kavität zählen ausschließlich die 15 × 15 inneren Fluidzellen. Die Norm ist der euklidische Fehler geteilt durch die Norm des jeweiligen Referenzfelds.

| Vergleich | FNO | Vergleichsrechnung |
|---|---:|---:|
| Saite, 24 glatte Testfelder, mittlerer relativer Fehler | 1,54 % | Trainingsmittel 101,98 % |
| Saite, CP2-Dreieck, 501 Knoten, 5 s | 3,00 % | Newmark 0,37 % |
| Saite, dasselbe Dreieck, 501 Knoten, 8 s | 0,88 % | Newmark 0,15 % |
| Kavität, 24 Dichtevariationen, mittlerer relativer Fehler | 11,98 % | Trainingsmittel 14,91 % |
| Kavität, feste Anfangsdichte eins, verkleinerter Lauf | 11,59 % | D2Q9 als Referenz |

Die Saite wurde auf 65 Knoten trainiert. Dasselbe Gewichtsfeld liefert am Dreieck bei 5 s auf 65 und 501 Knoten jeweils knapp 3 % Fehler. Beim klassischen Verfahren senkt das feinere Gitter den Fehler von 2,50 % auf 0,37 %. Der Gittertransfer des FNO zeigt hier eine andere Eigenschaft als Konvergenz unter Gitterverfeinerung. In der Kavität ist der Geschwindigkeitsbetrag konstruktionsbedingt nichtnegativ, der Deckelwert eins ist vorgegeben. Aus diesem einzelnen Ausgabefeld lässt sich die Massenbilanz der neun Populationen nicht bestimmen.

Seed 2027, 80 Epochen, Adam mit Lernrate 0,003 und 16 Feldern je Batch, ein CPU-Thread. Die Epochen 76 bzw. 78 lieferten den geringsten Validierungsfehler. Die Zeitprotokolle unterscheiden Referenzdatenerzeugung, Training und Inferenz auf einem Testbatch. Ein allgemeiner Geschwindigkeitsvorteil lässt sich daraus nicht ableiten. [Vollständige Messwerte](evidence/cp2-operators.json)

**Zum Selbstprüfen.** Warum muss eine ganze Anfangsform einer einzigen Datenmenge angehören? Wenn Orte derselben Kurve zugleich in Training und Test gelangen, kann der Test deren Wiedererkennen belohnen. Wiederholen Sie die Saitenrechnung mit einer schärferen Anfangsform und prüfen Sie die Form der Fehlerkurve. Welche Wellenlängen tragen den Fehler?

**Forschung und offene Frage.** Die modale Lösung einer Saite folgt durch Einsetzen jeder Sinusmode in die Wellengleichung. Bei festem d’Alembert-Anfangswertproblem liefert sie eine unabhängige physikalische Prüfung. Für die trainierten Gewichte ist eine Fehlerschranke über alle zulässigen Anfangsfelder offen. Die 24 Testfelder beschreiben die angegebene Stichprobe. [CP2-Definition](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/CP/CP2-definition.pdf) · [Korrigierte Saitendaten](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_32_4/articles/sne.32.4.10625.bncp2.OA.pdf) · [NeuralOperator](https://github.com/neuraloperator/neuraloperator) · [Kovachki et al.](https://www.jmlr.org/papers/v24/21-1524.html)

## Störmer–Verlet als zweite klassische Rechnung

Mit den gleichen festen Enden, dem CP2-Dreieck aus der Ruhe und Δt = 0,01 s ergibt die explizite Ortsform von Störmer–Verlet auf 501 Knoten 0,2313 % relativen Feldfehler nach 5 s und 0,0946 % nach 8 s. Auf 65 Knoten ergeben sich 2,4840 % und 0,9306 %. Der Vergleich verwendet die d’Alembert-Referenz und beide Ausgabetermine der Tabelle. Für 501 Knoten ist die Courant-Zahl 0,6. Bei 1001 Knoten wäre sie 1,2 und die implementierte Stabilitätsgrenze verletzt. Nachrechnen im ausgepackten Rechenlabor mit `python methodenlabor.py`. [Python-Quelltext](lehrbuch/studienbuch/material/methodenlabor.py) · [Bachelor-Lehrbuch](ARGESIM_SOLVER_STUDY.pdf)

## Genauigkeitsstudie für Saite und Kavität

Das feste Vergleichsprotokoll, fünf Abbildungen, die Operatorgrenze und die vollständige Kavitätsreferenz stehen im [Bachelor-Lehrbuch](ARGESIM_SOLVER_STUDY.pdf). Die Messdateien enthalten auch negative Transferergebnisse. [Felder, Gewichte und Ergebnisse](lehrbuch/studienbuch/material/cp2_genauigkeit/)

| Fall und Fehlergröße | Bisher | Neue Rechnung |
|---|---:|---:|
| Mittige Saite, 501 Knoten, 5 s, relativ | 3,0009 % | 0,04303 % |
| Dieselbe Saite nach 8 s | 0,8816 % | 0,01416 % |
| Kavität 17², Schritt 16, mittlerer Betragsfehler der 24 Testfelder | 11,9756 % | 0,05074 % |
| Dasselbe Feldensemble, affine Regression allein | | 0,1299 % |
| Neue Parameter 21², U = 0,1, Schritt 16, mittlerer Vektorfehler | 40,48 % beim parameterbedingten Netz ohne Nachkalibrierung | 0,156 % nach 13 Referenzläufen |

Die Saitenschicht ist ein für die lineare Wellengleichung spezialisierter Fourier-Operator. Sinusmoden berücksichtigen die festen Enden. Die modalen Faktoren wurden auf 96 synthetischen Profilen für 192 Moden und 321 Zeiten gelernt. Eine Auswertung mit der Spektralschicht von NeuralOperator prüft die Übereinstimmung. Für die Kavität stammen die 96/16/24 Dichtefelder des festen Vergleichs aus denselben Zufallsfolgen wie in der Erststudie. Das neue Modell lernt zwei vorzeichenbehaftete Geschwindigkeitskomponenten. Seine affine Regression und die restliche neuronale Korrektur werden getrennt bewertet. Die Kavitätsprognosen geben die Geschwindigkeiten in Einheiten der Deckelgeschwindigkeit aus.

Beim Nachtraining des ursprünglichen nichtlinearen Saiten-FNO bleiben Architektur und Ausgabekanäle unverändert. Zusätzliche 48 glatte und 48 dreieckige Trainingsprofile und wechselnde Auflösungen reduzieren den relativen Fehler auf 501 Knoten beim mittigen Dreieck auf 2,1815 % und 0,6218 %. Die 24 glatten Testfelder erreichen im Mittel 0,9538 %. Drei Mischfolgen sowie alle Zupfpositionen sind in den Messdaten enthalten. Der ursprüngliche Befehl für Vorhersagen lädt auch den neuen Checkpoint.

### Eine neue Eingabe auswerten

Die Befehle laufen im Wurzelverzeichnis des Repositorys. Für die Prüfung der gespeicherten Saitenprofile und Strömungsdaten genügt NumPy. Die Modellbefehle verwenden Python mit dem optionalen Paketumfang für Operatoren.

```sh
python -m pip install -e '.[operators]'
material=docs/lehrbuch/studienbuch/material
python "$material/cp2_genauigkeit/auswerten.py"
python -m argesim_benchmarks.experiments.cp2_operators predict "$material/cp2_genauigkeit/saite_fno_nachtrainiert.npz" "$material/cp2_feldlabor/rope/rope-501-input.npy" /tmp/saite_fno.npy
python -m argesim_benchmarks.experiments.cp2_operators predict-refined "$material/cp2_genauigkeit/saite.npz" "$material/cp2_feldlabor/rope/rope-501-input.npy" /tmp/saite.npy --times 2.5 5 8
python -m argesim_benchmarks.experiments.cp2_operators predict-refined "$material/cp2_genauigkeit/kavitaet.npz" "$material/cp2_feldlabor/cavity/cavity-input.npy" /tmp/geschwindigkeit.npy
python -m argesim_benchmarks.experiments.cp2_operators predict-refined "$material/cp2_genauigkeit/kavitaet_familie.npz" "$material/cp2_feldlabor/cavity/cavity-input.npy" /tmp/familie.npy --lid 0.0875 --step 12
```

Für die Saite ist die Ausgabe ein Array mit einer Zeile je Zeitpunkt und einer Spalte je Knoten. Die Kavität liefert ein Array mit Form (2, N, N), zuerst die horizontale und dann die vertikale Geschwindigkeit. Das feste Netz gilt für N = 17, U = 0,1 und Schritt 16. Das Familiennetz akzeptiert N von 17 bis 33, U von 0,075 bis 0,125 und Schritte 8 bis 24. Die gemessenen Fehler zwischen seinen Trainingskombinationen sind im Buch angegeben. Die dreizehn zusätzlichen Kalibrierläufe sind allein im dafür gekennzeichneten Vergleich enthalten.

### Studien wiederholen

```sh
python -m pip install matplotlib mpmath
python scripts/cp2_accuracy/rope_study.py
python scripts/cp2_accuracy/rope_finetune.py
python scripts/cp2_accuracy/cavity_study.py
python scripts/cp2_accuracy/conditioned_cavity.py
python scripts/cp2_accuracy/target_calibration.py
python scripts/cp2_accuracy/steady_cavity.py
python scripts/cp2_accuracy/operator_bounds.py
python scripts/cp2_accuracy/chapter_checks.py
python scripts/cp2_accuracy/constrained_pendulum.py
python scripts/cp2_accuracy/transport_check.py
python scripts/cp2_accuracy/unseen_systems.py
python scripts/cp2_accuracy/figures.py
python scripts/build_studienbuch.py
```

Die Versuche verwenden CPU, NeuralOperator 2.0.0, PyTorch 2.8 und SciPy 1.17.0. Die drei Trainingsläufe des festen Netzes ändern nur die Initialisierung und die Mischfolge der Trainingsbeispiele. Das Familiennetz verwendet separate Trainings- und Validierungsfelder. Der lange D2Q9-Lauf benötigt einen C++17-Compiler mit OpenMP-SIMD-Unterstützung. Das Skript kompiliert die Referenz, vergleicht ihren Kleingitterlauf mit dem skalaren Python-Kern und prüft beide Komponenten an je sechs Innenpunkten der publizierten Mittellinien. Jede Gittergröße endet bei derselben konvektiven Zeit. Die Profile, der Massenverlauf von Anfang zu Ende und die Unterschiede der letzten Zeitfenster sind archiviert. Der lange Lauf erzeugt eine physikalische Referenz für die Strömung. Der größte trainierte Ausgabezeitpunkt des neuronalen Kavitätsmodells ist Schritt 24. [ARGESIM-Definition](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/CP/CP2-definition.pdf) · [Ghia, Ghia und Shin, 1982](https://doi.org/10.1016/0021-9991(82)90058-4)

## Zusatzprüfungen ohne neues Training

```sh
python -m scripts.cp2_accuracy.rope_symmetry
python -m scripts.cp2_accuracy.transport_check --fixed-faces
python -m scripts.cp2_accuracy.chapter_checks --diode-grid
python scripts/cp2_accuracy/review_figures.py
```

Der Spiegeltest nutzt die drei veröffentlichten Saitenoperatoren. Die beiden
Zeit- und Raumgitterprüfungen ergänzen die Kapitel zu C21 und C19R. Dafür
werden SciPy, NumPy und mpmath benötigt. Matplotlib erzeugt die Vektorfiguren.

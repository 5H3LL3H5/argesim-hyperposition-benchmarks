# Zwei ausführbare Operatoren für C19R und CP2/3

Ein Brunnen meldet einen Wert, fordert die vorgesehene zweite Messung an oder lässt den Auftrag offen. Bei der Saite schlägt ein gelernter Filter eine Lösung des dualen Problems vor. Ein Prüfer gibt die Sensorausgabe frei, sobald ihre berechenbare Fehlergrenze das vorgegebene Budget einhält. Das Kapitel 9.27–9.32 des Lehrbuchs v9.11 erklärt die beiden Verfahren. Beide verwenden die als JSON mitgelieferten Gewichte. Für einzelne Aufträge ist kein Training erforderlich.

## Eine eigene Anfrage rechnen

Wechseln Sie nach dem Entpacken in `rechenlabor/physik_residual/entscheidung`. Die dokumentierten Messungen verwenden Python 3.12.14, NumPy 2.3.5 und SciPy 1.17.0. Die unabhängige C++20-Prüfung benötigt einen C++20-Compiler und die GMP-Entwicklungsbibliotheken mit C++-Header. Matplotlib wird für die Abbildung gebraucht.

```sh
python3 labor.py brunnen --ort 5.275 --grob 0.5
python3 labor.py brunnen --ort 5.275 --grob 0.5 --fein 0.5
python3 labor.py saite --knoten 501 --mu 5/4 --zupfstelle 2/17 --sensor 3/20
```

Die beiden Brunnenaufrufe illustrieren dieselbe Anfrage vor und nach der späteren Ablesung. `--grob` und `--fein` sind Anteile der bekannten Gesamtmasse. Die Fehlergrenze des zweiten Gerätes lässt sich mit `--fehler-fein` setzen. Das vorgegebene relative Budget ist 1 %. Für die Saite umfassen die 501 Knoten beide festen Enden. `--mu` ist das Quadrat der halben Courant-Zahl. Die Sensorposition und die Zupfstelle beziehen sich auf die Saitenlänge. Das Budget ist hier ein absoluter Fehler in Einheiten der Anfangsamplitude. `--bewegt` fügt eine definierte Anfangsgeschwindigkeit hinzu, `--gemittelt` verwendet im Inneren die Sensorgewichte 1/4, 1/2, 1/4. `--budget` und `--modell` erlauben einen eigenen Vertrag und andere trainierte Gewichte. `Problem` und `verify` in `dualer_operator.py` nehmen auch selbst erzeugte rechte Seiten und lineare Messfunktionen an.

## Nachrechnen und erneut trainieren

```sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python3 -B test_verfahren.py -v
python3 -B cpp_vergleich.py
python3 -B labor.py pruefen --out wiederholung --mit-zeiten
python3 -B labor.py trainieren --modell neu/modell.json --zeitdatei neu/vorbereitung.json
python3 -B labor.py pruefen --modell neu/modell.json --out neu/vergleich
python3 -B zeichnen.py --out bilder
```

`messung/modell.json` enthält die Parameter der Aktionsnetze und des dualen Filters. `messung/ergebnisse.json` enthält die zusammengefassten Vergleiche. `messung/einzellaeufe.json` speichert Parameter, Entscheidungsfolge, Zielwert, obere Fehlergrenze und unabhängig gerechnete Referenz je Auftrag. Bei einer offenen Anfrage entfallen Zielwert und Fehlerschranke. Zuverlässige Intervallentscheidungen verwenden rationale Zahlen. Die CPU-Zeiten und die Dauer der Datenaufbereitung mit Training stehen getrennt in `laufzeiten.json` und `vorbereitung.json`.

## Welche Daten eine Entscheidung sehen darf

`aktion.execute(station, erste_ablesung, sensor_callback, plan.choose)` erhält den späteren Wert nur durch den einmaligen Aufruf des Sensors. Die beiden Transportkerne, ihre garantierten Schranken und die groben Quadraturwerte werden bei der Einrichtung eines Brunnenorts berechnet. Der Einzelaufruf bereitet den Brunnenort ohne Referenzquadratur vor. Im Prüfprogramm liefert die ausdrücklich aktivierte Vergleichsrechnung ihren Referenzwert separat. Die Merkmale des Aktionsnetzes verwenden nur den bisher bekannten Anteilbereich, Budgets und bereits ausgeführte Schritte. Eine Vorprüfung schließt Arbeit aus, die denselben Intervalltest grundsätzlich verfehlen müsste. Die zum Vergleich ausgewertete Netzvariante ohne Vorprüfung zeigt den Beitrag dieser Regel. Bei einem unmöglichen Messwertpaar bricht die Schnittstelle mit `ValueError` ab.

`dualer_operator.solve(problem, zeuge, auswahl)` versucht eine modale Feldnäherung und ein duales Polynomfilter. Bei Bedarf folgen mehr Moden oder eine tridiagonale Lösung. `verify` prüft das Zielintervall in ganzzahliger Arithmetik. Ein unzureichendes Intervall nach dem klassischen Schritt führt zu `None`. Der Python-Prüfer und `zielpruefer.hpp` sind unabhängig implementiert. Der C++20-Header bietet `argesim::pruefe_ziel` auch ohne die Python-Bibliotheken an. Der Kommandozeileneingang akzeptiert je Anfrage `n m d scale` und anschließend vier Vektoren mit je `n` ganzen Zahlen in der Reihenfolge rechte Seite, Messfunktion, Feld, adjungierter Vorschlag. Für die Buchdaten ist `scale=1000000000`. Es gelten die Nenner `d*scale` für die rechte Seite und `scale` für die übrigen Vektoren. Die Ausgabe enthält zwei rationale Zahlen, Zielwert und Radius. Negative Budgets, ungültige Gitter oder unvollständige Aufträge haben keine Freigabe.

## Vergleich und Geltungsbereich

Beim Brunnen trainiert das Aktionsnetz an sieben Orten und 1 008 Sensorkonstellationen. Der Prüfsatz kombiniert sechs andere Positionen und neun weitere Pulsmischungen mit je drei Fehlerwerten pro Messung. Eine zweite Reihe verlegt den Brunnen über den Trainingsbereich hinaus und verbreitert die Fehlergrenze des zweiten Geräts. Die feste Aktionsfolge wurde auf den Trainingsdaten aus allen sechs Reihenfolgen gewählt. Die Intervallregel wählt bei ausreichender Information zunächst die verfeinerte Quadratur. Die klassische Kontrolle verwendet unmittelbar den robusten Wert des Green-Intervalls.

Der duale Saitenfilter lernt aus 56 adjungierten Aufgaben auf 31 und 63 Innenknoten. Das Aktionsnetz der Saite trainiert an 882 Konstellationen. Der reguläre Prüfsatz hält die Innenknotenzahlen 79, 159 und 499, sechs Parameterwerte, vier Zupfstellen und drei Sensorlagen für die Endauswertung zurück. Bewegt oder ruhend und punktweise oder gemittelt sind fest an die angegebenen Positionen gekoppelt. Der Stresstest verwendet weitere Pulsformen und die Parameter 24 und 48. Sämtliche Zahlen beziehen sich bei der Saite auf die diskrete Zielgröße nach genau einem Newmark-Schritt. Die unabhängige Vollmodenlösung dient allein der Prüfung. Auch eine analytische Chebyshev-Entwicklung durchläuft denselben Prüfer mit denselben Filtergraden.

Die Aufwandseinheiten für den Brunnen sind 3 für die erste Messung mit Rechteckwert und Prüfung, 14 für die zusätzliche Messung samt erneutem Rechteckversuch, 3 für die Verfeinerung und 7 für den klassischen Wert. Für die rein klassische Kontrolle kostet die erste Messung einzeln 1 und die zweite 12. An der Saite zählen der erste Versuch 3, eine Verfeinerung 6 und die Bandlösung 12. Diese Gewichte definieren einen Vergleich unter angenommenen Handlungskosten. Die zusätzlich gemessene CPU-Latenz schließt Auswahl, Prüfung und ausgelöste Ersatzrechnungen ein. Sie verwendet vorbereitete Gewichte und keinen physischen Sensor. Kapitel 17 des Buches verwendet bei der Katalogstudie andere Messverträge.

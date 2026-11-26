# Operatoren und Bildversuche für 28 ARGESIM-Messaufgaben

Der Projektstand `16f0f2528fcf77f16898ecd74ad952be2c09eac2` und die ursprünglichen Messverträge sind in `../messplanung/` enthalten. Die Auswahl umfasst C01 bis C22 mit den Revisionen C17R und C19R sowie je drei CP1- und CP2-Teilaufgaben. Die 28 Aufgaben definieren überprüfbare Zielgrößen und Sensoren. Zusätzliche Teilversuche der offiziellen ARGESIM-Definitionen behalten ihren eigenen Validierungsbedarf.

## Nachrechnen

Alle Befehle sind vom Ordner dieser Anleitung aus ausführbar. Das Labor benötigt Python ab 3.11, NumPy, SciPy, CPU-PyTorch und Matplotlib. Ein Durchlauf verwendet einen CPU-Thread. Die Messdateien liegen bei. Beim erneuten Rechnen ersetzen die Programme die entsprechenden lokalen Messdateien.

~~~sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python3 -B referenzen.py
python3 -B katalog.py
python3 -B quelle.py
python3 -B spektral.py
python3 -B trainingsdauer.py
python3 -B philosophen.py
python3 -B bilder.py
python3 -B -m unittest -v test_atlas
~~~

`referenzen.py` simuliert 27 Referenzbanken und vergleicht Felder, Kanalreihenfolge, Ereignisse und Zielwerte mit der Buchfassung. C19R berechnet die gerichteten Gewichte des Green-Kerns sowie eine unabhängige Quadratur in `quelle.py`. Die gesonderte Saitenprüfung lässt sich mit `python3 -B ../physik_residual/entscheidung/labor.py pruefen --out prueflauf` wiederholen.

## Einen Lauf lesen

* `katalog.csv` zählt die Freigaben und Ablesungen der vier Regeln je Aufgabe. `katalog_einzeln.csv` nennt jede angeforderte Kanalnummer (ab eins). Die Fallnummern (ab null) beziehen sich auf die gespeicherte Referenzliste. `Dual` meldet eine global geprüfte affine Abschätzung, `Hülle` den Mittelpunkt der Menge verträglicher Zielwerte. Bei `Paar` nennen zwei Indizes ununterscheidbare Fälle. Die erweiterte Variante verwendet die eigens dokumentierten Zusatzkanäle bei C01, C02, C03 und C13.
* `aktionsnetz_*.json` dokumentiert drei Aktionsnetze einschließlich der aus ihrem Training ausgeschlossenen Benchmarkgruppen. Die dualen Auslesekoeffizienten sind für jede tatsächlich angefragte Kanalmenge durch den deterministischen, im Code angegebenen Fit bestimmt. Alle Koeffizienten werden vor der rationalen Prüfung gerundet. Die Reduktion auf die geschlossene Referenzliste ist Teil des Modells.
* `quelle_einzeln.csv` erfasst Messungen, scharfe Prüfungen, Konzentrationsintervall und unabhängigen Vergleichswert. Jeder der 20 Quellabschnitte hat eine freie Rate im Intervall [0,1] und die normierte Gesamtmenge beträgt vier. Die Schranke gilt kontinuierlich. Die 4 845 Eckquellen und 256 inneren Prüfraten sind eine separate Gegenprobe. Der Versuch verwendet die 13 chronologischen Messmöglichkeiten des dokumentierten festen Plans. Die gelernte Aktion wählt zwischen scharfer Prüfung und nächster Ablesung. `quellnetz.json` enthält die Parameter der Aktionswahl und der Multiplikatoren.
* `kerne.csv` enthält 196 Aggregatzeilen. `kerne_einzeln.csv` nennt Rohfehler in Budgeteinheiten, korrektes Ereignis, direkte Freigabe und Endfehler je Versuch. Ein korrigierter Wert stammt aus dem Referenzintervall. `netzindex.json` und `kernnetze.npz` enthalten Trainings- und Testzuordnung, Abbruchgrund der Optimierung und sämtliche Gewichte. Die sieben kompakten Kerne verwenden die vorhandenen Transformationsfunktionen und den trainierten Feldeingang oder die eindimensionale Messauslese entsprechend dem jeweiligen Versuch. Die vollständige neue 28er-Matrix betrifft die Messauslese auf einem festen Kanalindex. Der frühere Feldvergleich mit räumlichen Netzen bleibt in `../cp2_operatoren/` dokumentiert.
* `trainingsdauer.csv` wiederholt C04, C19R und CP2/3 mit allen sieben Kernen und 800 statt 200 Optimierungsschritten je Start. Die Testdaten und die beiden Initialisierungen sind identisch. 375 der 574 ausgewählten Hauptanpassungen enden am festen Iterationslimit. Die Sensitivitätsanalyse berichtet den Einfluss auf die zurückgehaltenen Fälle.
* `philosophen.json` enthält die Zustandswechsel und Stäbchenbelegungen der beiden C04-Läufe, den Wartegraphen und die gleichzeitigen Konkurrenzereignisse eines C10-Referenzlaufs. Die passive Beobachtung wird gegen das unbeobachtete C04-Modell geprüft. `bilder.py` erzeugt die 19 Abbildungen neu als skalierbare SVG- und PDF-Dateien.

## Auswertung und Grenzen

Bei 352 endlichen Szenarien werden die Zeugen je Zielaufgabe mit dreifach getrennter Anpassung geprüft. Für das globale Residuum und die Rückfallintervalle kennt der Offline-Prüfer sämtliche Referenzspalten einschließlich der vom Training ausgenommenen. Eine Freigabe kann für eine bislang unbekannte Ereignisfolge mit denselben Sensorcodes falsch sein. Bei C19R schließen die physikalischen Ungleichungen dagegen alle Quellen des angegebenen Modells ein. Die bisherige CP2/3-Newmark-Prüfung bezieht sich auf den algebraischen Sensorfehler eines einzelnen diskreten Schritts.

Die sieben Kernverfahren bekommen in der neuen Studie je endlicher Aufgabe alle verfügbaren, erweiterten Kanalcodes, beim Brunnen die 13 festgelegten Ablesungen. Die getrennte Studie zur adaptiven Kanalwahl erhebt Messkosten. Beide Versuche haben deshalb verschiedene Nenner und Eingaben. Angaben zur CPU-Latenz für den ursprünglichen Quellen- und Saitenversuch stehen im Nachbarlabor. Für die hier gezählten Sensorzugriffe wurde keine Wandzeitersparnis oder finanzielle Amortisation abgeleitet.

## Messstand der Ausgabe v9.19

Die aktuelle [Methodenmatrix](daten/methodenmatrix.csv) stammt aus der Wiederholung mit dem Solver `3e7c1a0`. Im vollständigen Labor gehören die aktuellen Rohfelder und Einzelprotokolle zu derselben Wiederholung. Der folgende ursprüngliche Versuchsaufbau dokumentiert auch frühere Messstände.

# Ergänzungsstudie v9.17

Die erweiterte Studie enthält die Kleinserie und den Vollgittervergleich. [257 × 257 Knoten](vollgitter/README.md) · [Methodenmatrix](vollgitter/daten/methodenmatrix_voll.csv)

# Die deckelgetriebene Kavität mit QSS und D2Q9

Rechenlabor zur Ergänzungsstudie über ARGESIM CP2/2. Das Buch ist Christian Stenzels *Numerische Simulation dynamischer Systeme*, Gesamtausgabe v9.16. Das Paket enthält die Programme, Referenzfelder, ausgegebenen Geschwindigkeitsfelder und vollständigen Ergebnisprotokolle.

## Einen Befund nachrechnen

Benötigt werden Linux mit Python 3.12, NumPy, SciPy und Matplotlib. CasADi mit IDAS wird für die DAE-Gegenprobe verwendet. Für den zusätzlichen Operatorvergleich ist ein C++20-Compiler erforderlich. Die im Buch trainierten Gewichte liegen bei. Das Programm berechnet die 28 D2Q9-Prüffälle und alle zehn Vorhersagen erneut. Die getesteten Versionen stehen in `umgebung.json`.

```sh
python rechnen.py --grid 17 --methods qss2 --quanta .001 --workers 1 --limit 32
python quantisierer.py
python erweiterte_grenzen.py
python kontrollfelder.py
python gegenproben.py dae map
python netzvergleich.py
python auswerten.py
python pruefen.py
```

`bash wiederholen.sh` reproduziert alle Versuchsreihen. Die Programme schreiben in `daten/`. Für eine unabhängige Neuberechnung einschließlich aller engen Referenzlösungen kann man das Labor in ein neues Verzeichnis kopieren und dort ohne das mitgelieferte Verzeichnis `daten/` starten. Vorhandene Raumreferenzen und stationäre Referenzfelder werden sonst wiederverwendet. Die Original-Solver unter `original/argesim_benchmarks` und `original/nsa_devs` stammen aus den Gesamtquellen des Buches. Beim Start wird die Registry überprüft. `eqss` und `eqss1–3` sind Aliasse für die als eLIQSS bezeichneten Implementierungen. BQSS1 ist ein zusätzlicher Algorithmus neben den 18 Einträgen der bisherigen Buchmatrix.

## Einstieg in die Ergebnisse

| Datei | Bedeutung |
|---|---|
| `daten/methodenmatrix.csv` | Alle 19 QSS-Verfahren auf dem 17er-Gitter, drei ursprüngliche Quanten und die gemeinsame Kontrolle bei 0,001. Die Fehler in dieser Tabelle sind Prozentwerte. |
| `daten/integrationen_alle.csv` | Eine Zeile je regulärer Konfiguration. `time_l2_rel` und `lbm_l2_rel` sind Verhältnisse. Der Prozentwert ist das Hundertfache. `time_linf_U` ist eine lokale Vektorabweichung in Einheiten der Deckelgeschwindigkeit. |
| `daten/laeufe/` | Pro Lauf eine JSON-Datei, auch bei Fehlern und Zeitüberschreitungen. Die Detailmeldung erklärt den Abbruch. `accepted` beschreibt je nach Verfahren Ereignisse oder akzeptierte Schritte. |
| `daten/felder/`, `daten/referenz/` | Komprimierte NumPy-Rohfelder für reguläre, vollständige Integrationen und Referenzen. Im Populationsversuch heißt das Feld der hochgenauen kontinuierlichen Referenz ebenfalls `ns`. Das Suffix `_map` kennzeichnet dieses Zeitmodell. |
| `daten/quantisierer_nachversuch.csv`, `daten/erweiterte_grenzen.csv` | Zusätzliche CQSS-Zelllagen, BQSS-Zwischenquanten und erweiterte Zeit- oder Ereignisgrenzen. Die gesonderte Wiederholung bei gemeinsamem Quantum ist unter `daten/kontrollfelder/` mit vier Rohfeldern je Verfahren gespeichert. |
| `daten/gitter.csv`, `daten/gittertransfer.csv`, `daten/mach.csv` | Je Gitter und Zeitpunkt beide Fehlermaße. Im Gittertransfer wird das feinere Feld an gemeinsamen Knoten abgetastet. `gitter.csv` benennt den Nenner in beiden Normierungsrichtungen. |
| `daten/abbildungsidentitaet.csv`, `daten/kontrollen.json`, `daten/idas.csv` | Populationsidentität für Euler, Abgleich des diskreten Zustands mit dem Originalcode und den Buchfeldern, Prüfung von Poisson-Löser und Jacobimatrix sowie IDAS-Gegenprobe. |
| `daten/stationaer.csv`, `daten/ghia_profile.csv` | Ghia-Mittellinien, Komponentenfehler, einzelne Koordinaten und zeitliche Reständerung für Re = 100. |
| `daten/zeiten_median.csv`, `daten/dolan_more_quotienten.csv`, `daten/dolan_more_profil.csv` | Wiederholte Prozesszeiten bis zum letzten Messzeitpunkt und Leistungsprofile für drei Aufgaben. |
| `daten/surrogate.csv`, `daten/surrogate_einzel.csv`, `daten/surrogate_abgleich.json` | Zehn Vorhersagemethoden mit 28 neuen D2Q9-Referenzen, Kohorten und Abgleich mit dem archivierten Operatorversuch. |

## Vergleichsregeln

Die Wirbelgleichung nutzt die Variable `z=h*omega`, der Populationsversuch `z_i=(f_i-w_i)/(w_i*0.1)`. Derselbe Zahlenwert des Quantums beschreibt in diesen zwei Modellen verschiedene physikalische Auflösungen. Die ODE-Ausgaben sind vier eigenständige Läufe jeweils aus dem Anfangszustand. Die dokumentierte Laufzeit `cpu_s` betrifft den längsten Präfix, `all_prefix_cpu_s` umfasst alle gemessenen Präfixe und gegebenenfalls Wiederholungen. Nach einem Abbruch bei einer Zwischenzeit entsteht kein bestandener Vier-Zeitpunkte-Vergleich. Vorberechnete konstante Raumoperatoren, Fehlerauswertung und Datei-I/O liegen außerhalb der ODE-Zeit. Die D2Q9-Zeiten enthalten die Initialisierung des Gitters und die Feldrekonstruktion. Die D2Q9-Wandwerte stammen aus den Populationen nach dem Streaming. Bei der Deckelzeile gilt die im Buch dokumentierte makroskopische Ausgabevorschrift. Im Wirbelmodell sind Wandwerte und diskrete Divergenz konstruktionsbedingt erfüllt.

Die vollständige 19er-Reihe wurde auf dem 9er- und 17er-Gitter bei Re = 1000, auf dem 9er-Gitter bei Re = 100 und im direkten Populationstest auf dem 5er-Gitter angesetzt. Auf feineren Gittern wurden die im Bericht bezeichneten QSS-Verfahren nachgerechnet. Gitter mit 129 bzw. 257 Knoten pro Richtung dienen dem Vergleich der zwei Strömungsdiskretisierungen. CPU-Zeitgrenzen gelten je eigenständigem Präfix auf der jeweiligen Maschine und können auf anderer Hardware zu einem anderen Abbruchstatus führen.

Für LIQSS–BDF liegen auf dem Wirbelgitter die Zustände der obersten inneren Reihe im BDF-Teil, alle anderen im LIQSS2-Teil. Beim Populationsversuch gehören die neun Populationen an jedem Deckelknoten zum BDF-Teil. Die absolute BDF-Toleranz ist das Maximum aus 0,05 Quantum und 0,000002, die relative Toleranz ist 0,001. Die neun klassischen Vergleichsmethoden umfassen alle fünf ODE-Zeitintegratoren der Projekt-Registry sowie SciPys DOP853, Radau, BDF und LSODA. IDAS integriert eine eigene Index-1-Formulierung mit algebraischer Stromfunktion.

Der Dolan–Moré-Nenner ist der schnellste zulässige Lauf derselben Navier–Stokes-Aufgabe. Die Aufgaben sind 9² und 17² bei Re = 1000 bis T = 0,1 sowie 9² bei Re = 100 bis T = 0,5. Das Profil verwendet das Standardquantum 0,001 und die neun klassischen Methoden. Fehlschläge zählen bei der Berechnung des Anteils gelöster Aufgaben mit. Die getrennten Auswertungen für LBM und trainierte Operatoren beziehen sich auf deren diskrete Zielgrößen.

## Satz und Herkunft

Abbildungen und Tabellen für den Bericht entstehen mit `auswerten.py`. Die Quelldatei `satz/Studie.tex` verwendet XeLaTeX mit DejaVu-Schriften. Nach der Auswertung genügen zwei Läufe von `xelatex Studie.tex` im Verzeichnis `satz`. Die SHA-256-Summen der Eingangsdokumente stehen in `umgebung.json`. `SHA256SUMS.txt` deckt die mitgelieferten Dateien ab. Kapitel 6, 7, 8 und 16 des Buches sowie die Primärliteratur sind im Bericht belegt.

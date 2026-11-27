# CP2-Kavität · Vom Endfeld zum geprüften Anfahrverlauf

Die Versuche behandeln die anlaufende Deckelkavität mit festem Deckeltempo U = 0,1. Auf 257 × 257 Knoten erreicht der D2Q9-Vergleich nach 350 000 Takten die dimensionslose Zeit 136,71875. Die sieben veröffentlichten Zeitkerne wurden jeweils direkt und mit Grobgitterkorrektur ausgewertet. Hinzu kommen ein frei laufender gelernter Zeitschritt, Interpolationskontrollen und zwei Kombinationen aus feiner Gitterrechnung und gelernter Spätphase. Alle Modellgewichte stammen aus dem bestehenden Vollgitterlabor. Der Prüfaufruf kontrolliert die SHA-256 jeder Eingabedatei.

## Einstieg

Die kurze Prüfung verwendet Linux, Python ab 3.10, NumPy, SciPy und g++ mit OpenMP. Gemessen wurde mit Python 3.12.14, NumPy 2.3.5 und SciPy 1.17.0. Im Repository oder im entpackten vollständigen Offline-Labor in den Ordner `rechenlabor/kavitaet_verlauf` wechseln und ausführen.

```bash
python -m pip install -r requirements.txt
python reproduce.py
```

Die zwölf Regressionstests kompilieren den Referenzkern, führen einen kleinen Gitterlauf aus, vergleichen mit einer unabhängig geschriebenen NumPy-Kollision, laden reale Gewichte und prüfen die Fehlerkriterien aus den mitgelieferten Messdaten. Die große Messkampagne startet ausschließlich durch den folgenden ausdrücklichen Aufruf. Etwa 3 GB freier temporärer Plattenplatz und ein Rechner mit mindestens 2 GB verfügbarem Arbeitsspeicher werden empfohlen. Beide Zielverzeichnisse müssen neu oder leer sein.

```bash
python reproduce.py --full --raw /tmp/cp2-roh-neu --results /tmp/cp2-messung-neu
```

Jeder Prozess hat eine eigene Laufzeitgrenze. Die Standardgrenze für einen einzelnen 257er Referenzlauf beträgt acht Minuten. `--cpu NUMMER` bindet den Wiederholungslauf auf Wunsch an eine erlaubte logische CPU. Die gespeicherten Zeitmessungen beschreiben den verwendeten Linux-Host. Bei anderer Auslastung und anderer Hardware ändern sie sich. Kleine Abweichungen der Gleitkomma-Ergebnisse sind bei anderer Software oder Architektur zu erwarten.

## Welche Daten fließen in die Prognose ein?

- Die 14 Zeitkernmodelle verwenden die unveränderten Hauptreihen-Gewichte des Rechenlabors. Die Trainings-Reynolds-Zahlen sind 650, 750, 850, 950, 1050, 1150, 1250 und 1350. Die Auswahl der Regularisierung nutzte 900 und 1100. Das ursprüngliche Zeitraster hatte 37 Ausgaben, davon 34 im Training. Bei der Auswertung auf Re = 1000 sind 278 der 315 positiven Zeiten neu gegenüber allen 37 Zeiten. Die Messung bei Takt 4, 8 und 12 liegt vor der ersten Trainingszeit 16. Der große direkte Fourier-Fehler bei Takt 28 liegt innerhalb des zeitlichen Trainingsbereichs.
- Der neue Zeitschrittoperator nutzt die vorhandenen 24 räumlichen POD-Moden und ausschließlich hochaufgelöste Bahnen bei Re = 950 und 1050 für das Training seiner Ausgabematrizen. Die 158 positiven Stützzeiten plus t = 0 ergeben je 470 Übergänge. Die drei im Buch verdeckten Zeiten bleiben aus dieser Anpassung ausgeschlossen. Die Zufallsmerkmale sind fest, Breite 64, Ridge-Parameter 0,01. Der freie Lauf verwendet nach dem Start die eigenen Zustände. Die separat mit `one_step_reset` bezeichnete Einzelschrittdiagnose setzt den projizierten Referenzzustand vor jedem Schritt ein. Die beiden `pod_oracle`-Zeilen sind Projektionen der bekannten Lösung auf die jeweilige Basis und messen die bestmögliche räumliche L₂-Anpassung im Innenfeld.
- Die lineare Interpolation in Re greift auf die zwei zusätzlichen Nachbarläufe zu. `interpolation_same_time` erhält ihre Felder genau zu allen Zielzeiten, `interpolation_sparse_time` nur zu den 158 positiven Stützzeiten und t = 0. Beide Varianten verwenden ausschließlich die benachbarten Reynolds-Zahlen als Eingang.
- Die feste abrupte Umschaltung wurde anhand von Re = 1000 gewählt und anschließend bei Re = 975 geprüft. Das Überblendungsfenster für die glatte Variante wurde nach der Messung des Sprungs und vor der ersten Referenzrechnung bei Re = 1025 festgelegt. Bei der anschließenden Anwendung werden das jeweils feine und grobe D2Q9-Modell aus der Ruhe gestartet. Das feine Gitter wird bis zur letzten benötigten Ausgabe mit positivem Feingittergewicht integriert. Die Grobgitterkorrektur erhält ausschließlich Zeit, Reynolds-Zahl und das eigene 65er-Grobfeld. `switch_protocol.json` und `smooth_protocol.json` enthalten die beiden vorab festgelegten Versuchsregeln.

## Messergebnisse lesen

| Datei unter `results/` | Inhalt |
| --- | --- |
| `verlauf.csv`, `vergleich.csv` | Alle 14 eingefrorenen Modelle, freier Zeitschritt und Kontrollen bei Re = 1000. Jeder Lauf hat einen absoluten Starttest und 315 positive Prüfzeiten. |
| `switch_verlauf.csv`, `switch_vergleich.csv`, `switch_fenster.csv`, `switch_viertaktschritt.csv` | Abrupte Umschaltung und Fehler beim ersten Zustandszuwachs. |
| `smooth_verlauf.csv`, `smooth_vergleich.csv`, `smooth_fenster.csv` | Überblendung für drei Reynolds-Zahlen. Zwei Fenster mit je 64 Vier-Takte-Intervallen ergänzen die Hauptserie. Zusammen gibt es 442 unterschiedliche positive Prüfzeiten je Fall. |
| `smooth_alle_knoten.csv` | Zusätzliche Auswertung einschließlich der Randknoten zu den 315 Hauptzeiten. Sechs Ausgaben je Fall überschreiten dann das lokale Budget. |
| `timing_*.json`, `paired_1025.json` | Warme Online-Wand- und Prozesszeiten. Gleiche Ausgabearrays in RAM, gleiche Ausgabegenauigkeit (float64), eine logische CPU je Lauf. Die separate Sandwichmessung bei Re = 1025 folgte nach allen anderen Solverläufen dieser Studie. |
| `n257_re*.csv`, `n65_re*.csv` und zugehörige JSON | Fortschritt, Dichten und Laufzeiten der separaten Referenz- und Nachbarrechnungen mit Dateiausgabe. |
| `reference_check.json`, `design.json`, `stepper.npz` | Gegenrechnung, Prüfplan und angepasste Gewichte des reduzierten Zeitschrittoperators. |

`rel` ist der relative Vektor-L₂-Fehler als Verhältnis. `0.01` entspricht 1 %. `max_U` ist der größte lokale euklidische Vektorfehler in Einheiten von U. Beide Größen beziehen sich in den Haupttabellen auf die 255 × 255 inneren Knoten. Am Anfang ist die Referenznorm null, deshalb bleibt das relative Feld leer. Die Randreihe vergleicht die gespeicherten makroskopischen Geschwindigkeiten mit derselben Deckelvorschrift. Eine Vier-Takte-Differenz hat andere Einheiten und eine andere Bezugsnorm als das Feld. `delta_rel` bezieht sich auf die Referenzänderung im gleichen Intervall. `space_time_rel` integriert die quadrierten Feldnormen auf der nichtäquidistanten Zeitachse mit der Trapezregel.

## Buch und Herkunft

[Kapitel 16](../../kapitel/16.md#verlauf-pruefung) enthält die Herleitung und die Abbildungen 16.19 und 16.20. Die Abbildungen lassen sich mit `python src/figures.py results /tmp/cp2-abbildungen` und Matplotlib aus den einzelnen Prüfzeiten neu erstellen.

Im Checkout liest `src/eingaben.py` die Eingaben aus `../../pakete/`. Im entpackten vollständigen Labor stammen dieselben Dateien aus `../kavitaet_vollgitter/`. Wer das kompakte Bachelor-ZIP verwendet, gibt beim Test zusätzlich `--input-archive /pfad/zum/vollstaendigen_labor.zip` an. Im Repository erzeugt `python scripts/build_studienbuch.py --full-lab /tmp/cp2-voll.zip` dieses Archiv. Das kompakte ZIP enthält alle Auswertungen und die Messdaten dieser Studie.

Die 23 SHA-256-Werte in `eingaben.json` identifizieren Quellkern, Stützzeiten, räumliche Basen, Gewichte und archivierte Referenzen. Der unveränderte D2Q9-Kern hat SHA-256 `19af37840e3a86d8f9938af78d8277bc8e857314dfe034162e85f8fca2dc8de5`. Der RAM-Treiber benutzt dessen Kollisions- und Randfunktionen. Die Tests prüfen die sieben archivierten Vollgitterfelder sowie frühe Schritte gegen eine eigenständige NumPy-Implementierung.

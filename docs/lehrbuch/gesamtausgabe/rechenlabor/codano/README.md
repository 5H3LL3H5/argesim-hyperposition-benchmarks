# Zwei gekoppelte Diffusionsfelder: CoDA-NO und FNO

Zusatzversuch zu Kapitel 9, kein offizieller CP2-Fall und keine Reproduktion
des NeurIPS-Papers. Beide Modelle lernen aus demselben Satz analytisch
erzeugter Eingabe- und Zielfelder. Download fremder Daten, Paper-Checkpoints
und W&B sind für diesen Versuch nicht nötig.

## Reproduzieren

Python 3.12, NeuralOperator 2.0.0, PyTorch 2.8.0 CPU und NumPy erforderlich.
Die feste Bibliotheksversion erwartet explizite Skalierungslisten für CoDA-NO.
Im Projekt lässt sich der optionale Abhängigkeitssatz `.[operators]` nutzen.

```sh
python austausch.py > messung-neu.json
```

Der Standardlauf verwendet einen CPU-Thread, je drei gepaarte Starts und 40
Epochen. Auswahl nur nach Validierungsfehler. Der Test benutzt dieselben
ungesehenen Koeffizienten auf dem Trainingsgitter (13 × 13) und dem feineren
Gitter (25 × 25) und führt eine getrennte Gegenprobe für die Kopplung aus:
gleiches u-Anfangsfeld, v-Anfangsfeld einmal null und einmal ein Sinusprodukt.
Das Modell soll die analytische Änderung in u vorhersagen. Randwerte werden
beiden Modellen durch die gleiche ungerade Projektion vorgegeben; ein bestandener
Randtest ist daher keine erlernte Physik.

Das Experiment vergleicht zwei kleine, konkret spezifizierte Netze unter
gleichem Daten- und Epochenbudget. Es isoliert den Beitrag der Attention weder
durch eine Ablation noch durch exakten Abgleich der Parameter-/FLOP-Zahl.
Keine Aussage über Vortraining, andere Rechtecke, PDE-Transfer oder Langzeitstabilität.
Laufzeiten sind lokal und nicht bitweise reproduzierbar.

- [Paper von Rahman et al., NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/bc75fa9843a7905bbed9d83895a88f7f-Abstract-Conference.html)
- [Forschungsrepository](https://github.com/neuraloperator/CoDA-NO)
- [Verwendete Bibliotheksimplementierung](https://neuraloperator.github.io/dev/_modules/neuralop/models/codano.html)

## Messdateien und getrennte Saitenprobe

- `messung.json` enthält die sechs abgeschlossenen FNO/CoDA-NO-Läufe.
- `saite_tfno_messung.json` vergleicht FNO und TFNO mit Tucker-Rang 0,25 an
  der CP2-Saite. Dieser zweite Vergleich verwendet eigene Eingangsfamilien,
  d’Alembert-Referenzprofile für sechs ungesehene Zupfstellen und zwei Gitter.
  Aus dem Projektcheckout mit denselben optionalen Paketen wiederholen:
  `PYTHONPATH=. python docs/lehrbuch/gesamtausgabe/rechenlabor/codano/saite_tfno.py`.
  Die letzte JSON-Zeile enthält die vollständigen sechs Trainingsläufe.
- Beide Proben verwenden unabhängige Validierungs- und Testdaten. Die
  Parameterangabe zählt komplexe Gewichte als zwei reelle Skalare.

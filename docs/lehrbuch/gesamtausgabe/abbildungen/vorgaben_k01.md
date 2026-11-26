# Zeichenvorgaben für Kapitel 1

Die beiden Diagramme und das Schaltbild stehen als einzelne SVG-Dateien im selben Ordner wie diese Anleitung. Bei einer Satzbreite von etwa 170 mm bleibt die Schrift bis in die Legenden lesbar. Die SVG-Dateien enthalten Text, Linien und Symbole als skalierbare Vektorelemente. Ein weißer Hintergrund, dunkelblaue Beschriftungen (#19394D) und hellgraue Gitterlinien (#D8E1E3) tragen alle drei Darstellungen. Die Linien unterscheiden sich zusätzlich in Muster und Symbolform.

| Datei | Geometrie, Achsen und Einheiten | Daten und Darstellung |
|---|---|---|
| phasenraum.svg | Ausgabe 7,3 × 3,48 Zoll. A zeigt die Zeit in s und Q, V als dimensionslose Größen [1]. B zeigt Q, V bei gleichem Maßstab auf beiden Achsen. | Q = cos(2t) durchgezogen in Petrol (#006D67), V = −sin(2t) gestrichelt in Rost (#A94322). Ein Umlauf von 0 bis π s. In B verläuft die Bahn im Uhrzeigersinn. Start und erster Mittendurchgang sind markiert. Graue Feldpfeile zeigen die Richtung. |
| steifigkeit.svg | Ausgabe 7,3 × 3,56 Zoll. In A und B Zeit in ms mit Marken bei 0, 3, 6, 9 und 12. A verwendet eine logarithmische Ordinate für s/c₀ und d/c₀. B verwendet eine lineare Ordinate für d/c₀. | A zeigt die Summe durchgezogen in Petrol und die Differenz gestrichelt in Rost. B zeigt die exakte Differenz als dunkelblaue Kurve, explizite Euler-Werte rostfarben als ausgefüllte Kreise und implizite Euler-Werte petrolfarben als offene Quadrate. Die numerischen Stützstellen liegen bei 3j ms für j = 0,…,4. Die Verbindungen dienen als Lesehilfe. Unter B steht das normierte Wertepaar bei 3 ms, exakt 0,0498 und implizit 0,25. Es bleibt auch auf der großen Gesamtskala lesbar. |
| rc_schaltung.svg | Ausgabe 7,3 × 2,50 Zoll. Schaltbild ohne Koordinatenachsen. Der untere Leiter definiert 0 V. Die Quelle liegt links, der Widerstand oben, der Kondensator rechts. | Dunkelblaue Leitungen, petrolfarbener Strompfeil in Richtung der oberen Kondensatorplatte, rostfarbene Spannungspfeile vom jeweiligen Plus- zum Minuspol. Widerstandsabfall Ri und Kondensatorspannung u addieren sich zu U. |

Die Diagrammüberschriften sind 12 pt, die Achsenbeschriftungen 10 pt und die Legenden mindestens 8,3 pt groß (vor dem Einpassen in den Satzspiegel). Die Schriftfamilie ist DejaVu Sans. Die Bildunterschriften im Manuskript benennen die Teilbilder ausdrücklich und erklären die Normierung. Exaktkurven werden dicht ausgewertet, Euler-Werte bleiben an den Gitterpunkten erkennbar.

## Erneut zeichnen

Für den Bildsatz genügt `python3 zeichnen.py` mit installiertem Matplotlib. Die Dateien werden neben dem Skript ausgegeben. Die sechs eigenständig ausführbaren Programme im Ordner `beispiele` benötigen ausschließlich die Python-Standardbibliothek.

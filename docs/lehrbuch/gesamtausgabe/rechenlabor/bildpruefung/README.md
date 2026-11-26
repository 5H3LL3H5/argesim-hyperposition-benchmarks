# Abbildungen prüfen und nachrechnen

Christian Stenzel · Numerische Simulation dynamischer Systeme · Register und Bildatlas der Druckfassung v9.21

Abb. 6.9 entsteht aus den Ereigniszahlen und Schnittkarten des [PDES-Labors](../pdes_partitionierung/README.md). Die Tafeln zu CP-Dynamik entstehen im [Labor für CP-Dynamik](../cp_dynamik/README.md). Der neue Fühlervergleich und die zwei ergänzten Tafeln sind im [Revisionslabor](../revisionspruefung/README.md) beschrieben.

Welche Spuren muss ein Modell hinterlassen, damit eine Abbildung seine Aussage trägt? In C12 verraten die Knicke der Positionsbahnen den Geschwindigkeitsaustausch. Bei der Diode bestimmt erst die Fortsetzung vom Anfangswert, welcher algebraische Ast zum Experiment gehört. Dieses Labor führt von den Modellparametern über die Messdatei zum druckfertigen Bild. Das Abbildungsverzeichnis nennt zu jeder Tafel des Buchs ihre Nummer, Druckseite, Quelldatei, Abmessungen und Prüfsummen.

## Reproduktion

Im entpackten Gesamtpaket und im eigenständigen Rechenlabor gelten dieselben Pfade. Vom Paketstamm aus führen die folgenden Aufrufe die Rechnungen aus, zeichnen die neun neuen Abbildungen, erstellen die sechs überarbeiteten Bilddateien und prüfen die Ergebnisse.

```sh
python3 -B rechenlabor/bildpruefung/versuche.py
python3 -B rechenlabor/bildpruefung/zeichnen.py
python3 -B rechenlabor/bildpruefung/bestand.py
python3 -B rechenlabor/bildpruefung/test_bilder.py -v
```

Benötigt werden Python ab 3.10, NumPy, SciPy, Matplotlib, PyMuPDF und für zwei überarbeitete SVG-Druckvorlagen Inkscape. Die tatsächlich geprüften Versionen stehen in `umgebung.txt`. Alle Eingabedaten liegen bei. Die wissenschaftlichen Kurven und Kartendaten werden unabhängig von der PDF-Seitenfolge erzeugt. Das seitenbezogene Verzeichnis enthält die 92 Abbildungen der Druckausgabe v9.21. Wer nur ein Teilbild ablesen möchte, findet die neun neuen Druckvorlagen im Ordner `druck/` unter dem Namen `bild_*.pdf`.

| Abbildung | Experiment und Beleg |
|---|---|
| 10.2 | Der ausführbare Ereignis- und Budgetvertrag prüft Abbruch, Beobachtungsfolge, endliche Größen und den größten Quotienten. Tests decken die Gleichheit am Budgetrand sowie falsche Kontaktidentitäten ab. |
| 11.2 | Das C05-Projektmodell in `beispiele/c05.py` liefert die geschlossene Lösung in jedem Modus. Die Zeit wird an den drei Schwellentreffern geteilt. Zustände stimmen beidseitig überein. Rohdaten in `c05_phasen.csv`. |
| 12.3 | Das ereignisdiskrete Projektmodell liefert die Stoßfolge. Aus Durchmesser, Anfangslücke und übergebenen Geschwindigkeiten werden die physischen Mittelpunkte rekonstruiert. Lücken, Impuls und Energie werden geprüft. Rohdaten in `c12_bahnen.csv`. |
| 13.2 | Die statische Kennlinie und der reduzierte Zeitverlauf mit separat geklammerter Astumkehr stehen in `c21_kennlinie.csv` und `c21_quelle.csv`. Bei effektiv 0,2 V existieren zwei Wurzeln. Die Betriebsspur reicht über 500 µs. |
| 14.3 | Originale P-Fuzzy-Regel und Originalpflanze mit DOP853 und integriertem Volumensaldo. Gegenprobe an allen 16 Taktenden mit der RK4-Projektintegration. Rohdaten in `c09_takte.csv`. |
| 15.3 | Quelle und Brunnen mit zwei verschiedenen Gitterkonventionen. Gewichtssumme und Schwerpunkt werden für beide Orte auf allen sechs Gittern geprüft. Rohdaten in `c19r_projektion.csv`. |
| 16.10 | Neuer D2Q9-Anlauf in `cp2_anlauf.npz` mit allen 17² bzw. 257² Knoten. Die neun Populationen und das Ausgabefeld des groben Gitters werden gegen das skalare Projektmodell geprüft. Die unteren Fehlerkarten stammen aus gepaarten Referenz- und Vorhersagefeldern der bestehenden Studie in `../cp2_operatoren/messung/kavitaet_felder.npz`. |
| 18.2 und 18.3 | `daten/qss-extension.csv` ist die unveränderte Messquelle. Jede feste Kombination von Methode und Quantenfaktor bleibt eine eigene Konfiguration. `456_arbeit_fehler.csv` enthält Status, Medianlaufzeit, Score und Zugehörigkeit zur Front. `57_leistungsprofile.csv` enthält die Stützstellen der rechtsstetigen Treppenfunktionen. |

Sämtliche hier genannten neuen Messdateien stehen unter `messung/`. Der Diagrammcode verwendet für Gebietsgrenzen, Kurven, Texte und Markierungen Vektoren. Für tatsächlich rasterförmige Felder speichert er die Farbwerte in einer Bildfläche. Am Originalprofil 16.6 liegen die historischen Kurven als Vektorgrafik mit eigenem Druckoriginal vor. Der Reproduktionsschritt fügt darüber die beiden Überschriften hinzu. Bei 16.8 werden Profilkurven und Ghia-Punkte aus dem Feldarchiv mit derselben Achsenkonvention neu gezeichnet.

## Was die Vergleiche tragen

456 archivierte Laufzeiten wurden neu ausgewertet. Der Zeitfaktor im Leistungsprofil bezieht sich ausschließlich auf bestandene Messungen desselben Modellfensters. Bei null bestandenen Läufen in C05 bleibt der Zeitfaktor undefiniert. Das Fenster bleibt im Nenner der Abdeckung. Die Pareto-Front enthält auch nichtdominierte Punkte oberhalb des Fehlerbudgets. Die Zeitmessungen stammen vom ursprünglichen Rechner. Die neue Auswertung wiederholt die Erhebung dieser Laufzeiten nicht. Das Zeitprofil folgt Dolan und Moré (2002), DOI 10.1007/s101070100263.

Die kleineren D2Q9-Karten in 16.1 und 16.4 geben die Originaldaten wieder. In 16.10 zeigen A und B denselben frühen dimensionslosen Zeitpunkt. C und D stammen aus einer anderen Studie und zeigen je einen Fehler gegen die zugehörige Feldreferenz. Die 421²-Referenz hatte ihr Abbruchkriterium für Stationarität noch nicht erreicht.

## Druckausgabe und Bildatlas kontrollieren

Der folgende Aufruf prüft die 92 Bildnummern in der gelieferten Buch-PDF, gleicht die Seiten und SHA-256-Werte mit dem Verzeichnis ab und erzeugt den vollständigen Bildatlas erneut. Legen Sie die Buch-PDF dazu in den Paketstamm oder geben Sie ihren Pfad an. Für die Verzeichnisseiten verwendet der Bildsatz die DejaVu-Schriften in der Standardinstallation von Debian. Ohne die Option `--atlas` führt das Programm nur die Prüfung aus.

```sh
python3 -B rechenlabor/bildpruefung/buchatlas.py lehrbuch_numerische_simulation.pdf --atlas Mein_Bildatlas.pdf
```

Die 57 Vektorlinien von Abb. 18.3 werden im [Druckfahnenversuch](../revisionspruefung/README.md) zusätzlich direkt gegen die Laufzeiten des Archivs geprüft. In Abb. 9.4 ist die Flussprojektion die mittlere der drei Balkenreihen.

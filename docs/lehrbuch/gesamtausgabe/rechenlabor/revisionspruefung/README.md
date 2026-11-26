# Rechenversuche zur Ausgabe v9.16

## Druckfahnenprüfung

Die Basisprüfung `python3 -B rechenlabor/revisionspruefung/druckfahne.py` benötigt die Standardbibliothek. Sie führt den gedruckten QSS-Kalender mit zwei Nummerierungen aus, prüft Polynomidentitäten und Nullstellenintervalle und rekonstruiert die 272 Profilstützstellen aus den archivierten Medianzeiten. Für die erneuten Feldrechnungen werden NumPy, SciPy und mpmath benötigt. Für die Vektoren der gesetzten Abb. 18.3 wird zusätzlich PyMuPDF verwendet. Der Buchpfad im folgenden Beispiel bezeichnet das separat mitgelieferte PDF oder den eigenen Neusatz.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 -B rechenlabor/revisionspruefung/druckfahne.py --felder --buch Numerische_Simulation_dynamischer_Systeme_v9_16.pdf
```

Das [Druckprotokoll der Rechnungen](messung/druckfahne_916.json) enthält alle vier Wandspuren, die sechs erneut berechneten Quellfälle, die Zunahme des zweiten Quellmoments, die Originalzeit-Minima und die Positionsprüfung der Druckkurven. Die ursprünglichen 456 Integrationen wurden über ihre Ergebniszeilen ausgewertet. Der gesonderte C05-Quantenversuch steht im eigenen Protokoll.


Die Befehle starten im entpackten Paketstamm. Die Basisprüfungen benötigen Python 3.12 mit Standardbibliothek. Für die Wandprüfung und die zusätzliche C05-Integration werden NumPy und SciPy benötigt.

| Fragestellung | Aufruf | Protokoll |
|---|---|---|
| Welchen Fehler hat die kubische Radau-Kurve bei halber Schrittweite? Welche Ereignisse, Moden, Budgets und Archivwerte ergeben sich? | `python3 -B rechenlabor/revisionspruefung/massnahmen_916.py` | Die Bruchrechnung ergibt $h^4/320$. Die Gegenproben umfassen RC-Sprung, Gleitfeld, Stiftkontakt, Kalender, Aliasing, Laplace-Mode, Nullbudget, Bayes-Schätzung und die archivierten C05- und C19R-Daten. |
| Wie verändern die zwei Projektionen das gespeicherte 65²-Fourierfeld der Kavität? | `python3 -B rechenlabor/revisionspruefung/massnahmen_916.py --wand` | [Nachrechnung aus den Feldkomponenten](messung/massnahmen_v9_16.json) |
| Bei welchem festen Quantum hält LIQSS–BDF das ursprüngliche C05-Budget ein? | `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 -B rechenlabor/revisionspruefung/c05_quanten.py` | [Vier Quantenfaktoren, fünf Zielgrößen, Einzelzeiten und Zeitgrenze](messung/c05_quanten_v9_16.json) |

Der C05-Versuch verwendet Linux bzw. einen POSIX-Rechner mit Interval-Timer und denselben Benchmarktreiber wie die 456er-Reihe. Er vergleicht drei Schaltzeiten und zwei Endzustände bis 3,5 s. Jeder abgeschlossene Versuch besteht aus dem ersten Lauf und drei gemessenen Wiederholungen mit identischem Ergebnis. Die berechneten Quanten sind Quantenfaktor mal Zustandsskala. Der Prozess begrenzt jede Integration auf zwei Sekunden. Bei anderer Hardware kann zuerst ein anderer Quantenfaktor die Zeitgrenze erreichen. Die Archivmatrix und das zusätzliche Protokoll sind getrennte Datensätze.

## Dokumentierte Versuche der vorigen Ausgabe v9.15

Alle Befehle gehen vom entpackten Paketstamm aus. Das Quellenregister nennt für jede Ergebnistabelle die Fundstelle und den SHA-256-Wert der Bezugsdatei. Maßeinheiten, Zeitfenster, Testaufteilung und Referenzgitter gehören zur jeweiligen Messung. Vor dem Vergleichen eigener Laufzeiten die Zahl der BLAS- und OpenMP-Threads auf eins setzen.

| Fragestellung | Aufruf | Ergebnis |
|---|---|---|
| Welche Takte fallen auf dieselbe absolute Uhrzeit? | `python3 rechenlabor/revisionspruefung/taktkalender.py` | Drei getrennte Taktindizes, zwei positive Integrationsintervalle, geordnete gleichzeitige Ereignisse. Python-Standardbibliothek. |
| Stimmt der gedruckte C++20-Block mit dem Programm überein? Welche Eingaberichtungen gehen verloren? | `python3 rechenlabor/revisionspruefung/gegenproben.py` | Übersetzt den Buchblock, führt zwei Python-Negativtests aus und prüft die archivierten Zeitkernmatrizen samt Radon-Impulsen. Python, NumPy, C++20-Compiler. |
| Welche Zahl liefert die Diode mit direktem Residualsolver? | `PYTHONPATH=rechenlabor/messplanung/projekt python3 rechenlabor/revisionspruefung/c21_dae_reference.py` | JSON auf der Standardausgabe. CasADi 3.8.2 mit IDAS, NumPy, SciPy. Archivierte Wiederholung in `messung/idas.json`, geladene Bibliothek und Initialisierung in `messung/idas_build.json`. |
| Ist das archivierte 421²-Endfeld bei Re = 100 wiederholbar? | `python3 rechenlabor/revisionspruefung/feingitter.py 0 erneut_konstant.json` und `python3 rechenlabor/revisionspruefung/feingitter.py 0.23 erneut_profil.json` | Frisch übersetztes C++20-Programm, neuer temporärer Cache einschließlich des 65²-Startfelds. Vier Zeitstände entstehen. Das historische Archiv enthält auf dem Feingitter nur den letzten. |
| Wie schneiden dieselben vier Grobgitterausgaben gegen eine gemeinsame Feinreferenz ab? | `python3 rechenlabor/revisionspruefung/gittervergleich.py` | Je 28 Fälle für D2Q9, lineares und quadratisches Modell sowie Quadratik plus Netz. CSV mit beiden Fehlermaßen und vollständigem Score. |
| Was ändert eine neue Stichprobe beim Anpassen? | `python3 rechenlabor/revisionspruefung/neue_starts.py` | Zwei neue Sobol-Aufteilungen der Eingaben, 64/16/16 je Durchgang und Modellfamilie. Gespeichert werden alle Eingaben, Modellwahl und unabhängige Innentests. |
| Was ändert beim Grundwasser allein das Fourier-Band oder die Quellprojektion? | `python3 rechenlabor/revisionspruefung/transport_varianten.py` | Im Bandversuch sechs Auslesebreiten. Im Quellversuch zwei Quellformen × drei Gitter bei festem Sensor. Verwendet NumPy, SciPy und mpmath. |
| Wie entsteht die Fühlergrafik? | `python3 rechenlabor/revisionspruefung/fuehlerbild.py` | SVG und Vektor-PDF aus dem Abkühlgesetz. |
| Wie entstehen die beiden dynamischen Abbildungen? | `python3 rechenlabor/cp_dynamik/zeichnen.py` | Verwendet die Bahn-NPZ, die gemessenen Felder und die 112 Zeilen der Feinreferenz. |

Die Dateien in `messung/` dokumentieren den tatsächlich ausgeführten Lauf. Die Rechenzeit hängt von Hardware und Laufumgebung ab. Die fachlichen Vergleiche verwenden die Zustandsfelder, Ereignisse und die für den jeweiligen Versuch angegebenen Budgets.

Die IDAS-Prüfung verwendet die ursprüngliche Projektimplementierung am Stand `1824c9104152674b82de6cd84d53b0b4f68dca37`. Die Kontrollreihe zum Grundwasser verwendet `transport_check.py` aus `scripts/cp2_accuracy/` am Projektstand `16f0f2528fcf77f16898ecd74ad952be2c09eac2`. Der übrige Revisionscode und seine Eingabe- und Ausgabehashes sind im vorliegenden Quellenpaket verzeichnet.

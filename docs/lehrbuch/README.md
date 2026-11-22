# Numerische Simulation dynamischer Systeme

**Autor** · Christian Stenzel

**Deutsche Bachelor-Ausgabe.** 17 Kapitel führen von Modellbildung und Systemtheorie über ODE, DAE, PDE und Solvertechnik zu ausführbaren ARGESIM-Versuchen. Die drei Teile umfassen neun Theoriekapitel, acht Kapitel zu Methodik, Leitbenchmarks und Synthese sowie die Anhänge mit 24 Referenzblättern und den 456 Einzelkonfigurationen. [Aktuelles Lehrbuch (PDF)](../ARGESIM_SOLVER_STUDY.pdf) · [PDF herunterladen](../ARGESIM_SOLVER_STUDY.pdf?raw=true) · [Python-Rechenlabor mit CP2-Gewichten (ZIP)](../ARGESIM_Bachelor_Rechenlabor.zip)

## Gliederung und Quellen

[Fachlich-didaktische Kapitelprüfung mit PDF-Fundstellen](../ARGESIM_Kapitelpruefung.md) · [Inhalt, Lesewege und Drucksatz](studienbuch/kurs.tex) · [Hauptkapitel und Anhänge](studienbuch/kapitel) · [Abnahme der PR-77-Befunde mit aktualisierten PDF-Seiten](../ARGESIM_Review_PR77_Abnahme.md)

| Teil | Inhalt |
|---|---|
| I, Kapitel 1–9 | Modellierung und Steifigkeit, explizite und implizite Integration, DAEs, Ereignisse, QSS/DEVS, räumliche Diskretisierung, Lattice-Boltzmann und Operator Learning. |
| II, Kapitel 10–17 | Prüfmethodik, C05, C12 und C21-Ball, C07 und C21-Diode, C09 und C13, C19R, CP2 sowie die Synthese über acht Modellfenster. |
| III, Anhänge A und B | 14 vertiefte Referenzblätter und die 10 weiteren Familien des Projektkatalogs, alle 456 Messkonfigurationen, Ereignis- und Intervallschranken sowie der Python- und C++-Vertrag. |

### Redaktioneller Maßstab

Jedes Theoriekapitel beginnt mit einem beobachtbaren physikalischen Vorgang und einer Leitfrage. Die Herleitung führt Voraussetzungen, Einheiten und Zwischenrechnungen ein. Eine Werkstattseite legt den inneren Algorithmus offen und schließt mit einer lösbaren Gegenprobe. Bei Benchmarks folgen auf die Leitfrage Modell, Härtefall, Methodenvergleich, Aufgaben mit Akzeptanzkriterium und Diagnose. Quellen, Datenfenster und Grenzen stehen an der betreffenden Aussage.

## Drei Einstiege in die Methodenwahl

| Frage | Rechnung im Buch |
|---|---|
| Wie wird ein Feld zu einem Zeitproblem? | Kapitel 7 führt die Linienmethode (MOL) am Wärmestab ein. Raumverfahren, Zeitintegrator und algebraische Randbedingungen lassen sich am selben Modell wechseln. Im Vier-Zellen-Versuch werden Erhaltung und Positivität getrennt geprüft. |
| Was bewegt sich im Lattice-Boltzmann-Modell? | Kapitel 8 verfolgt die Kollision und den Transport aus einer einzigen D2Q9-Zelle bis zur CP2-Deckelströmung. |
| Was lernt das Netz? | Ein Gradientenschritt von Hand führt zu FNO, PINN und DeepONet. An der CP2-Saite lassen sich die gemessenen FNO-, Newmark- und Verlet-Fehler gegen die exakte Lösung vergleichen. |

Im entpackten Rechenlabor startet `python methodenlabor.py` die Handrechnungen und die Störmer–Verlet-Studie ohne Zusatzpakete. `python cp2_feldlabor/auswerten.py` benötigt NumPy und vergleicht die archivierten Felder. [CP2-Versuchsanleitung](../CP2_NEURAL_OPERATORS.md)

## Ausgabe aktualisieren

Die Fassung auf `main` ist unter demselben PDF- und ZIP-Link erreichbar. Die Buchquellen, Abbildungen und Begleitdateien liegen gemeinsam unter [studienbuch](studienbuch/). Für den Satz werden XeLaTeX mit deutscher Silbentrennung, `xdvipdfmx`, die Schriften Noto Serif, Noto Sans Display, DejaVu Sans Mono und Latin Modern Math sowie PyMuPDF benötigt. Unter Debian und Ubuntu liefert `texlive-fonts-recommended` die von Hyperref verwendeten Schriftmetriken. Für die Prüfung des eingecheckten Buchstands genügt Python ab 3.10.

```sh
python -m pip install PyMuPDF==1.26.6
python scripts/build_studienbuch.py
python scripts/build_studienbuch.py --check
```

Der Bau schreibt PDF, ZIP und `docs/ARGESIM_Buchstand.json`. Alle drei gehören zusammen mit den geänderten Quellen in denselben Commit. Bei Pull Requests und Pushes auf `main` vergleicht die Testsuite die SHA-256-Werte der Quellen, der Messdateien und beider Ausgaben. Ein altes PDF oder Labor lässt diese Prüfung fehlschlagen.

## Kompaktfassung zum Nachschlagen

Die folgenden Markdown-Kapitel bilden die frühere Kurzfassung. Die vollständige Bachelor-Ausgabe steht oben.

| Kapitel | Leitfrage |
|---|---|
| [1 · Anfangswertproblem und Fehler](01-anfangswertproblem.md) | Wie unterscheiden sich Modellfehler, Einschrittfehler und Fehler am Messzeitpunkt? |
| [2 · Runge–Kutta](02-runge-kutta.md) | Wie liefern vier Steigungen einen Endwert, und wie regelt ein eingebettetes Paar seine Schrittweite? |
| [3 · Steifheit](03-steifheit.md) | Wann bestimmt Stabilität den Rechenaufwand, und wie dämpfen implizite Methoden? |
| [4 · PDE und Linienmethode](04-pde.md) | Wie werden aus einem Feld gekoppelte Zustände, und was zeigt die Grundwasseraufgabe C19R? |
| [5 · DAE und Konsistenz](05-dae.md) | Welche Startwerte sind zulässig, und wie testet man die C21-Diodenschaltung? |
| [6 · DEVS und Geschichte](06-devs.md) | Was geschieht mit einer geplanten Ausgabe, wenn vorher ein Eingang eintrifft? |
| [7 · QSS und Solverwahl](07-qss.md) | Wann helfen lokale Zustandsänderungen, höhere Ordnung und implizite Quantisierer? |
| [8 · ARGESIM-Fallstudien](08-argesim.md) | Welche Genauigkeit und Arbeit erreichen die Verfahren bei Kontakten und Schaltern? |
| [9 · Praktikum](09-praktikum.md) | Wie lässt sich ein eigenes Vergleichsergebnis reproduzieren und widerlegen? |
| [10 · Lösungen und Glossar](10-loesungen.md) | Welche Zahlen, Einheiten und Gegenproben sichern die Rechnung ab? |
| [Bibliographie und Quellenverzeichnis](literatur.md) | Welche Arbeiten begründen die Methode und welche Messdaten tragen den Vergleich? |

Die historischen Fachkapitel sind als separate Quellen und über den eingebetteten Studienanhang zugänglich. [DEVS und QSS](../QSS_DEVS_HISTORY.md) · [Solverwahl](../SOLVER_SELECTION.md) · [Methodenkatalog](../SOLVER_METHODS.md) · [Acht ARGESIM-Fälle](../SOLVER_COMPARISON.md)

Für den historischen Markdown-Satz mit Pandoc, WeasyPrint, lxml und Matplotlib dient `python scripts/build_solver_study.py --revision <Commit-SHA> --output kurzfassung.pdf`.

## Was verbessert die Genauigkeit der Fourier-Operatoren?

Der Zusatzversuch in Kapitel 16 untersucht sechs Zupfpositionen, vier Saitengitter, Zwischenzeiten und veränderte Kavitätsparameter. Fünf Grafiken zeigen die Ortsfehler, Modenzahl, neuronale Korrektur, Übertragung auf neue Bedingungen und den Vergleich der langen Kavitätsrechnung mit Literaturprofilen. Die Abschlussfragen aller 17 Kapitel verweisen auf Rechnung, Beweis, Gegenbeispiel oder die benötigten realen Messdaten. [Genauigkeitsstudie mit Python-Befehlen](../CP2_NEURAL_OPERATORS.md#genauigkeitsstudie-für-saite-und-kavität)

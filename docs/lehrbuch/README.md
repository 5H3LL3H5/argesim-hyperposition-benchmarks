# Numerische Simulation dynamischer Systeme

**Autor** · Christian Stenzel

**Ein deutschsprachiges Lehrbuch für Studierende der Ingenieurwissenschaften, Informatik und angewandten Mathematik.** Ein abkühlender Fühler führt von der analytischen Lösung zu Euler, Runge–Kutta und QSS. Die ARGESIM-Fälle behandeln schnelle Schaltvorgänge, elastische Kontakte, eine algebraische Diodengleichung und die getrennte Verfeinerung von Raum und Zeit. [Gesamtes Lehrbuch als PDF](../ARGESIM_SOLVER_STUDY.pdf)

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

Die vier englischen Fachkapitel der vorangegangenen Studie sind im selben PDF als Anhang enthalten. [DEVS und QSS](../QSS_DEVS_HISTORY.md) · [Solverwahl](../SOLVER_SELECTION.md) · [Methodenkatalog](../SOLVER_METHODS.md) · [Acht ARGESIM-Fälle](../SOLVER_COMPARISON.md)

## Abbildungen und PDF erstellen

Der Satz verwendet Pandoc, WeasyPrint, lxml und Matplotlib. Das Abbildungsskript benötigt auch NumPy. Die SVG-Dateien gehören zum Repository und können direkt für den PDF-Bau verwendet werden. Für die vorliegende Ausgabe wurden WeasyPrint 68.1 und Matplotlib 3.10.8 verwendet.

```sh
python scripts/lehrbuch_abbildungen.py
python scripts/build_solver_study.py --revision "$(git rev-parse HEAD)" --output lehrbuch.pdf
```

Das Argument `--revision` bestimmt das Ziel der Repository-Links im PDF. Für eine Ausgabe mit festem Quellenstand ist der Commit mit den zugehörigen Markdown-Dateien, Messdaten und Lehrbuchabbildungen anzugeben.

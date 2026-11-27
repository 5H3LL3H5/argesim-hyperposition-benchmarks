# Numerische Simulation dynamischer Systeme

**Christian Stenzel · Gesamtausgabe v9.22 · 18 Fachkapitel und vier Anhänge**

Die mathematischen Grundlagen führen von Fehlermaßen und Stabilität zu Zeitintegration, Ereignissen und räumlicher Diskretisierung. Kapitel 6 erklärt die Kalender der QSS-Familie. Kapitel 16 prüft die Verfahren an der CP2-Kavität. Kapitel 18 vergleicht ihre Entscheidungen an den ARGESIM-Modellfenstern. Die Ausgabe enthält 92 nummerierte Abbildungen.

[Lehrbuch öffnen (PDF)](../ARGESIM_SOLVER_STUDY.pdf) · [PDF herunterladen](../ARGESIM_SOLVER_STUDY.pdf?raw=true) · [Volltext und Kapitelfahrplan](gesamtausgabe/lehrbuch_numerische_simulation.md) · [Einzelkapitel](gesamtausgabe/kapitel)

## Messungen und Rechenlabor

Im Revisionsvergleich sind die Ergebnisse von 399 Basisfällen, 456 erweiterten Einstellungen, 520 Auswahlversuchen und 138 RK23-Vergleichen paarweise zugeordnet. Die ergänzende Skalierungsprüfung enthält 82 Vertragsproben sowie zwölf direkte Gegenläufe. Die Vollgitterstudie dokumentiert auch die bis zum Zeitlimit erreichten Zustände.

[1.513 Vergleichszeilen (CSV)](gesamtausgabe/rechenlabor/qss_pruefung/messung/kontakt_v919/vergleich.csv) · [Wiederholungsprotokoll](gesamtausgabe/rechenlabor/qss_pruefung/README.md) · [QSS-Prüflabor und Bachelor-Übungen (ZIP)](../ARGESIM_Bachelor_Rechenlabor.zip?raw=true) · [Vollständiges Labor mit Messfeldern und Modellgewichten](gesamtausgabe/Labor.md)

## Forschungsstudie zur Parallelisierung von QSS

Wann darf ein logischer Prozess bis zur nächsten vorhergesagten Schwelle vorausrechnen? Die Studie zu Kapitel 6 leitet sichere Zeitgrenzen und die Bedingungen für lokale Rollbacks her. Kapitel 6 führt die Messungen mit bis zu acht Prozessen anhand der Grundwasserfahne ein. Kapitel 16 vergleicht LBM, klassisches AB2, adaptives DOP853 und Gruppen-QSS auf allen 257 × 257 Knoten bis zum selben Endtermin. [Lehrbeispiel und Übung](gesamtausgabe/kapitel/06.md#pdes-vorausschau) · [Laufzeiten und Referenzfehler](gesamtausgabe/kapitel/16.md#cp2-voll-direktvergleich) · [Messpakete und Wiederholung](gesamtausgabe/rechenlabor/pdes_partitionierung/README.md)

[Forschungsstudie als PDF](QSS_PDES_Studie.pdf) · [Text und Quellen](QSS_PDES_Studie.md) · [Messwerte der seriellen Kontrollläufe](QSS_PDES_Referenzen.json) · [Python-Referenz](../../argesim_benchmarks/qss_pdes_calendar.py) · [Kalender- und Kausalitätstests](../../tests/test_qss_pdes_calendar.py)

## Druckausgabe und Nachweise

`python scripts/build_studienbuch.py --check` prüft die Ausgaben und ihre Eingaben mit der Python-Standardbibliothek. Der Drucksatz verwendet Pandoc, XeLaTeX und PyMuPDF. Der Build prüft das erzeugte TeX gegen das Manuskript und überprüft die PDF-Navigation. Der Aktionslauf **Studienbuch** liefert zusätzlich das vollständige Labor als ein ZIP-Archiv.

[Build und Prüfsummen](../ARGESIM_Buchstand.json) · [Druckquellen](gesamtausgabe/druck) · [Archiv der früheren 17-Kapitel-Ausgabe](studienbuch) · [Kapitelprüfung der früheren Ausgabe](../ARGESIM_Kapitelpruefung.md)

### Abnahme der Lehrbuchbefunde

Unter [Actions → Studienbuch](https://github.com/5H3LL3H5/argesim-hyperposition-benchmarks/actions/workflows/studienbuch.yml) startet **Run workflow** die Prüfung des ausgewählten Git-Stands. Die Zusammenfassung nennt fehlgeschlagene Tests. Im Artefakt **ARGESIM-Lehrbuchbefunde** stehen pro ID das Prüfergebnis, der Bezug zur Quelle und, soweit über ein eindeutiges PDF-Lesezeichen gefunden, die physische Buchseite. Der Bericht enthält den vollständigen Commit und die SHA-256 der geprüften PDF.

Die ersten Abnahmetests prüfen die exakte Brent-Toleranz, die PDF-Anlagenschlüssel und die Herkunft der Operator-Messdateien. Für die Messdateien bindet `source_commit` das Skript an einen Git-Baum und `source_script_sha256` an die verwendeten Skriptbytes. Das Archivregister wird gegen die Git-PDFs einschließlich ihrer physischen Seitenzahlen geprüft. Die archivierte Einstufung bleibt eine redaktionelle Entscheidung. Fachliche Einzelbelege ohne registrierten Test tragen im Bericht den Prüfstatus `manual`. Der separate Wert `review_status` gibt die Einstufung aus dem Archivregister oder der optionalen Arbeitsliste wieder.

Für die Freigabe von `book-v*`-Tags, etwa `book-v9.22`, läuft dieselbe Prüfung im strengen Modus. Der manuelle Start bietet dafür die Option `release_check`. Eine automatisierte Veröffentlichung kann den Workflow über `workflow_call` als vorgeschalteten Job für denselben Commit nutzen. Bei einem manuellen Release dient der erfolgreiche Lauf für den Tag als Freigabenachweis. Die fachliche Abnahme erfolgt anhand der verbleibenden Einzelbelege.

Lokal steht derselbe Prüfbefehl für einen Checkout mit den referenzierten Git-Commits zur Verfügung.

```sh
python -m pip install pypdf==6.21.4
python scripts/pruefe_studienbuch_befunde.py --output /tmp/ARGESIM_Lehrbuchbefunde.json
```

`--strict` liefert bei einem fehlgeschlagenen Abnahmetest Exitcode 1. Infrastruktur- und Zuordnungsfehler liefern in beiden Modi Exitcode 2. Mit `--arbeitsliste PFAD` lassen sich die IDs einer lokalen Arbeitslisten-CSV ergänzen. Ihre Ausgangsrevision steht separat im Bericht. Seitenzahlen werden für die aktuelle PDF und für die belegten Archiv-PDFs ermittelt.

## Kompaktfassung zum Nachschlagen

Die folgenden Markdown-Kapitel bilden die frühere Kurzfassung. Die Gesamtausgabe v9.22 steht oben.

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

Die historischen Fachkapitel sind als separate Quellen zugänglich. [DEVS und QSS](../QSS_DEVS_HISTORY.md) · [Solverwahl](../SOLVER_SELECTION.md) · [Methodenkatalog](../SOLVER_METHODS.md) · [Acht ARGESIM-Fälle](../SOLVER_COMPARISON.md)

Für den historischen Markdown-Satz mit Pandoc, WeasyPrint, lxml und Matplotlib dient `python scripts/build_solver_study.py --revision <Commit-SHA> --output kurzfassung.pdf`.

## Was verbessert die Genauigkeit der Fourier-Operatoren?

Der Zusatzversuch in Kapitel 16 untersucht sechs Zupfpositionen, vier Saitengitter, Zwischenzeiten und veränderte Kavitätsparameter. Fünf Grafiken zeigen die Ortsfehler, Modenzahl, neuronale Korrektur, Übertragung auf neue Bedingungen und den Vergleich der langen Kavitätsrechnung mit Literaturprofilen. Die Abschlussfragen der früheren 17-Kapitel-Ausgabe verweisen auf Rechnung, Beweis, Gegenbeispiel oder die benötigten realen Messdaten. [Genauigkeitsstudie mit Python-Befehlen](../CP2_NEURAL_OPERATORS.md#genauigkeitsstudie-für-saite-und-kavität)

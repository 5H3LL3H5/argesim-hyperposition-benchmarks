# Editionsprüfung der Vollgitterstudie v9.17

## Vollgitterstudie v9.17

Die Ausgabe umfasst 485 Druckseiten und 85 nummerierte Abbildungen. Der Vergleich auf 257 × 257 Knoten und über 350 000 Takte ist in den Kapiteln 6, 7, 8, 9, 16, 18 und Anhang D integriert. Die neuen Methodenmatrizen bewahren auch früh beendete Läufe. Das vollständige Rechenlabor enthält C++20-Kerne, Python-Kalender, Modellgewichte und prüfbare Rohfelder.

[Studie in Kapitel 16](lehrbuch_numerische_simulation.md#cp2-voll-vertrag) · [Messdaten und Wiederholung](rechenlabor/kavitaet_vollgitter/README.md)

# Druckfahne v9.16

Das Ausgangs-PDF mit 472 Seiten und die gesetzte Druckfassung mit 473 Seiten wurden stellenbezogen verglichen. Alle 27 Maßnahmenanker, 40 ursprünglichen Revisionsanker und 80 Tabellenziele sind vorhanden. Bei 83 Abbildungen stimmen Nummer, Quelldateipaar und aktuelle Druckseite. Auf den betroffenen Seiten wurden Formeln, Kalendercode, Wandgrafik und Profil visuell geprüft. Die PDF-Linienzüge aller 57 Profile stimmen mit den aus der Archivmatrix berechneten Treppen innerhalb 0,001 pt überein.

Bei den vier Korrekturstellen gibt das [Druckfahnenprotokoll](druck/Druckfahnenprotokoll_v9_16.pdf) den alten und neuen Seitenstand an. Die [Messdatei](rechenlabor/revisionspruefung/messung/druckfahne_916.json) enthält die beiden wiederholten Feldversuche, die mathematischen Gegenproben und sämtliche Profilkontrollen. 33 Standardprogramme, acht Abbildungstests und der C++20-Vertrag liefen erfolgreich.

## Historische Editionsprüfung v9.16 vor dieser Druckfahne

Christian Stenzel · Numerische Simulation dynamischer Systeme · 25. November 2026

Die Ausgangsfassung v9.15 umfasst 469 Druckseiten. Die Ausgabe v9.16 umfasst 472 Druckseiten, 18 Fachkapitel, vier Anhänge, 83 Abbildungen und 80 Tabellen. Der [Maßnahmenkatalog](daten/massnahmen_v9_16.csv) weist alle 27 Entscheidungen mit Fundstellen in beiden Ausgaben aus. Er verwendet die tatsächlichen Druckseiten. Jede Zielstelle besitzt einen internen PDF-Anker.

| Gegenstand | Prüfweg und Reichweite |
|---|---|
| Ausgabe und Verweise | Titel, Impressumsangabe im Quellenstand, PDF-Metadaten, 27 Maßnahmenanker, 80 Tabellenziele und 83 Bildunterschriften mit Quellenpaaren geprüft. |
| Rechenwege | Die lokale Radau-Abweichung, der RC-Sprung, der gemeinsame Tangentialraum des Stiftpendels, die Filippov-Gewichte, der QSS-Kalender, die Laplace-Mode und zwei Schätzer wurden unabhängig nachgerechnet. |
| Kavität | Aus dem archivierten 65²-Geschwindigkeitsfeld und den diskreten Wand- und Flussmatrizen wurden die drei Wandmaxima erneut berechnet. Der Wert entspricht 0,22449 roh, 0,37603 nach reiner Flussprojektion und rund 4,4·10⁻¹⁶ nach gemeinsamer Projektion. |
| Grundwasser | In der dokumentierten Bandbreitenreihe wurden die acht Quellrichtungen sowie die bestandenen Fälle für jedes Band nachgezählt. Für das volle Fourier-Band beträgt der größte Score 0,728842. |
| C05 | Die 456 Archivzeilen wurden ausgewertet. C05 besteht bei keiner der 57 Matrixeinstellungen. Im Zusatzversuch besteht derselbe LIQSS–BDF bei Quantenfaktor 8·10⁻⁶ in vier Läufen, mit größtem Budgetquotienten 0,262674. Bei 1,6·10⁻⁶ greift auf dem Versuchsrechner das Zeitlimit. |
| Software | 33 Standardprogramme, acht Bild- und Datentests sowie der C++20-Vertrag wurden ausgeführt. Die archivierten CPU-Zeiten der 456er-Reihe stammen aus dem ursprünglichen Lauf. |

[Laufbefehle und Rohprotokolle](rechenlabor/revisionspruefung/README.md) · [Bildregister](rechenlabor/bildpruefung/abbildungsverzeichnis.csv) · [Tabellen und Messnachweise](daten/messregister.csv)

## Historische Editionsprüfung v9.15

Christian Stenzel · Numerische Simulation dynamischer Systeme · 25. November 2026

Die vorangehenden Gutachten beziehen sich auf die Gesamtausgabe v9.14 mit 455 Druckseiten. Diese Ausgabe hat 469 Druckseiten, 18 Fachkapitel, die mathematischen Grundlagen, vier Anhänge, 83 Abbildungen und 80 Tabellen. Alle 40 bestätigten Arbeitsaufträge tragen einen Zielanker in der Druckfassung. Die Freigabe gilt für diese redaktionelle Umsetzung. Die Reichweite der experimentellen Bestätigung steht bei jeder Studie.

| Gegenstand | Prüfweg und Ergebnis |
|---|---|
| Redaktion | Für jede der 40 IDs Ausgangsstelle, Auftrag und neue Druckseite abgeglichen. Die 34 Einzelentscheidungen zum Zweitgutachten und die acht ergänzenden Prüfungen bleiben separat nachvollziehbar. |
| Neu gesetztes Buch | Zweifacher XeLaTeX-Lauf mit aufgelösten Verweisen. Alle 80 Tabellen und 40 Arbeitsaufträge haben ein PDF-Ziel. Die Kapitelreihenfolge und der letzte gedruckte Folio wurden geprüft. |
| Abbildungen | Die 83 Bildunterschriften wurden ihrer Druckseite und den SHA-256-Prüfsummen beider Bilddateien zugeordnet. Beim Fühler, bei CP1/B und beim dynamischen Gittervergleich wurden die neu gestalteten Seiten visuell geprüft. |
| Software | 33 Lehrprogramme erfolgreich ausgeführt. Acht Bild- und Datenregressionstests bestanden. Der abgedruckte C++20-Code läuft mit strikten Compilerwarnungen. Die Python-API weist die beiden ungültigen Beispiele zurück. |
| Dynamik | Zwei zusätzliche 64/16/16-Aufteilungen je Modellfamilie neu gerechnet. Zwei 421²-Kavitäten aus erneuerten 65²-Startfeldern integriert. Bei beiden stimmen die archivierten letzten Geschwindigkeitsfelder komponentenweise überein. |
| Grundwasser und DAE | Sechs Bandbreiten, drei Gitter mit je zwei Quellformen. Die IDAS-Wiederholung über 149 Übergänge stimmt im protokollierten JSON mit dem bisherigen Resultat überein. |
| Gittertransfer | Alle 112 Vergleiche derselben Kandidaten gegen die unabhängig neu gerechnete 65²-Referenz wiederholt. Eingaben und Kombinationen sind im Revisionslabor dokumentiert. |

Die wichtigsten Dateien sind [Umsetzungsliste](daten/aenderungen_v9_15.csv), [Ergebnisregister](daten/messregister.csv), [Prüfumfang](daten/pruefumfang_v9_15.csv) und [Laufbefehle](rechenlabor/revisionspruefung/README.md).

## Historische Berichte zur jeweiligen Ausgangsfassung

Die folgenden Seiten- und Bildverweise gehören zu den genannten früheren Revisionen.

# Prüfung der Erweiterung v9.14

Christian Stenzel · 25. November 2026

Die fünf neuen Lehrseiten verbinden je einen vollständigen Operatorversuch mit der unabhängigen Referenz, den Grenzen des Trainingsbereichs und den klassischen Vergleichsmodellen. Die drei neuen Abbildungen stehen auf den Seiten 234, 338 und 339. Das aktualisierte Buch umfasst 455 Seiten und 82 Abbildungen. Die 875 Lesezeichen und 1 009 Links im Buch sowie alle 82 Bildziele im 86-seitigen Atlas wurden geprüft. Die vorhandenen Lesezeichen bleiben in ihrer bisherigen Reihenfolge. Alle Druckschriften sind eingebettet.

Die [Einzelmessungen](rechenlabor/cp_dynamik/README.md) umfassen 371 Tests der sieben kompakten Kerne und 134 Tests der Vergleichsmodelle. Sechs automatisierte Testgruppen prüfen unter anderem Nominalwerte, Kausalität, Nullantwort, Feldfehler, Wiederherstellung aus Gewichten und die beiden Benutzerschnittstellen. Nach vollständiger Wiederholung aus dem entpackten Rechenlabor sind alle vier numerischen Einzelwerttabellen, die vier Fehlerprotokolle sowie sämtliche Zahlen in den sechs Daten- und Gewichtspaketen identisch. Die 32 bestehenden Python-Prüfprogramme bestehen ebenfalls. Drei Referenzfelder aus den bisher vorhandenen C++-Betriebsarten stimmen bytegenau mit der vorherigen Fassung überein. Die [aktuelle Seitenzuordnung](rechenlabor/bildpruefung/abbildungsverzeichnis.csv) gilt für die vollständige Ausgabe v9.14.

## Historischer Befund zur Ausgabe v9.13

# Fachlektorat der Gesamtausgabe

**Numerische Simulation dynamischer Systeme · Christian Stenzel · Revision v9.13 · 24. November 2026**

## Vergleich mit der tatsächlich veröffentlichten Ausgabe

Geprüft wurde die gesetzte Ausgangsfassung v9.12 mit 441 Seiten und 70 Abbildungen. Alle Bildnummern wurden am Ort der tatsächlich gedruckten Bildunterschrift gelesen und gegen die zugehörige Grafik geprüft. In v9.13 stehen 79 Abbildungen auf 450 Seiten. Die 70 übernommenen Motive sind vollständig enthalten. Das [seitenbezogene Verzeichnis](rechenlabor/bildpruefung/abbildungsverzeichnis.csv) enthält für jede Abbildung ihren Befund, ihr Dateipaar und dessen SHA-256-Prüfsummen. Die Zahlen in der folgenden Tabelle bezeichnen Seiten der Revision v9.13.

| Gegenstand | Befund und Änderung | Druckseite |
|---|---|---:|
| D.1, Lastpuls und Bolus | Im Ausgangs-PDF standen die Winkelachse und das graue Pulsfenster links, die Konzentration rechts. An den vorhandenen Daten wurden A/B, Titel und Abszissen präzisiert. | 432 |
| D.2, Saite | Das farbige nominelle Raum-Zeit-Feld stand links, die beiden Sensorkurven für die neue Anregung rechts. Die 5-m-Position und die Einheit Meter sind jetzt explizit. | 434 |
| 16.6 und 16.8, Ghia-Profile | In beiden Ausgangsbildern war die Horizontalkomponente links. Ihr Achsentausch zwischen den Abbildungen erschwerte das Vergleichen. Beide zeigen jetzt links u/U gegen die vertikale Koordinate mit der Höhe auf der Ordinate. Rechts liegt v/U über der Breite. | 320, 332 |
| 1.1, 1.2 und 1.3 | Der Federwagen, das bisher unnummerierte RC-Schaltbild und das Euler-Bild sind durchgehend nummeriert. Beide Euler-Teilbilder sind im Ausgangs-PDF nachgewiesen. | 29, 38, 44 |
| 17.1 und 18.1 | Der doppelte Bezeichner war im PDF vorhanden. 17.1 bleibt die C19R-Messplanung. Der Statusbalken der 456 Rechnungen heißt nun 18.1. | 339, 363 |
| 3.1, 3.3, 5.1 und 9.5 | Alle vier Ausgangsgrafiken sind im gesetzten Buch vorhanden, darunter beide Teile von 5.1. Die Manuskripte enthalten nun durchgängig direkt aufgelöste Bildpfade. | 71, 86, 115, 221 |
| 9.6, 11.1 und 14.1 | Die überprüften Originale sind ein Balkendiagramm, die beiden Zeitsichten auf die Hysterese und eine C13-Lastpulsdarstellung. Ihre Vektorobjekte sind auch im Prüfkatalog gezählt. | 227, 247, 289 |
| 7.1 und 8.1 | Auf der Gitterachse der Wärmeleitung erscheinen ausschließlich 8, 16, 32 und 64. Der D2Q9-Titel „Eingänge am Deckel“ endet vollständig innerhalb des Satzspiegels. | 155, 166 |
| 16.1, 16.4 und 16.10 | Die bisherigen Karten enthalten tatsächlich 17 × 17 Knoten und 15 × 15 bewertete Innenzellen. Das neue Vergleichsbild zeigt unter anderem eine neu gerechnete 257 × 257-Referenz zum selben frühen Zeitpunkt. Die vier Rastergrößen der neuen Tafel sind im PDF direkt überprüft. | 310, 318, 334 |

## Neun neue Abbildungen

Die Entscheidungslogik in Kapitel 10 besitzt ausführbare Grenzfallproben. C05, C12, C09 und C21 werden aus den Modellgleichungen bzw. Ereignissen erneut berechnet. Für C19R sind sowohl feste äußere Zellmitten als auch feste Gebietsflächen erfasst. Das D2Q9-Anlaufmodell stimmt auf dem 17er-Gitter in allen neun Populationen bis auf höchstens 1,56 · 10⁻¹⁵ mit der skalaren Projektimplementierung überein. Das Feld auf 257 × 257 Knoten wurde mit 256 Zeitschritten neu berechnet. Die Fehlerfelder der Fourier-Korrektur auf 65² und 421² Zellen verwenden die gespeicherten gepaarten Vorhersagen und Referenzen. Die Grenzen der zeitlichen und stationären Vergleichbarkeit stehen auf der Bildseite.

* S. 243, Abbildung 10.2. Ereignis- und Budgetprüfung eines Laufs
* S. 253, Abbildung 11.2. C05 · Phasenbahn der Hysterese
* S. 263, Abbildung 12.3. C12 · Kugelmittelpunkte und Impulsweitergabe
* S. 281, Abbildung 13.2. C21 · Diodenfalte und Betriebsbahn
* S. 292, Abbildung 14.3. C09 · Zwei Pegel und gehaltene Pumpenspannung
* S. 307, Abbildung 15.3. C19R · Quelle, Brunnen und Gitterkonvention
* S. 334, Abbildung 16.10. CP2 · Nativer Anlauf und Fehler auf feineren Gittern
* S. 365, Abbildung 18.2. Aufwand und Fehler mit acht Pareto-Fronten
* S. 366, Abbildung 18.3. Leistungsprofile für 57 feste Konfigurationen

Das Aufwand-Genauigkeits-Diagramm gewinnt 373 numerische Messpaare aus der 456er-Reihe. 222 davon bestehen, 151 überschreiten das Budget. 46 Zeitlimits, 20 Ereignisabweichungen und 17 Solverfehler bleiben als eigene Kategorien sichtbar. Alle 57 festen Einstellungen und alle acht Modellfenster gehen in den Nenner der Leistungsprofile ein. C05 hat in dieser Reihe keinen bestandenen Lauf. Die separaten Radau- und BDF-Rechnungen aus Kapitel 11 sind an ihrer Originalstelle beschrieben.

## Abnahme

Die 79 Nummern wurden in Master, Einzelkapiteln und gesetztem Buch der Reihe nach abgeglichen. Jede Bildquelle ist einmal im eigenständigen Master eingebettet. Geprüft wurden auch die Existenz aller Kapitelanker, fortlaufende Nummern, PDF-Seiten, eingebettete Schriftarten und gültige Linkziele. Die vollständige Ausgabe hat 870 Lesezeichen und 997 Links. Der Bildatlas enthält vier Registerseiten, 78 Originalbuchseiten mit 79 Abbildungen und eine Befundseite. Alle Bildeinträge führen zur richtigen Originalseite. Der Atlas wurde über den mitgelieferten Aufruf einschließlich aller Sprungziele reproduziert.

Aus dem eigenständig entpackten Labor wurden die zehn Messdateien, die neun neuen Grafikpaare und die sechs geänderten Grafikpaare bytegleich reproduziert. Acht neue Regressionstests und alle 32 bisherigen Python-Lehrprüfungen liefen erfolgreich. Der C++20-Schnittstellentest und der unabhängige Vergleich über 481 rationale Zielintervalle wurden erneut ausgeführt. Die archivierten Zeiten wurden ausgewertet. Die Berechnungen für diese Revision enthalten keine neue Laufzeitmesskampagne der 456 Konfigurationen.

## Archiv der früheren Prüfungen

Die folgenden Berichte und Seitenangaben gehören zur jeweils genannten damaligen Fassung.

# Fachlektorat der Gesamtausgabe

**Numerische Simulation dynamischer Systeme · Christian Stenzel · Revision v9.12 · 24. November 2026**

## Durchgerechneter Transfer

27 endliche Messaufgaben mit insgesamt 352 verschiedenen Szenarien wurden aus den Referenzmodellen erzeugt und feldweise gegen die gespeicherten Messverträge geprüft. Für C19R wurden die gerichteten Green-Gewichte und 5 101 unabhängige Prüfquellen neu ausgewertet. Die Kernmatrix enthält 196 Kombinationen. Die 38 171 Vorhersagen besitzen jeweils einen Rohfehler, einen Nachweis für Ereignis und Zielwert und ein abschließendes Ergebnis nach Prüfung. Der Acht-Sekunden-Sensor, der Einzelzeitschritt und das vollständige Saitenfeld sind im Text jeweils kenntlich gemacht.

Bei den endlichen Aufgaben gelten die Freigaben ausschließlich relativ zum vollständigen Referenzkatalog. Die Lernregel benötigt 538 Ablesungen, die gierige Regel 535, das zulässige Optimum 528. Ohne die vier ergänzenden Messkanäle bleiben elf Aufträge in vier Benchmarks durch ununterscheidbare Szenarien offen. Bei C19R liefern 5 079 von 5 101 Quellen direkt einen dualen Nachweis, 22 werden über die scharfe Intervallrechnung freigegeben. Der Hauptversuch verwendet zwei Optimierungsstarts mit jeweils höchstens 200 Iterationen. Der vierfach längere Kontrollversuch umfasst drei Aufgaben und alle sieben Kerne.

## Druck, Code und Abbildungen

Die Ausgabe hat 441 Seiten, 70 Abbildungen, 861 Lesezeichen und 987 Link-Anmerkungen. Die 19 neuen Abbildungen sind im Text verankert und in einem eigenen Bildatlas mit anklickbarem Verzeichnis gesammelt. Jede der 28 Messaufgaben erscheint im Kernvergleich und in einem eigenen oder gemeinsam beschrifteten Messbild. Die C04-Spuren wurden gegen die unbeobachtete Implementierung geprüft. Die C10-Vergabe wurde direkt der Referenzsimulation entnommen. Die 19 Grafiken sind im Rechenlabor reproduzierbar. Die skalierbaren Quellen und Druckfassungen liegen bei.

Acht eigens ausgeführte Tests prüfen unbekannte Beobachtungen, verlorene Trennmöglichkeiten, beliebige duale Multiplikatoren, die Gültigkeitsgrenze des endlichen Katalogs, die C04-Blockade, die Vollständigkeit der 196 Vergleiche und das Laden eingefrorener Modellgewichte. Die 32 bestehenden Lehrrechnungen und der bestehende C++20-Solververtrag wurden erneut ausgeführt. Die bestehenden regulären und verschärften Saiten- und Brunnenversuche lieferten beim unabhängigen Wiederholungslauf wieder die publizierten Einzelergebnisse. Alle 14 Mess- und Modelldateien sowie die 38 Grafikdateien (19 Paare aus SVG und PDF) wurden aus dem eigenständigen, frisch entpackten Rechenlabor bytegleich reproduziert. Auch die zehn bisherigen Eigenschaftstests und der unabhängige C++20-Vergleich über 481 rationale Zielintervalle wurden erneut erfolgreich ausgeführt. Sämtliche Schranken der neuen endlichen und kontinuierlichen Versuche wurden gegen die zugehörigen Referenzen geprüft.

## Seiten der neuen Versuche

* S. 110, Abb. 4.2. 4.6 · Was die Rückprojektion einer Kreisbahn erhält
* S. 134, Abb. 5.5. 5.8 · Fünf gleichzeitige Anforderungen im Ereigniskalender
* S. 148, Abb. 6.2. 6.6 · Die Abstände zweier Quantisierungsereignisse vorhersagen
* S. 177, Abb. 8.3. 8.7 · Wo im Wirbel eine gelernte Korrektur fehlt
* S. 229, Abb. 9.7. 9.33 · Die Reichweite eines gelernten Fehlernachweises sehen
* S. 231, Abb. 9.8. 9.35 · Wo ein Netzvorschlag eine direkte Freigabe erhält
* S. 287, Abb. 14.2. Lesebeispiel · Was zwei Abtastreihen über ihre Zielgrößen verraten
* S. 301, Abb. 15.2. Lesebeispiel · Einen vorgeschlagenen Brunnenwert über das ganze Quellenintervall prüfen
* S. 327, Abb. 16.9. Bildversuch · Eine Reflexion im Raum-Zeit-Bild verfolgen
* S. 344, Abb. 17.2. 17.15 · Wo eine andere Messreihenfolge tatsächlich Arbeit spart
* S. 361, Abb. A.1. Bildversuch · Warteschlange und drei parallele Modellaufträge
* S. 363, Abb. A.2. Bildversuch · Vom ersten Messwert zum späteren Ergebnis
* S. 366, Abb. A.3. Bildversuch · Schaltzeit, Aufenthaltszeit, Winkel und Transit
* S. 369, Abb. A.4. Bildversuch · Gleicher Messkanal, verschiedene Zielgrößen
* S. 373, Abb. A.5. Bildversuch · Bewegung und Bestände aus einem frühen Kanal
* S. 376, Abb. A.6. Bildversuch · Modellbestand, Kraft, Durchlaufzeit und Kontakt
* S. 380, Abb. A.7. Bildversuch · Drei verschiedene Bedeutungen eines Sensors
* S. 383, Abb. A.8. Bildversuch · Den Wartekreis von C04 lesen
* S. 387, Abb. A.9. Bildversuch · Wer beim gleichzeitigen Zugriff gewinnt

## Prüfberichte früherer Revisionen

Die folgenden Berichte dokumentieren die jeweils genannten früheren Fassungen. Ihre Seitenzahlen gehören zur damaligen Druckausgabe.

# Fachlektorat der Gesamtausgabe

**Numerische Simulation dynamischer Systeme · Christian Stenzel · Revision v9.11 · 24. November 2026**

## Ausgeführte Verfahren in Kapitel 9.27–9.32

Auf S. 219–224 werden die Implementierung, eine Handrechnung für zwei Knoten, die getrennte Kalibrierung und die unabhängigen Messungen ausgeführt. Die Zugänge in Kapitel 9, 16, 17 und 18 sind im PDF verlinkt. Die veröffentlichten Vergleichszahlen gelten jeweils für den Zweipuls-Brunnen bzw. einen diskreten Newmark-Schritt mit festen Saitenenden.

Der Trainingslauf verwendet 1 008 Brunnenkonstellationen, 882 Saitenkonstellationen für die Aktionswahl und 56 adjungierte Saitenprobleme für den dualen Filter. Der reguläre Test mit festgehaltenen Gewichten umfasst 486 Brunnen- und 432 Saitenaufträge. Alle erhalten einen Wert im vereinbarten Budget. Bei den zusätzlich geprüften 162 Brunnenaufträgen mit vergrößerter Messunsicherheit bleiben 121 offen. Zu jedem offenen Auftrag belegt ein Paar zulässiger Quellen die unzureichende Information. Bei 48 verschärften Saitenaufträgen übernimmt immer die klassische Bandlösung.

Auf dem regulären Saitensatz ergeben sich 130 unmittelbar freigegebene grobe Vorschläge mit gelerntem Filter und dualer Korrektur. Der analytische Filter gleicher Grade erreicht 171 und der Nullzeuge null. Bei derselben festen Handlungsfolge übernimmt die Bandlösung 106-mal mit gelerntem, 33-mal mit analytischem und 420-mal mit Nullzeugen. Auf dem regulären Brunnensatz liegen die mittleren Aktionseinheiten der gelernten Auswahl bei 17,66, der besten im Training gewählten festen Reihenfolge bei 19,78 und der analytischen Intervallregel bei 17,32. Die direkt gemessenen CPU-Zeiten und die Kostenannahmen stehen getrennt im Buch und im Rechenlabor.

Die zehn Eigenschaftstests prüfen unter anderem unzugängliche zukünftige Messwerte, die Ausführung ohne unabhängige Referenzquadratur, widersprüchliche Ablesungen, das offene Ergebnis bei zu engem Budget, Spiegelung und die Fehlergrenze für beliebige und absichtlich verfälschte Zeugen. Der separate C++20/GMP-Prüfer wurde mit strengen Compilerwarnungen gebaut. Für alle 480 regulären und verschärften Saitenaufträge sowie einen Großzahlfall ergeben sich dieselben rationalen Intervalle wie in Python. Vier ungültige C++-Eingaben wurden zurückgewiesen.

Das eigenständige Versuchspaket und das Buchquellenpaket enthalten identische Programm- und Messdaten. Nach frischem Entpacken wurden Modellgewichte, Einzelentscheidungen, Kennzahlen und Vektorabbildung reproduziert. Die Laufzeitdateien enthalten die tatsächliche Buchmessung. Die v9.10-Versuche wurden nach der Trennung der optionalen Referenzquadratur ebenfalls erneut ausgeführt und ihre numerischen Ergebnisse byteweise verglichen.

## Projektion und A-posteriori-Fehlerabnahme in Kapitel 9

Die Abschnitte 9.17–9.26 (S. 209–218) verbinden die Begleitstudie v9.8 mit drei neuen Gegenproben. Die Buchseite 211 ordnet vier Zahlenpaare ihrer Vergleichsrechnung, Zielgröße und Auflösung zu. Die vier Versuche der Begleitstudie wurden mit ihren Daten erneut ausgeführt. Ihre Ergebnistabelle ist bytegleich mit dem Original. Der PDF-Text der Studie und die zur Wiederholung benötigten Quellen stehen im Unterordner `rechenlabor/physik_residual/v98/`.

Für die CP2/2-Kavität (S. 212–213) wurde für ein gehaltenes Referenzfeld bei Re=100 auf 65 × 65 Zellen das affine Modell mit sieben Korrekturvarianten und der D2Q9-Referenz verglichen. Ein ganzzahliger Zeuge belegt, dass die zunächst versuchten Fluss- und Wandgleichungen an den Deckelecken unverträglich sind. Mit der angegebenen Eckvorschrift erfüllen die projizierten Felder die gemeinsamen Nebenbedingungen bis auf Rechengenauigkeit. Beim Fourier-Feld steigt der Fehler im Innern dabei von 1,173 auf 2,151 %. Beim D2Q9-Feld verschiebt sich der Innenzustand um 1,894 %. Die Messung gilt für diese Gitteroperatoren an diesem Betriebspunkt.

Der C15-Versuch (S. 214–215) akzeptiert alle 2 880 nominalen Schritte und erkennt in allen sechs Testverläufen die gezielte Umverteilung trotz richtiger Summe und positiver Mengen. Bei verdreifachtem Austauschkoeffizienten übernimmt die klassische Rechnung 2 872 Schritte. Die mit rationaler Arithmetik bestimmte globale Fehlerschranke bleibt innerhalb des Budgets. Das Referenzfeld wird erst im Anschluss verwendet. Auf der dokumentierten CPU kostet der hybride nominale 480-Schritt-Lauf im Median 74,49 ms, die ebenfalls abgesicherte klassische Rechnung 51,83 ms.

Bei C19R (S. 216–217) wurden je Brunnen 297 Verläufe bei vorgegebenen Gerätegrenzen auf dem neuen Zweipulsmodell geprüft. Bei 5 m genügt die gröbere Ablesung. Bei 5,25 m ist die zweite Ablesung für 288 der 297 Verläufe nachweislich zur Einhaltung des Ein-Prozent-Vertrags erforderlich. Das Labor gibt die beiden nach der ersten Ablesung noch möglichen Eingaben an, mit denen der Unmöglichkeitsnachweis geführt wird. Das vorangegangene allgemeine C19R-Experiment von Kapitel 17 verwendet andere Eingabe- und Messannahmen.

Abschnitt 9.22 leitet einen nachprüfbaren dualen Fehlernachweis für eine diskrete lineare Zielgröße her. Abschnitt 9.26 formuliert die lernbare Wahl der nächsten Messung oder Rechnung als Forschungsfrage mit Vergleichsverfahren, Fehlerbudget und vollständiger Kostenzählung. In dieser Ausgabe folgen darauf Implementierung und Endauswertung beider Vorschläge. Einleitung und Schluss von Kapitel 9 sowie die Schlüsse der Kapitel 16–18 stellen den Bezug zu den Versuchen her.

Die drei neuen Versuche sind aus dem fertigen Quellenpaket reproduzierbar. Dabei wurden die einzelnen Messdaten, beide SVG-Abbildungen, beide Vektor-PDFs und der generierte TeX-Quelltext byteweise mit den Buchdateien verglichen. Zeiten werden in einer eigenen Datei mit ihren Einzelmessungen dokumentiert. Die neu gesetzten zehn Seiten und die geänderten Kapitelübergänge wurden anhand des erzeugten PDFs geprüft.

## Zielgerichtete Messplanung in Kapitel 17

Kapitel 17 (S. 318–327) untersucht einen Messauftrag je C-Familie und jede der sechs CP-Teilaufgaben. Alle 28 Aufgaben wurden mit festem Fehlerbudget und dokumentierten Ablesungen erneut aus dem entpackten Quellenstand gerechnet. Ohne Zusatzkanäle sind 24 Verträge in allen zugehörigen Verläufen erfüllbar. In neun davon benötigt der adaptive Plan im ungünstigsten Fall weniger Ablesungen als der gleichmäßige. Bei C10 und CP1/A spart die adaptive Wahl auch gegenüber dem besten festen Plan jeweils eine Ablesung im ungünstigsten Fall.

Für C01, C02, C03 und C13 enthält das Labor je ein unentscheidbares Paar unter den ursprünglichen Ablesungen. C01 liest zusätzlich die Clustergröße m bei 3 s, C02 verwendet das Steuerprotokoll, C03 liest u4 bei 18 µs und C13 die Katzposition bei 12 s. In allen vier Erweiterungen sind sämtliche Katalogfälle entscheidbar. Die adaptive Ablesezahl ist dann höchstens 1, 2, 1 beziehungsweise 1.

C19R weist für exakte Zählerstände eine Schranke über die kontinuierliche Menge der Raten aus. Für die kleinste feste zielgerichtete Ablesezahl 13 wurde zusätzlich die Unzulänglichkeit aller 50 388 Pläne mit zwölf Ablesungen überprüft. Die adaptiven Ablesezahlen stammen aus 5 101 Prüfraten. Der übrige Vergleich gilt für die angegebenen Referenzverläufe und die festgelegte Auflösung der Messkanäle. Die Protokolle, beide Abbildungsformate und der TeX-Quelltext ließen sich aus dem entpackten Paket bytegleich reproduzieren.

## Gemeinsame Auswertung in Kapitel 9

Die Abschnitte 9.12–9.16 (S. 204–208) führen den Vergleich von der Eingabe und der Referenz über das Fehlerbudget bis zur Gegenprobe. Der Haupttext bespricht alle zehn Teilaufgaben anhand der Schalt- und Regelkreise, der Zeitreihen und der räumlichen Felder. Am C19R-Doppelpuls ergibt die ungerundete Auswertung aus Feld, Brunnen und Bilanz einen Laplace-Score von 15,122744853. Die zugehörige Messmatrix steht auf S. 406. Einleitung und Schluss von Kapitel 9 greifen den Prüfaufbau auf. Kapitel 16, Kapitel 18 und Anhang D verweisen auf die Auswertung. Die Daten und Rechenprogramme dieser Operatorstudie stammen aus Revision v9.7.

## Vollständiger Operatorvergleich

Anhang D.15–D.18 steht auf S. 405–408. Die folgende Auswertung beruht auf der Rechenstudie von v9.7. Die Studie rechnet alle zehn im Buch mit FNO dokumentierten ARGESIM-Teilaufgaben mit FNO, LNO, WNO, HNO, RNO, WLNO und FMNO. Das Rechenlabor enthält 70 verschiedene Paarungen sowie zusätzliche Gegenproben. Für jede Aufgabe werden dieselben Trainings- und Prüfdaten, Beobachtungspunkte und Fehlergrenzen verwendet. CP2 wurde auf den in v9.6 definierten Referenzen erneut gerechnet. Auch die ursprünglichen klassischen und FNO-Läufe der acht übrigen Aufgaben wurden wiederholt.

C05 und C09 bestehen mit allen sieben Varianten. C07 besteht mit der Mittelpunktsbasis in allen zwölf Fällen. Die Euler-Basis besteht abhängig von der Korrektur null bis drei Fälle. Beim C18-Kraftsignal ist der beste direkte RMSE 0,04567 mit FMNO, der beste RMSE für die Korrektur des ARX-Modells 0,04266 mit FNO. Der frühe Teil der Ausgabe bleibt bei geänderter Zukunft in allen kausalen Kontrollen unverändert.

Bei C13 bestehen mit vollständiger Auslese der Bandmerkmale fünf Familien, bei C15 vier. Der verkleinerte Fit und ein Fourier-Modenschnitt begrenzen den Rang des identifizierbaren Faltungskerns. Bei C19R und CP1/C verfehlen alle sieben hier gerechneten Korrekturen auf den groben Modellen die Budgets. Die früheren vollständigen Fourier-Läufe bestehen beide Aufgaben. Bei CP2/2 erfordert die Radon-Lehrvariante auf dem feinsten Gitter ein Referenzfeld mit Flussprojektion für beide Prüfprofile. Bei der idealen CP2/3-Saite erfüllen alle sieben Ausgaben das Ziel.

Der Kapiteltext nennt den Fehlervertrag und die betrachtete Variante. Das Quellenpaket enthält die CSV-Matrix sowie die Werte, Vorhersagen und Koeffizienten der einzelnen Läufe. Die Codes prüfen die sieben Fenstermatrizen gegen die PyTorch-Schichten, die Kausalität und die Rekonstruktion bekannter Faltungs- und Feldkoeffizienten. Der Lauf aus dem entpackten Paket reproduziert die Felder und die Messwerte der vollständigen Studie innerhalb der Vergleichstoleranzen.

## Alternative neuronale Operatoren in CP2

In Kapitel 9, S. 200–203, stehen Herleitung und Lernregel der sieben vergleichbaren PyTorch-Varianten. Kapitel 16, S. 310–316, enthält deren getrennte Saiten-, Front- und Kavitätsversuche. Anhang C, S. 386–388, dokumentiert das Rechenlabor, die Messkosten und die Amortisation. Die Schichten verwenden dieselbe kleine trainierbare Mischmatrix. Der Befund gilt für diese Lehrimplementierungen.

Auf 501 Knoten besteht jede Variante für fünf Anfangsprofile zu beiden Messzeiten den 1-%-Vertrag. Die exakte d’Alembert-Basis lässt im idealen Modell ein Zielresiduum von null. Im getrennten dispersiven Modell reichen die maximalen Feldfehler von rund 0,55 bis 0,86 Prozent, verglichen mit rund 1,77 Prozent für die ungestörte Basis allein. Die Reihe mit 8192 Moden, ein glatter Energietest und das Spiegelpaar ergänzen den Feldvergleich. Der Burgers-Versuch rekonstruiert eine bekannte Entropiefront. Er vergleicht Überschwingen und Frontfehler unter den jeweiligen Darstellungsgrenzen.

Bei Re=100 auf 421 Quadratgitterzellen pro Seite bestehen das affine Modell und sechs Hybride ihre beiden Prüffälle direkt. Der Radon-Hybrid besteht nach einem Kalibrierfeld mit Flussprojektion. Bei Re=140 auf dem 65er-Gitter bestehen alle Varianten und das affine Modell nach zwei Ankerfeldern mit Flussprojektion. Das reine Nachpassen der Mischgewichte erfüllt in den gemessenen Re=140-Fällen das gemeinsame Budget bis zum vierten Kalibrierlauf nicht. Die Ghia-Werte werden unabhängig vom Training ausgewertet. Auf dem feinsten nominalen D2Q9-Lauf endet die Rechnung an der Zeitgrenze mit einer relativen Änderung über das letzte vollständige Messintervall von rund 0,000104.

Die PyTorch-Schnittstelle ist für beide Raumdimensionen und alle Transformationen getestet. Das C++20-D2Q9 stimmt nach 1, 7 und 16 Schritten mit dem früheren skalaren Python-Beispiel bis auf Rundung überein. Newmark und Verlet wurden gegen ihre voll diskreten Eigenmoden geprüft. Aus dem entpackten Quellenpaket wurden beide Auswertungsskripte ausgeführt. Dabei wurden die enthaltenen Referenzfelder, die vorhergesagten Felder und die Mischgewichte abgeglichen. Die Laufzeitmatrix stammt von einer CPU. Eine CUDA-Messung hängt vom verfügbaren Gerät ab.

## FNO-Transfer in Anhang D

Die ursprüngliche Transferstudie steht auf S. 390–404. Der Katalog erfasst alle 24 ARGESIM-Familien des Referenzkatalogs und führt die sechs Aufgaben der Parallelfamilien einzeln auf. Für 28 Katalogeinträge sind die zu prüfenden Ausgaben und der jeweilige Befund hinterlegt. Die sechs neuen Rechnungen betreffen jeweils einen benannten Ausschnitt. Der Katalog verknüpft außerdem die vier vorhandenen FNO-Versuche.

Für C05, C07, C09, C13, C15 und CP1/C liegen sechs reproduzierbare Versuche neben den klassischen Auswertungen. Die jeweils vollständigeren FNO-Varianten erfüllen die gemeinsam festgelegten Fehlerbudgets in den 52 vorgesehenen Fällen. Klassische Verfahren erfüllen diese Budgets ebenfalls. Beim Stiftpendel besteht allein die FNO-Korrektur auf den Mittelpunktsfenstern 12 von 12 Prüffällen, während die Korrektur auf Euler-Fenstern 0 von 12 besteht. RK4 hat den kleineren größten Schaltzeitfehler und ist schneller. Die Trainingsläufe für C07 und C09 endeten an der Grenze von 600 Iterationen.

C13, C15 und CP1/C enthalten zusätzlich Versuche mit begrenzten Fourier-Moden. Diese Varianten verfehlen alle zugehörigen Prüfbudgets. Für die CP1-Saite beträgt der relative Innenfeldfehler bei einer neuen Anregung von 2,6 rad/s rund 96 %. Der Randfehler nach Projektion auf die sechs Trainingsfrequenzen liegt bei rund 97 %. Die Wiederholung aus dem entpackten Paket reproduziert die gespeicherten NumPy-Arrays byteweise und die Ergebniswerte ohne Zeitmessungen. Gegenüber den passenden vorbereiteten klassischen Kontrollen ergibt sich in diesen Versuchen kein nachgewiesener Rechenzeitvorteil.

## Parallele FNO-Vergleiche in Anhang C

Anhang C steht auf S. 378–389. Die Gegenproben zu C19R verwenden acht zurückgehaltene Quellverläufe, eine nachgerechnete Punktreferenz, ein Feldbudget und eine Stoffbilanz. Die lineare Fourier-Schicht mit allen Moden und der vorberechnete Green-Operator bestehen alle acht Fälle mit einem maximalen Score von 0,729. Der FNO mit begrenzten Moden und die finite Volumenrechnung auf dem geprüften Gitter verfehlen das gemeinsame Ziel. Der erneute RK4-Lauf mit halber Schrittweite trennt den Zeitanteil vom räumlichen Fehler.

C18 vergleicht publizierte und neu identifizierte ARX-Koeffizienten, die bestehenden statischen und rekurrenten Netze sowie zwei kausale FNO-Varianten. Die rekonstruierten Veröffentlichungskurven haben je 2 000 Werte. Der erste Muskel dient der Identifikation, der zweite der Prüfung. Auf der zweiten Kurve beträgt der RMSE 0,04491 für das direkte FNO, 0,04833 für den ARX-FNO-Hybrid und 0,11732 für das neu identifizierte ARX. Der ausführbare Eingang akzeptiert auch zwei getrennte Aufzeichnungen im 100-Hz-Format. Die Buchzahlen beziehen sich auf die Kurvenrekonstruktion. Das Quellenpaket enthält die Eingabekurven, Gewichte, Vorhersagen und gemessenen Fehler sowie die Git-Blob-Kennungen des getrennt ausgeführten Vergleichs mit dem Bestandsmodell.

Die Prüfläufe kontrollieren die Green-Quadratur, FNO-Multiplikatoren, RK4-Massenbilanz, inverse FFT, Differenzengradienten und kausalen Zugriff auf die Eingabe. Beim Ändern der zweiten Signalhälfte bleiben alle Ausgaben der ersten Hälfte gleich. Die überprüfte Buchmessung verwendet Python 3.12.14, NumPy 2.3.5 und SciPy 1.17.0. Aus einem frisch entpackten Quellenpaket wurden die gespeicherten Gewichte, Referenzen und Vorhersagen reproduziert. Die zwei Abbildungen, Tabellen und internen Verweise des Anhangs wurden im Drucksatz geprüft.

## Einleitung, Kapitelrahmen und Forschungsstand

Die Einleitung des Buchs (S. 1) und Kapitel 18 (S. 328–340) folgen denselben drei Fragen nach dem Rechenauftrag, der Fehlerursache und der entscheidenden Gegenprobe. Die Synthese greift den Federwagen wieder auf und endet mit den übertragbaren Prüfschritten. Kapitel 1 bis 18 und der Grundlagenteil führen vom Einstieg per Link zum Schluss und zurück. Jeder Schluss beantwortet die Leitfrage, rekapituliert die Ergebnisse und ordnet sie im Abschnitt „Aktueller Stand der Forschung“ anhand ausgewählter Literatur bis November 2026 ein. Zum jeweiligen Lehrfall ist eine Frage formuliert, die eine weiterführende Untersuchung prüfen könnte.

Alle 18 Fachkapitel enthalten einen zusätzlich ausgeführten Rechen- oder Vergleichsschritt. Die neuen Handrechnungen wurden unabhängig überprüft. Sie illustrieren unter anderem, wie alte Defekte durch nachfolgende Schritte fortwirken, was ein kleines Newton-Residuum über den Zeitfehler verrät und wie sich ein unveränderter Stoffeintrag auf anders große Gitterzellen verteilt.

## Mathematischer Grundlagenteil

Der Einstiegsabschnitt belegt die Druckseiten 5–26. G.1 bis G.5 führen von Skalen, linearen Gleichungen und Taylorentwicklung zu Anfangswertproblemen und Fehlerfortpflanzung. G.6 bis G.9 vertiefen Nullstellen, Fixpunkte, räumliche Felder, Fourier-Analyse und Messdaten. Neun Verweise aus den Fachkapiteln führen zu den relevanten Grundlagen. Die Aufgaben stehen auf S. 22–23, die Lösungen beginnen auf S. 24.

`rechenlabor/grundlagen.py` prüft unter anderem die Rückrechnung des Fühlerüberschusses, die Taylor-Schranke, die beiden Eigenmoden, die gemessene Euler-Ordnung, die Nullstellenklammer, den Projektionsfehler, Aliasing und die Normalbedingung für den Messdatenfit.

## Prüfung von Drucksatz und Rechenlabor

Die überarbeitete Druckfassung enthält 414 A4-Seiten, 51 Abbildungen, 834 Lesezeichen und 921 Link-Anmerkungen. Alle Seiten wurden gerendert und auf Seitennummern und Textgrenzen geprüft. Für die Einleitungen und Schlüsse sind die Druckansichten, Überschriften und Querverweise kontrolliert. Alle Schriften sind eingebettet. Die 51 SVG-Abbildungen sind zusätzlich in der separat bereitgestellten Markdown-Ausgabe eingebettet.

| Kapitel | PDF-Seiten | Schluss und Forschung | Überarbeitete Fachinhalte |
|---:|---:|---:|---|
| 1 | 27–54 | 54 | Lokal und global Lipschitz, Wachstumsschranke, RC-Singularität und Ableitungswert. |
| 2 | 55–68 | 68 | RK4 mit Halbierung, FSAL-Zählung, Schrittprüfung und Hermite-Überschwingen. |
| 3 | 69–98 | 98 | Jacobi-Kosten nach Aufrufen und skalarer Arbeit, BDF-Stabilitätssektor und Neustart. |
| 4 | 99–110 | 110 | Index-1-Initialisierung, gedämpfte Newton-Korrektur, Rangverlust und RATTLE-Korrekturen. |
| 5 | 111–133 | 133 | Zwei gerichtete Durchgänge aus automatisch bestimmter Teilung, Filippov-Skizze. |
| 6 | 134–146 | 146 | QSS2-Termin mit Wurzelprodukt, absolute und relative Quanten, Kostenmodell. |
| 7 | 147–160 | 160 | CFL-Fußpunkt, Mass-Lumping am Zweiknotenelement, Vergleich FDM/FVM/FEM. |
| 8 | 161–174 | 174 | SI- und Gittergrößen, Relaxationszeit und Niedrig-Mach-Skalierung. |
| 9 | 175–225 | 225 | Dirichlet-Ränder, Physik-Layer, sieben Lehrvarianten, Physikverlust und Vergleich von zehn Teilaufgaben. Projektion, kausaler Zustand, Fehlerschranke und Wahl zwischen Messung und Ersatzrechnung. Neue quantitative Gegenproben zum gelernten Aktionsplan und zum dualen Sensorfilter. |
| 10 | 226–235 | 235 | Maximalscore und einzelne Messbudgets, Ereignisfolge als zusätzlicher Teil des Auftrags. |
| 11 | 236–244 | 244 | Dormand–Prince-Stabilitätsgrenze aus dem Stufentableau. Radau-/BDF-Archivzahlen im Versuchskontext. |
| 12 | 245–253 | 253 | Geometrische Summe bis zur Häufungszeit und Budgets für die Fortsetzung in Kontakt. |
| 13 | 254–270 | 270 | Orts- und Tangentialbindung am Stift sowie Neuinitialisierung der kartesischen Phase. |
| 14 | 271–279 | 279 | Bekannte Reglertakte und Pulsflanken als Solver-Grenzen. |
| 15 | 280–292 | 292 | Péclet-Zahlen 20, 10 und 5 auf den studierten Gittern. Zentrale und Upwind-Gegenrechnung. |
| 16 | 293–317 | 317 | Exakte Saitenreflexion, Biegesteifigkeit, Burgers-Front, Ghia-Vergleich, Reynolds- und Gitterwechsel. |
| 17 | 318–327 | 327 | Gleichmäßige, feste zielgerichtete und adaptive Pläne für 28 Messaufgaben, vier geprüfte Zusatzkanäle. |
| 18 | 328–340 | 340 | Sechsstufige Solver-Checkliste aus Auftrag, Modellform, Dynamik, Ereignissen, Gitter und Kosten. |

Alle 32 Python-Prüfprogramme mit Python 3.12.14 und aktiven Assertions bestanden. Der C++20-Vertrag wurde mit g++ 14.2.0, aktivierten Warnungen und Assertions übersetzt und ausgeführt. `pruefprotokoll.txt` hält den neuen Lauf fest.

Die bereits vorliegenden Datendateien stimmen byteweise mit dem aktuellen Quellenpaket überein. Die 456 Konfigurationen ergeben weiterhin 222 bestandene Läufe, 151 Budgetüberschreitungen, 46 Zeitlimits, 20 Abweichungen der Ereigniszahl und 17 Solverfehler. Die CP2-Trainings- und Inferenzzeiten stammen aus dem gespeicherten Messprotokoll. Für C05 zählt die neue Stabilitätsprobe Schritte eines fest gewählten Gitters. Die QSS-Zahl 2000 beschreibt das Verhältnis von Komponentenaktualisierungen im Lehrbeispiel.

## Prüfung der Ausgangsfassung v9

Im folgenden archivierten Teil beziehen sich Seitenzahlen, Abbildungszahl und Prüfprotokoll auf die Ausgangsfassung v9.

### A · Was die Bestandsaufnahme ergeben hat

Die bisherige Master-PDF umfasste 135 Seiten. Kapitel 1 bis 9 lagen als Volltext vor, die acht Methodenanwendungen und beide Anhänge als Fahrplan. Die gesonderten LaTeX-Kapitel des Autorenprojekts enthielten die fehlenden Herleitungen, Übungen, Lösungen, Datenblätter und Quellen. Sie sind mit der aktuellen Fassung von Teil I und seinen FNO-Versuchen zu einer fortlaufenden Gesamtausgabe verbunden worden.

Die kurze Angabe „14 Benchmarks“ bezeichnet den vertieften Teil des Katalogs. Anhang A weist alle 24 erfassten Familien aus. Im Messraster stehen acht Modellfenster mit je 57 Einstellungen. Die Statusprüfung hat zwei zusätzliche, bereits mit Zahlen befüllte Scorefelder bei abgebrochenen Zeitlimit-Läufen sichtbar gemacht. In Kapitel 17 und B.1 sind sie als Zeitlimit erläutert. Druckbezüge auf Seiten und Anlagen der früheren Einzelausgabe wurden auf die aktuelle Gliederung oder den fixierten historischen Versuchsstand umgestellt.

### B · Volltext und didaktische Prüfung

Die Gesamtausgabe hat **247 Seiten**. Im Folgenden steht bei jedem Kapitel, an welcher Beobachtung sich Herleitung und Programm prüfen lassen und an welcher Stelle die Aussage endet. In Teil I führen die Versuche vom Phänomen über die Gleichung zur Gegenrechnung. Teil II beginnt mit einem messbaren Auftrag und führt über Referenz und Fehlerbudget zur Diagnose. Die Katalogblätter verwenden sechs feste Fragen für den gezielten Vergleich. Die Seiten beziehen sich auf diese Gesamtausgabe.

| Kapitel oder Anhang | PDF-Seiten | Lehrgegenstand | Nachvollzogene Gegenprobe | Reichweite |
|---|---:|---|---|---|
| Kapitel 1 | 5–27 | Federwagen, RC-Kreis und Reaktionsmoden | Energie, Maschenresiduum, Existenzintervall und Moden mit unabhängiger Lösung. | Die Kreisbahn setzt normierte Phasenkoordinaten voraus. Die Kontraktionsschranke gilt lokal. |
| Kapitel 2 | 28–35 | Adaptiver Runge–Kutta-Schritt | Paardifferenz, Annahme oder Verwerfung und exakte Viertelung der Differenz beim Halbieren im Lehrpaar. | Die Paardifferenz schätzt den führenden lokalen Fehler des niedrigeren Verfahrens. |
| Kapitel 3 | 36–60 | Radau IIA und BDF | Verstärkungsfaktoren, Newton-Residuen, drei Radau-Stufen und C05-Phasenrechnung. | Stabilitätsgebiet, Lösungsfehler und Kosten der linearen Algebra haben verschiedene Maße. |
| Kapitel 4 | 61–68 | Gebundenes Pendel | RATTLE, konsistente Startwerte und unabhängiger Defekt der Beschleunigungsbindung. | Ein kleiner Lagefehler lässt einen unzulässigen Geschwindigkeits- oder Beschleunigungswert zu. |
| Kapitel 5 | 69–86 | Kontakt und Zeno | Dichte Ausgabe, doppelte Nullstelle im Schritt, gerichteter Reset, Saltation und Restflugzeit. | Die Genauigkeit der Nullstellensuche ist von der Güte des Schrittpolynoms und der Transversalität abhängig. |
| Kapitel 6 | 87–94 | Quantisierte Speicher | QSS1 mit zwei exakten Ereigniszeiten, gekoppelter Kalender und Fehlerschranke. | Eine Schranke für ein stabiles lineares Modell begründet keine allgemeine Stabilitätszusage für alle Quantisierer. |
| Kapitel 7 | 95–103 | Wärmestab und Stoffbilanz | Gittereigenwert, getrennte Raum- und Zeitverfeinerung und Teleskopieren der Zellflüsse. | Ein kompensierter Gesamtfehler kann zwei größere Einzelfehler verdecken. |
| Kapitel 8 | 104–113 | LBM am bewegten Deckel | D2Q9-Momente, Kollision, Streaming und rekonstruierte Randpopulationen. | Der Anlaufversuch und der lange CP2-Referenzlauf haben verschiedene Gitter und Horizonte. |
| Kapitel 9 | 114–134 | Gelernter Wellenoperator | Trainierte Fourier-Gewichte, zurückgehaltene Moden, gelernte Geschwindigkeit und Physik-Layer auf versetzten Gittern. | Rauschmodell und Wellengesetz bestimmen, wie weit eine Verbesserung übertragbar ist. |
| Kapitel 10 | 135–140 | Messauftrag und Score | Drittes Ereignis um 1,2 ms verspätet bei 1 ms Budget. Vertauschte Kontaktkennungen aktiv widerlegt. | Zur äußeren Abnahme gehören die Zuordnung und Vollständigkeit der Beobachtungen. |
| Kapitel 11 | 141–146 | C05, steifer Schalter | Exakter Phasenfluss und Vergleich der Zeit- und Endwertbudgets. | Kein Treffer unter den 57 ursprünglichen Einstellungen. Separate Referenzläufe besitzen eigene Budgets. |
| Kapitel 12 | 147–153 | C12 und C21-Ball | Kugelkennungen, Impulsübertrag, gerichteter Bodenkontakt und Restflugzeit. | Das elastische Studienfenster deckt nur einen Teil der offiziellen C12-Aufgabe ab. |
| Kapitel 13 | 154–166 | C07 und C21-Diode | Kinematischer Reset, Bindungsfehler, Diodenast und archivierte 149 Schaltungen. | Astregularität und kleiner numerischer Defekt beantworten unterschiedliche Fragen. |
| Kapitel 14 | 167–171 | C09 und C13 | 16 Reglertakte, Langzeitplateau und ein Puls mit richtigem Endimpuls trotz falschem Beginn. | Der kurze Tankversuch erklärt die Abweichung vom veröffentlichten Langzeitplateau nur begrenzt. |
| Kapitel 15 | 172–180 | C19R, Transport zum Brunnen | Drei Gitter, feste Außenflächen, Quellmassen und Konzentration am selben Ort. | Die drei Vergleichsläufe haben einen gemeinsamen Messort. Aussagen an anderen Orten brauchen eigene Kontrollen. |
| Kapitel 16 | 181–194 | CP2, Kavität und Saite | Getrennte Feldnormen, analytischer Saitenvergleich, Verlet-Neurechnung und Abgrenzung zum Physik-Layer. | Archiviertes Nachtraining, analytisch strukturierte Varianten und der Lehrversuch in 9.7 bilden eigene Versuchsreihen. |
| Kapitel 17 | 195–204 | Methodenwahl aus 456 Einstellungen | Alle Schlüssel und Statusklassen, wiederholte Zeitmessungen und zwei Zahlenfelder trotz Zeitlimit. | Die Wahl des Nenners und der physikalischen Aufgabe bestimmt, welche Rangfolge sinnvoll ist. |
| Anhang A | 205–229 | 24 Datenblätter | Alle 24 Kennungen und je sechs Abschnitte im Katalog geprüft. | 14 vertiefte Familien und zehn weitere Einträge des fixierten Projektregisters. Der Volltext benennt den jeweiligen Implementierungsstand. |
| Anhang B | 230–241 | Rohdaten, Beweise und Code | Alle 456 Zellen samt Kennung und gerundetem Wert, zwei exakte Nullstellen, Astregularität und Python-/C++-Vertrag. | Archivmessungen bleiben an ihren Solver-, Versions- und Hardwarestand gebunden. |

Vier kürzere Methodenkapitel erhielten jeweils eine zusätzliche Herleitung mit veränderter Versuchsannahme. Beim RK-Paar wird die unterschiedliche Ordnung der beiden Fehler sichtbar, beim Pendel eine falsche Beschleunigung trotz konsistenter Lage. Beim QSS-Speicher rückt ein geänderter Termin, im Finite-Volumen-Verfahren macht eine einseitige Flussänderung die Massenbilanz messbar falsch. Alle vier Versuche rechnen mit exakten rationalen Zahlen.

### C · Abbildungen und Druckprüfung

In der Ausgabe stehen **32 Vektorgrafiken**. Die ersten 18 enthalten unter anderem das normierte Phasenporträt, die getrennten Reaktionsmoden, den RC-Kreis mit Zählrichtungen, die Kollisions- und Transportbilanz und die Wellenversuche. Elf weitere Grafiken entstammen dem fixierten Benchmarkmaterial. Drei neu gezeichnete Abbildungen betreffen den Stoßscore, die Pulsabtastung und die Statusverteilung. Die Achsen, Einheiten, Teilbilder, Farbskalen und Quellen sind in den fünf Vorgabendateien unter `abbildungen/` dokumentiert.

Alle 247 PDF-Seiten wurden gerendert. Die Textprüfung fand keine abgeschnittene Zeile am Seitenrand. Die Kapitel und Anhänge sind über Lesezeichen erreichbar. Der Kapitelfahrplan trägt zusätzlich gedruckte Seitenangaben. Für die eigenständige Markdown-Fassung wurde geprüft, dass die eingebetteten Bilddaten mit den 32 SVG-Dateien übereinstimmen.

### D · Reproduzierbarkeit und offene Nachweise

| Gegenstand | Ergebnis dieser Ausgabe |
|---|---|
| Python-Prüfprogramme | 30 Programme mit Python 3.12.14, aktiven Assertions und ohne Drittanbieterpakete ausgeführt. Ein gemeinsames Modul unterstützt die Ereignisbeispiele. |
| C++-Schnittstelle | C++20-Beispiel mit g++ 14.2.0, aktivierten Warnungen und Assertions übersetzt und ausgeführt. Eingabezustand und abgeleitete Ausgabe geprüft. |
| Archivquelle | 34 Text-, Code-, Bild- und Datenquellen byteweise gegen ihre Git-Blob-Identität bestätigt. Die ursprüngliche Acht-Fälle-Studie gehört zum archivierten Messstand. |
| Drucktabelle | Jede der 456 Kombinationen aus Modell, Methode und Quantum mit der CSV abgeglichen, einschließlich aller Statuskennungen und gedruckten Scorewerte. |
| Numerische Bewertungen | 222 bestanden, 151 über Budget. Weitere 46 Zeitlimits, 20 Abweichungen der Beobachtungszahl und 17 Solverfehler. Zwei der 46 Zeitlimits enthalten einen Zahlenwert. |
| C19R, C21-Diode und CP2 | Separate Archivdaten und exemplarische Neurechnungen. Diese Versuche haben eigene Referenzen und gehen nicht in den Nenner 456 ein. |
| Quellen und Volltext | Markdown, Vektor-PDFs und SVGs, Kapiteldateien, Satzquelle, Programme, CSV-/JSON-Metriken und Ausführungsprotokoll im Gesamtquellenpaket. |

Die Vollständigkeit bezieht sich auf den vereinbarten Kapitelfahrplan und den benannten Projektkatalog. Die lokalen Prüfungen decken die dokumentierten Rechenwege, Assertions, Tabellen und Strukturmerkmale ab. Die historischen Solverläufe und das ursprüngliche CP2-Netztraining wurden für diese Ausgabe nicht vollständig neu ausgeführt. Das didaktische Urteil beruht auf einem kapitelweisen Fachlektorat. Ein unabhängiges Fachgutachten und eine Erprobung der Lernergebnisse mit Studierenden stehen aus.

[Autorenquelle des Buchs](https://github.com/5H3LL3H5/argesim-hyperposition-benchmarks/tree/16f0f2528fcf77f16898ecd74ad952be2c09eac2/docs/lehrbuch) · [Rohdaten der 456 Konfigurationen](https://github.com/5H3LL3H5/argesim-hyperposition-benchmarks/blob/16f0f2528fcf77f16898ecd74ad952be2c09eac2/docs/evidence/qss-extension.csv) · [Offizielle ARGESIM-Benchmarks](https://www.argesim.org/benchmarks)

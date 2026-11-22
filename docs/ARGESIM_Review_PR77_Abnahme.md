# Abnahme der Arbeitsanweisung zu PR #77

Geprüfte Ausgangsfassung d2db4732cf20a491d9a2f13b105ff0392ebf0641. Die nach dem neuen Inhaltsverzeichnis umgearbeitete Ausgabe umfasst 17 Kapitel und hat 343 Seiten, 343 Lesezeichen und 11 PDF-Anlagen. Die Seitenzahlen in dieser Liste bezeichnen die physischen PDF-Seiten.

[Lehrbuch](ARGESIM_SOLVER_STUDY.pdf?raw=true) · [Rechenlabor](ARGESIM_Bachelor_Rechenlabor.zip?raw=true) · [SHA-256-Nachweis](ARGESIM_Buchstand.json)

## 15 Korrekturen und 20 didaktische Empfehlungen

Die kurzen Pfade zu TeX-, Grafik- und Labordateien beginnen in docs/lehrbuch/studienbuch/.

| Befund | Seite vorher | Seite neu | Geänderte Quelle | Ergebnis der Gegenprobe |
|---|---:|---:|---|---|
| R77-C-05 | 119 | [212](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=212) | `kapitel/13.tex` | Tangential- und Radialprojektion, Ruheprobe mit Spannung mg. |
| R77-C-09 | 131 | [238](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=238), [241](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=241) | `kapitel/15.tex`, `scripts/c19_profiles.py`, `scripts/cp2_accuracy/transport_check.py` | Historische Flächen rekonstruiert. Feste Außenflächen, Massenrate und Brunnenwerte separat berechnet. |
| R77-P-10 | 161 | [259](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=259) | `material/cp2_feldlabor/auswerten.py`, `tests/test_cp2_accuracy.py` | Original besteht. Nullfeld bei 501 Knoten liefert Fehlerstatus. |
| R77-N-C07 | 180 | [273](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=273) | `kapitel/17.tex` | Abschlusszeilen mit den fünf Benchmark-Nachweisen abgeglichen. Voraussetzungen und verbleibende Fragen angegeben. |
| R77-N-G07 | 180 | [273](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=273) | `kapitel/17.tex` | Abschluss verweist auf die modale Schranke und nennt die gewichtete Sinuskoeffizienten-Bedingung sowie Anfangsruhe. |
| R77-F-10 | 40 | [31](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=31) | `abbildungen/thermisch.pdf` | Legende außerhalb der Datenfläche, 60-°C-Linie im PDF separat lesbar. |
| R77-G-04 | 40 | [31](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=31) | `kapitel/01.tex` | Bei 60 s ergeben sich 564,015 J gespeicherte Energie und 8,82497 W Änderungsrate. |
| R77-G-09 | 73 | [109](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=109) | `kapitel/04.tex` | Der Ast ist stetig differenzierbar. Im Gegenbeispiel hat seine erste Ableitung am Ursprung einen Knick. |
| R77-G-11 | 82 | [144](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=144) | `kapitel/07.tex` | Leitfähigkeit bleibt 200 W/(m K). Leitwert sinkt bei doppelter Länge von 4 auf 2 W/K. |
| R77-F-21 | 113 | [204](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=204) | `abbildungen/kontakte.pdf` | Verschobene Ortsachse, drei Kontaktmarken bei 1, 2 und 3 s und Legende oberhalb der Kurven. |
| R77-N-S03 | 163 | [179](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=179) | `kapitel/09.tex`, `material/cp2_genauigkeit/saite_zeitreihen.npz` | 2.376 RMS-Feldwerte nachgerechnet. Kontinuierliches Maximum als eigene Frage ausgewiesen. |
| R77-N-S08 | 164 | [251](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=251) | `material/cp2_genauigkeit/auswerten.py`, `tests/test_cp2_accuracy.py` | Unabhängige d’Alembert-Referenz und Rundungsintervalle geprüft. Verdoppelte Referenz liefert Fehlerstatus. |
| R77-F-27 | 165 | [176](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=176) | `kapitel/09.tex`, `abbildungen/fno_saite_feld.pdf` | Zwei Profile gerendert. Die Legenden verdecken die Knicke nicht. |
| R77-N-G02 | 173 | [59](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=59) | `kapitel/01.tex` | Gleichgerichtete Nullstellen im Abstand T. Spitzenverhältnis exp(−γT). |
| R77-F-09 | 39 | [30](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=30) | `abbildungen/stab.pdf` | Isolation und Ortsmarke x = 0 sind im Druck getrennt. |
| R77-N-C05 | 178 | [268](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=268) | `kapitel/17.tex`, `scripts/cp2_accuracy/chapter_checks.py` | 17 Kandidaten und acht Auswahlen. Für C05 14 Solverfehler, 3 Zielverfehlungen und 5 Treffer außerhalb der Schnittmenge. |
| R77-F-12 | 54 | [64](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=64) | `abbildungen/stabil.pdf` | Euler-Nullstelle und Stabilitätsrand im PDF markiert. |
| R77-G-13 | 94 | [115](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=115) | `kapitel/05.tex` | Stiftwechsel direkt verlinkt. Aus −1 rad/s folgt −10/3 rad/s bei stetigen −1 m/s. |
| R77-F-20 | 106 | [195](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=195) | `kapitel/11.tex` | Exakte Euler-Grenze angegeben. Verstärkung −0,998 bzw. −1,0007 für die beiden gerundeten Schritte. |
| R77-F-23 | 120 | [213](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=213) | `kapitel/13.tex`, `abbildungen/c07kurven.pdf` | Ausschnitt 6,6–6,8 s zeigt Ereignisse 7 und 8. Zeiten mit Labor und Tabelle abgeglichen. |
| R77-C-07 | 123 | [218](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=218) | `kapitel/13.tex` | Beide positiven Nullstellen separat bestimmt und Ableitungsvorzeichen geprüft. |
| R77-C-11 | 142 | [232](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=232) | `kapitel/14.tex`, `material/labor.py` | Die drei Werte für die Winkelgeschwindigkeit folgen aus dem vollständigen C13-Zustand. |
| R77-P-02 | 153 | [247](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=247) | `kapitel/16.tex`, `abbildungen/cp2kavitaet.pdf` | Innenraum umrandet. Beide Maxima ausgewiesen. Deckelzeile geprüft. |
| R77-F-26 | 155 | [176](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=176) | `kapitel/09.tex`, `abbildungen/fno_saite_feld.pdf` | Fehlerprofile bei 5 und 8 s auf derselben Millimeterskala. |
| R77-P-09 | 160 | [250](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=250) | `kapitel/16.tex`, `material/cp2_feldlabor/rope/rope-501-fields.npz` | Relative Norm und Spitzenfehler 0,705 bzw. 0,762 mm unterschieden. |
| R77-A77-12 | 162 | [260](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=260) | `kapitel/16.tex` | Frage und Lösung nennen das ursprüngliche FNO. Anschlussaufgabe verlinkt drei Operatorvarianten. |
| R77-P-11 | 163 | [253](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=253), [252](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=252) | `kapitel/16.tex`, `scripts/cp2_accuracy/rope_symmetry.py` | Sechs Termin-Modell-Paare ohne Training gegen d’Alembert gerechnet. Spiegelabweichungen archiviert. |
| R77-N-S04 | 165 | [176](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=176) | `kapitel/09.tex`, `material/cp2_genauigkeit/auswerten.py` | Analytische und gelernte Faktoren bei gleicher Modenzahl und Interpolation verglichen. |
| R77-F-29 | 169 | [255](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=255) | `kapitel/16.tex`, `abbildungen/fno_kavitaet_feld.pdf` | Signierte Farblegende und Bedeutung der blauen Zellen im PDF geprüft. |
| R77-A77-02 | 183 | [331](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=331) | `kapitel/uebungen-und-quellen.tex`, `scripts/build_studienbuch.py` | Alle zwölf Paare Frage und Auflösung in beide Richtungen geprüft. |
| R77-A77-03 | 187 | [335](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=335) | `kapitel/uebungen-und-quellen.tex` | Aufgabe verlinkt das exakte Profil. Sollabweichung in der Mitte 0,3125 K. |
| R77-A77-09 | 194 | [342](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=342) | `kapitel/uebungen-und-quellen.tex` | Vier Quellen zentral aufgenommen und mit ihren Einsatzstellen verbunden. |
| R77-F-07 | 28 | [50](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=50) | `kapitel/01.tex` | Pfeile als schematisch markiert. Mit −2 N und −0,2 N folgen −1,1 m/s². |
| R77-P-07 | 159 | [173](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=173) | `kapitel/09.tex` | Gegenaufgabe mit gleicher Messung in der Mitte und Differenz a am Viertelpunkt. |
| R77-A77-04 | 188 | [336](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=336) | `kapitel/uebungen-und-quellen.tex`, `scripts/build_studienbuch.py` | Alle sechs Lösungen springen direkt zur jeweiligen Originalaufgabe zurück. |

Die 14 gewünschten Referenzblätter und die zehn übrigen Modelle ergänzen den vollständigen Projektkatalog. Alle 456 ursprünglichen Konfigurationen stehen einzeln in Anhang B.1. Kapitel 1–9 enthalten jeweils einen nachvollziehbaren Algorithmus und eine gelöste Gegenprobe.

Für die vollständige Ausgabe dokumentiert die [fachlich-didaktische Kapitelprüfung](ARGESIM_Kapitelpruefung.md) die Rechenwege und Gegenproben für jedes Kapitel und jedes Referenzblatt.

## 69 bereits bestätigte Befunde

Die Fundstellen wurden auf die neue PDF zugeordnet. Die ursprüngliche Arbeitsanweisung bleibt die Referenz für den fachlichen Abnahmeauftrag je Befund. Die ausgeführten Gegenproben schließen folgende Ergebnisse ein.

- kapitelproben.py, nachrechnen.py und labor.py alle ausgeführt. Sie prüfen unter anderem die sechs Folgereglerläufe, den C05-Phasenfluss, C07- und C12-Ereignisse, den C13-Lastpuls, die C19-Quadratur und die C21-Ballistik.
- Alle 168 PDF-Zellen der Acht-Fälle-Matrix gegen 456 CSV-Zeilen geprüft. Statuszahlen ergeben 222 bestanden, 151 außerhalb des Genauigkeitsziels, 46 mit Zeitlimit, 20 mit abweichender Ereigniszahl und 17 mit Solverfehler.
- Alle 2.376 Saiten-RMS-Zeilen neu berechnet. Vier verschwindende Referenznormen sind gekennzeichnet. Kontrollmode 193, gespeicherte CP2-Prognosen, Deckelzeile und Literaturwerte der Mittellinien nachgerechnet.
- Zeitgitter und Quellraster separat wiederholt. Folgeregler- und C19R-Einschließungen gegen die Grenzwerte geprüft, RATTLE-Ereignisse neu berechnet und C05-Auswahlfalten wiederholt.
- 915 interne PDF-Links, 13 Aufgaben- und Lösungsseitenpaare mit A, B und C sowie 18 direkte Rücksprungpaare geprüft. Die zwei CP2-Anlagen mit 12 und 24 Einträgen sind bytegleich zu den entsprechenden Teilen des ZIP.
- Die Prüfungen verwenden veröffentlichte Netzgewichte und die archivierten stationären Kavitätsfelder. Das Netztraining und der volle stationäre Kavitätslauf wurden für diese Revision nicht neu gestartet.

| Befund | Vorher | Neu | Prüfthema |
|---|---:|---:|---|
| R77-N-G05 | 174 | [82](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=82) | Alle drei feinen Kurven halten das Fehlerziel auf dem ganzen Zeitintervall ein |
| R77-G-06 | 57 | [87](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=87) | Alle sechs Läufe des steifen Folgereglers sind reproduzierbar |
| R77-C-01 | 107 | [196](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=196) | C05 erreicht drei Schaltzeiten mit zwei verschiedenen Genauigkeitsbudgets |
| R77-C-03 | 114 | [205](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=205) | C21 bestätigt den zweiten Aufprall für QSS3 und QSS4 |
| R77-C-06 | 121 | [214](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=214) | Beim C07-Pendel verfehlt schon der erste lineare Kontakt das 10-ms-Ziel |
| R77-C-10 | 140 | [265](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=265) | Die abgedruckten C05- und C12-Rangfolgen folgen aus unterschiedlichen Messgrößen |
| R77-C-12 | 143 | [267](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=267) | Alle 168 Zellen der Acht-Fälle-Matrix stimmen mit dem Archiv überein |
| R77-N-G06 | 168 | [177](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=177) | Für s = 1 ist die modale Fehlergrenze am Start sogar scharf |
| R77-N-K02 | 170 | [256](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=256) | Neue Betriebspunkte benötigen eigene Referenzläufe |
| R77-N-K03 | 171 | [257](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=257) | Mittellinienfehler und Massenbilanz getrennt prüfen |
| R77-N-C01 | 175 | [219](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=219) | Der Niedrigstromast der C21-Diode bleibt von der Falte getrennt |
| R77-N-C02 | 176 | [240](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=240) | Für den C19R-Brunnen ist die lokale Fehlergrenze jetzt beziffert |
| R77-N-C03 | 177 | [221](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=221) | Das Zeitfenster für die dritte und vierte Schaltung trennt die C05-Fälle eindeutig |
| R77-N-C04 | 177 | [221](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=221) | Die offene Restflugfrage von S. 117 ist in der neuen Ausgabe gelöst |
| R77-N-C06 | 179 | [216](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=216) | RATTLE hält die Bindungen ein und zeigt rund zweite Ordnung für die acht Ereigniszeiten |
| R77-F-01 | 3 | [13](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=13) | Förderrate und geförderte Menge |
| R77-F-02 | 4 | [14](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=14) | Genügt die Fördermenge trotz Quadraturfehler? |
| R77-G-01 | 4 | [14](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=14) | Wann die Fehlergrenze die Füllmenge entscheidet |
| R77-F-03 | 6 | [40](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=40) | Tankfüllung mit Modell- und Zeitdiskretisierungsfehler |
| R77-F-04 | 11 | [20](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=20) | Zwei Moden im Temperaturfeld |
| R77-F-05 | 13 | [24](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=24) | Gleicher Ort, zwei Geschwindigkeiten |
| R77-F-06 | 19 | [38](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=38) | Periodenfehler eines Pendels bei 60 Grad |
| R77-G-02 | 19 | [38](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=38) | Das Einprozentziel des Pendels gilt für die Periode |
| R77-F-08 | 29 | [51](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=51) | Weg und Geschwindigkeit einer gedämpften Feder |
| R77-F-11 | 44 | [36](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=36) | Was ein Mittelwertsensor sehen kann |
| R77-G-05 | 45 | [229](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=229) | Die kritische Abtastzeit folgt aus der exakten Strecke |
| R77-G-07 | 60 | [91](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=91) | Radau dämpft die schnelle Mode und lässt bei großem Schritt einen messbaren Rest |
| R77-A77-05 | 63 | [80](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=80) | Die Konvergenzaufgabe trennt gemessene Ordnung und Toleranz |
| R77-F-13 | 65 | [98](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=98) | Stromrichtung und Polung im RC-Kreis |
| R77-G-08 | 66 | [99](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=99) | Der RC-Kreis zeigt Gleichwertigkeit und Zeitfehler im selben Versuch |
| R77-F-14 | 68 | [102](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=102) | Konsistente Anfangswerte auf der Maschengeraden |
| R77-F-15 | 74 | [138](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=138) | Wärmefluss an drei Sensoren |
| R77-F-16 | 77 | [141](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=141) | Eine Linienmethode mit drei freien Knoten |
| R77-F-17 | 79 | [147](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=147) | Raumfehler, Zeitfehler und Fehlerkompensation |
| R77-G-10 | 79 | [147](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=147) | Raum- und Zeitfehler der Linienmethode kompensieren sich |
| R77-G-12 | 88 | [152](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=152) | Vier Zellen trennen Mengenerhaltung und Positivität |
| R77-F-18 | 93 | [114](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=114) | Zwei Schwellenübergänge innerhalb eines Schrittes |
| R77-F-19 | 95 | [127](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=127) | Meldewert und integrierter Zustand bei QSS1 |
| R77-G-14 | 96 | [129](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=129) | Die QSS-Fehlergrenze lässt sich am zweiten Ereignis messen |
| R77-C-02 | 112 | [203](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=203) | C12 lässt sich über die drei Spalte und die Stoßpartner prüfen |
| R77-F-22 | 114 | [205](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=205) | Ball nach dem ersten Bodenkontakt |
| R77-C-08 | 130 | [237](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=237) | Eine zweite Quadratur bestätigt den C19R-Sensorwert |
| R77-F-24 | 130 | [237](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=237) | C19R-Impuls im transportierten Feld |
| R77-A77-06 | 147 | [271](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=271) | Beim Solverprofil zählt auch der fehlgeschlagene Fall |
| R77-A77-07 | 148 | [226](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=226) | Die C07-Projektentscheidung lässt sich aus acht Zahlenpaaren rekonstruieren |
| R77-P-01 | 152 | [77](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=77) | Ein Modell liefert die Kontrollwerte für drei Integratoren |
| R77-F-25 | 153 | [247](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=247) | CP2-Kavität mit Referenz-, FNO- und Fehlerkarte |
| R77-P-03 | 154 | [165](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=165) | Die gestörte D2Q9-Zelle erhält Dichte und Impuls |
| R77-P-04 | 155 | [248](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=248) | Spiegelung und korrigierte Wellengeschwindigkeit sind konsistent |
| R77-P-05 | 156 | [249](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=249) | Newmark und Verlet bestehen beide 1-%-Prüfungen der Saite |
| R77-P-06 | 157 | [172](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=172) | Der Lernschritt lässt sich mit drei Zahlen kontrollieren |
| R77-P-08 | 160 | [250](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=250) | Die beiden FNO-Testmittel sind aus den Gewichten reproduzierbar |
| R77-A77-08 | 161 | [259](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=259) | Das Feldlabor bestätigt die Antwort zur Deckelzeile |
| R77-N-S01 | 165 | [176](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=176) | Die modale Fourier-Schicht erreicht auf beiden 501er Profilen weniger als 0,05 % |
| R77-N-S05 | 166 | [252](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=252) | Nachtraining und Architekturwechsel liefern messbar verschiedene Gewinne |
| R77-F-28 | 167 | [254](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=254) | Zupfposition, Modenzahl und zeitliche Stützstellen |
| R77-N-S02 | 167 | [254](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=254) | Die neue Ausgabe behandelt den Zeitpunkt mit verschwindender Bezugsnorm |
| R77-N-S06 | 167 | [254](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=254) | Alle 2 376 Saitenmessungen lassen sich neu berechnen |
| R77-N-S07 | 168 | [177](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=177) | Die Modengrenze kann auf einem darstellbaren Profil 100 % Fehler verursachen |
| R77-N-K01 | 169 | [255](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=255) | Geschwindigkeitsbetrag und Vektorfehler derselben Kavität |
| R77-F-30 | 170 | [256](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=256) | Vorhersagen auf neuen Gittern mit und ohne Kalibrierung |
| R77-F-31 | 171 | [257](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=257) | CP2-Mittellinien nach dem langen D2Q9-Lauf |
| R77-N-G01 | 173 | [59](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=59) | Ein optimaler Messabstand braucht kalibrierte Fehlergrenzen |
| R77-N-G03 | 173 | [59](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=59) | Die C²-Klassifikation steht jetzt im Buch und ist vollständig |
| R77-N-G04 | 173 | [59](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=59) | Sensor an beiden Endpunkten gleich empfindlich für die Differenzmode |
| R77-A77-01 | 182 | [330](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=330) | Alle 39 Kapitelaufgaben haben auffindbare Lösungswege |
| R77-A77-11 | 192 | [340](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=340) | Der Radau-Nachweis nennt Stufenzahl und die beiden Ordnungen |
| R77-A77-10 | 193 | [341](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=341) | Der QSS2-Beleg und die spätere Übersicht haben verschiedene Aufgaben |
| R77-D-01 | 195 | [343](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=343) | Buchseiten und interne PDF-Ziele lassen sich eindeutig auflösen |

## Alle 74 Zuordnungen aus PR #74

Die Statusangabe stammt aus dem Abgleich zu PR #77. Die letzte Spalte nennt das Prüfthema und, wo zutreffend, die Änderung dieser Revision.

| ID | Einordnung in PR #77 | Seite neu | Prüfung oder Ergänzung dieser Revision |
|---|---|---:|---|
| B-01 | Neu gefasst | [31](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=31) | Vom Fühler zur dimensionslosen Gleichung |
| B-02 | Weiter gültig | [74](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=74) | Was „lokaler Fehler“ im ersten Schritt bedeutet |
| B-03 | Neu gefasst | [70](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=70) | RK4 lässt sich am Fühler vollständig nachrechnen |
| B-04 | Weiter gültig | [75](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=75) | Beide RK23-Endwerte aus denselben vier Stufen eingesetzt. |
| B-05 | Neu gefasst | [78](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=78) | Am Oszillator Energie und Phase getrennt prüfen |
| B-06 | Neu gefasst | [64](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=64) | Vom Stabilitätsrand zur steifen Rechnung |
| B-07 | Neu gefasst | [141](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=141) | Den Modellwechsel von ODE zu PDE sichtbar machen |
| B-08 | Weiter gültig | [238](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=238) | Historische Gitterreihe und Versuch mit festen Außenflächen dokumentiert. Vergleich RK/QSS als Versuchsplan ausgewiesen. |
| B-09 | Weiter gültig | [336](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=336) | Eine erfüllte Maschengleichung reicht als Test nicht aus |
| B-10 | Neu gefasst | [115](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=115) | Die Brücke zwischen DAE, DEVS und QSS |
| B-11 | Weiter gültig | [64](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=64) | Eigenwerte allein entscheiden die Solverwahl nicht |
| B-12 | Nur Archiv | — | Vier englische Kapitel gezielt als Vertiefung lesen |
| B-13 | Neu gefasst | [343](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=343) | 343 Seiten, 343 Lesezeichen, 11 Anlagen und SHA-256 von PDF und Labor geprüft. |
| B-14 | Neu gefasst | [330](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=330) | Direkte Rücksprünge der Lösungen 1–6 und der zwölf Vorhersagen ergänzt. |
| B-15 | Neu gefasst | [191](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=191) | Wie weit reicht der Ausführungsnachweis der Codebeispiele? |
| Q-01 | Neu gefasst | [127](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=127) | Die ersten QSS1-Meldungen lassen sich nachrechnen |
| Q-02 | Neu gefasst | [129](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=129) | Vom Quantisierungsband zur Fehlerschranke |
| Q-03 | Weiter gültig | [130](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=130) | Erstes QSS2-Ereignis aus dem quadratischen Fehlerpolynom berechnet. |
| Q-04 | Neu gefasst | [133](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=133) | Welche Rückkopplung behandelt LIQSS implizit? |
| Q-05 | Neu gefasst | [133](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=133) | Gleiche Updates und experimentelle Erweiterungen kennzeichnen |
| Q-06 | Weiter gültig | [130](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=130) | Drei Quantenregeln am selben Speicher mit erster Ereigniszeit erläutert. |
| Q-07 | Neu gefasst | [129](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=129) | Externer Eingang löscht den alten QSS-Termin |
| Q-09 | Weiter gültig | [343](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=343) | 33 der 138 Konfigurationen betreffen ARGESIM |
| Q-10 | Weiter gültig | [343](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=343) | Drei Studien besitzen drei verschiedene Versuchsraster |
| Q-11 | Weiter gültig | [265](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=265) | C12 misst drei Kontakte und 36 RHS-Auswertungen |
| Q-12 | Weiter gültig | [265](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=265) | Stabilität und Zielerfüllung bei C05 getrennt lesen |
| Q-13 | Neu gefasst | [78](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=78) | Beim Oszillator wird der Phasenfehler nur indirekt erfasst |
| Q-14 | Weiter gültig | [232](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=232) | C13 belegt eine Grenze des untersuchten QSS-Rasters |
| Q-15 | Neu gefasst | [220](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=220) | Drei unabhängige Ausgabezeitgitter mit je 149 Zeitpunkten und Maximalabweichungen protokolliert. |
| Q-16 | Neu gefasst | [203](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=203) | Zwei Millisekunden Verspätung liefern bei richtiger Ereigniszahl Score 2 und einen Fehlerstatus. |
| Q-17 | Neu gefasst | [191](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=191) | CSV-Integrität ist belegt, Übertragbarkeit der Laufzeit bleibt offen |
| Q-18 | Weiter gültig | [205](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=205) | Ein wiedergefundener Ballkontakt ist ein begrenzter Regressionstest |
| ABB-01 | Entfallen | — | Abkühlung und Fehlerordnung |
| ABB-02 | Neu gefasst | [70](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=70) | Stufenzustände und Gewichte von RK4 |
| ABB-03 | Neu gefasst | [78](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=78) | Amplitude und Phase des Oszillators |
| ABB-04 | Neu gefasst | [64](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=64) | Euler-Nullstelle und Stabilitätsgrenze markiert. |
| ABB-05 | Neu gefasst | [141](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=141) | Wärmefeld und Drei-Punkt-Schablone |
| ABB-06 | Neu gefasst | [98](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=98) | RC-Ladekreis und Maschenbilanz |
| ABB-07 | Neu gefasst | [102](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=102) | Zulässige Zustandspaare im Ladekreis |
| ABB-08 | Neu gefasst | [127](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=127) | QSS1 im Bild: Näherung und Meldung unterscheiden |
| ABB-09 | Neu gefasst | [204](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=204) | Ordinate als verschobene Lage bezeichnet und Legende versetzt. |
| ABB-10 | Neu gefasst | [195](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=195) | Exakte Euler-Grenze und zwei Versuchsschritte verglichen. |
| ABB-11 | Neu gefasst | [265](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=265) | Welche Kosten zeigt der C12-Vergleich? |
| ABB-12 | Neu gefasst | [205](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=205) | C21: gerichtete Rückkehr zur Bodenfläche |
| A-01 | Entfallen | — | Abkühlen mit zwei Euler-Schritten |
| A-02 | Neu gefasst | [75](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=75) | Spannung und Strom im adaptiven Fehlertest |
| A-03 | Neu gefasst | [199](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=199) | Stabilität und Dämpfung des schnellen Modus |
| A-04 | Neu gefasst | [149](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=149) | Gitterweite bei Diffusion und Transport |
| A-05 | Weiter gültig | [336](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=336) | RC-Kreis zu einem festgelegten Zeitpunkt |
| A-06 | Neu gefasst | [129](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=129) | Ereignisplan nach einem externen Eingang |
| A-07 | Entfallen | — | QSS1 an der Temperaturschwelle |
| A-08 | Weiter gültig | [337](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=337) | Schaltfolge und Score für C05 |
| A-09 | Neu gefasst | [203](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=203) | Ein versetzter Stoß bei richtiger Endgeschwindigkeit |
| L-HNW | Weiter gültig | [340](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=340) | Solving Ordinary Differential Equations I: Nonstiff Problems |
| L-HW | Weiter gültig | [340](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=340) | Solving Ordinary Differential Equations II: Stiff and Differential-Algebraic Problems |
| L-FNC | Weiter gültig | [341](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=341) | Fundamentals of Numerical Computation |
| L-LV | Weiter gültig | [341](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=341) | Finite Volume Methods for Hyperbolic Problems |
| L-BS | Neu gefasst | [340](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=340) | A 3(2) pair of Runge–Kutta formulas |
| L-DP | Neu gefasst | [340](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=340) | A family of embedded Runge-Kutta formulae |
| L-KV | Weiter gültig | [340](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=340) | Singly diagonally implicit Runge–Kutta methods with an explicit first stage |
| L-IDA | Weiter gültig | [341](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=341) | IDA Mathematical Considerations |
| L-ZE | Neu gefasst | [341](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=341) | Theory of Modelling and Simulation |
| L-ZL | Neu gefasst | [341](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=341) | Theory of quantized systems: formal basis for DEVS/HLA distributed simulation environment |
| L-KJ | Weiter gültig | [341](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=341) | Quantized-State Systems: A DEVS Approach for Continuous System Simulation |
| L-Q2 | Neu gefasst | [130](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=130) | Primärarbeit und ausgerechneter QSS2-Termin sind verknüpft. |
| L-QD | Nur Archiv | — | Quantization-Based Simulation of Differential Algebraic Equation Systems |
| L-HY | Nur Archiv | — | Discrete Event Simulation of Hybrid Systems |
| L-Q3 | Nur Archiv | — | A Third Order Discrete Event Method for Continuous System Simulation |
| L-CK | Entfallen | — | Continuous System Simulation |
| L-BQ | Nur Archiv | — | Quantization-based new integration methods for stiff ordinary differential equations |
| L-LI | Weiter gültig | [341](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=341) | Linearly implicit quantization-based integration methods for stiff ordinary differential equations |
| L-FK | Nur Archiv | — | A stand-alone quantized state system solver for continuous system simulation |
| L-GL | Nur Archiv | — | On general linearly implicit quantized state system methods |
| L-ARG | Weiter gültig | [343](ARGESIM_SOLVER_STUDY.pdf?raw=true#page=343) | ARGESIM Benchmarks |

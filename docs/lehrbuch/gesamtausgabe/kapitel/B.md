<a id="fb-beweise"></a>

# Anhang B · Beweise, Einzelmessungen und Schnittstellen

<a id="fb-runs"></a>

## B.1 · Die 456 Einzelkonfigurationen

Jedes der acht Modellfenster hat 57 Konfigurationen. Die Tabellen führen jedes Verfahren und jede Einstellung auf. Zur Zeile gehören in der CSV-Datei auch Arbeitszähler, neu gemessene Laufzeiten in Millisekunden und gegebenenfalls die Diagnose.

Je Zelle stehen die Statuskennung und, sofern vorhanden, der auf drei signifikante Stellen gerundete gespeicherte Score. **B** bedeutet bestanden, **G** numerisches Budget überschritten, **T** Zeitlimit, **E** abweichende Zahl von Beobachtungen und **F** Solverfehler. Für abgeschlossene Bewertungen gilt der ungerundete CSV-Wert. Vier unvollständige Zeilen enthalten bereits einen Score aus dem Vorlauf. Die Statuskennung entscheidet über die Verwertbarkeit. Die Schreibweise 2,6e-5 entspricht 0,000026. Die Reihenfolge der Quanten ist grob, mittel, fein. Die drei klassischen Kontrollen besitzen jeweils eine feste Konfiguration. Messzeiten, Kosten und Fehlerdetails stehen für jede Zeile in `daten/qss-extension.csv`.

Die [Methodenlegende direkt unter der Hauptmatrix](../lehrbuch_numerische_simulation.md#auflage-k18-01) erklärt die Ordnungsziffer, die Schwellenwahl und den steifen Block.


<!-- Buchseite -->

<a id="fb-runC03a"></a>

### C03 · 54 Quantisierungen und drei Kontrollen

<a id="tab-ab-01"></a>

| Verfahren | 0,005 | 0,001 | 0,0002 |
|---|---|---|---|
| CHEQSS1 | G 9,4 | G 1,22 | T |
| CHEQSS2 | G 41,5 | G 8,37 | G 1,68 |
| CHEQSS3 | G 19,9 | G 10,2 | G 2,16 |
| CQSS1 | F | F | F |
| ELIQSS1 | G 9,4 | G 1,22 | B 0,199 |
| ELIQSS2 | G 28,6 | G 4,39 | G 1,11 |
| ELIQSS3 | G 45 | G 5,15 | B 0,692 |
| LIQSS-BDF | T | T | T |
| LIQSS1 | G 77,2 | G 19,1 | T |
| LIQSS2 | T | T | T |
| LIQSS3 | G 72,9 | G 24,7 | G 4,59 |
| MLIQSS1 | G 77,2 | G 19,1 | T |
| MLIQSS2 | T | T | T |
| MLIQSS3 | G 72,9 | G 24,7 | G 4,59 |
| QSS1 | G 96 | G 20,4 | G 4,19 |
| QSS2 | G 40,7 | G 7,74 | G 1,9 |
| QSS3 | T | T | T |
| QSS4 | T | T | T |

**Klassische Kontrollen.** EULER G 1,07, RK4 B 4,58e-11, RK45 B 1,06e-6.

**Statusbilanz.** 4 bestanden, 32 über Budget, 18 mit Zeitlimit, 0 mit abweichender Beobachtungszahl, 3 mit Solverfehler.

Am geschalteten Verstärker entscheidet das gewählte kurze Zeitfenster. Vergleichen Sie Spannungen und Ströme komponentenweise, bevor Sie die Zähler eines erfolgreichen Laufs interpretieren.


<!-- Buchseite -->

<a id="fb-runC05a"></a>

### C05 · 54 Quantisierungen und drei Kontrollen

<a id="tab-ab-02"></a>

| Verfahren | 0,005 | 0,001 | 0,0002 |
|---|---|---|---|
| CHEQSS1 | G 135 | G 16,2 | T |
| CHEQSS2 | E | T | E |
| CHEQSS3 | T | T | T |
| CQSS1 | F | F | F |
| ELIQSS1 | G 135 | G 16,2 | T |
| ELIQSS2 | E | T | T |
| ELIQSS3 | T | T | T |
| LIQSS-BDF | G 191 | G 39,5 | G 7,57 |
| LIQSS1 | E | E | T |
| LIQSS2 | T | T | T |
| LIQSS3 | E | E | E |
| MLIQSS1 | E | E | T |
| MLIQSS2 | T | T | T |
| MLIQSS3 | E | E | E |
| QSS1 | T | T | T |
| QSS2 | T | T | T |
| QSS3 | T | T | T |
| QSS4 | T | T | T |

**Klassische Kontrollen.** EULER F, RK4 T, RK45 F.

**Statusbilanz.** 0 bestanden, 7 über Budget, 32 mit Zeitlimit, 13 mit abweichender Beobachtungszahl, 5 mit Solverfehler.

Keine Einstellung der historischen Matrix erfüllt hier den Auftrag. Kapitel 11 beschreibt ein getrenntes Radau/BDF-Experiment mit korrekt lokalisierten Schaltungen. Es hat eigene Budgets.


<!-- Buchseite -->

<a id="fb-runC07a"></a>

### C07 · 54 Quantisierungen und drei Kontrollen

<a id="tab-ab-03"></a>

| Verfahren | 0,005 | 0,001 | 0,0002 |
|---|---|---|---|
| CHEQSS1 | B 0,872 | B 0,0805 | T |
| CHEQSS2 | G 7,71 | G 1,39 | B 0,238 |
| CHEQSS3 | G 6,41 | G 1,28 | B 0,351 |
| CQSS1 | B 0,249 | B 0,0123 | B 0,000444 |
| ELIQSS1 | B 0,872 | B 0,0805 | T |
| ELIQSS2 | G 7,19 | G 1,65 | B 0,319 |
| ELIQSS3 | G 3,81 | B 0,822 | B 0,166 |
| LIQSS-BDF | B 0,0121 | B 0,0121 | B 0,0121 |
| LIQSS1 | G 16,2 | G 3 | T |
| LIQSS2 | G 17,9 | G 3,35 | B 0,626 |
| LIQSS3 | G 27,2 | G 5,18 | B 0,947 |
| MLIQSS1 | G 16,2 | G 3 | T |
| MLIQSS2 | G 15,7 | G 3,35 | B 0,626 |
| MLIQSS3 | G 26,7 | G 5,18 | B 0,947 |
| QSS1 | G 14,4 | G 2,88 | B 0,566 |
| QSS2 | G 8,36 | G 1,58 | B 0,295 |
| QSS3 | G 7,13 | G 1,49 | B 0,269 |
| QSS4 | G 3,29 | B 0,765 | B 0,217 |

**Klassische Kontrollen.** EULER G 4,19, RK4 B 3,78e-9, RK45 B 3,25e-6.

**Statusbilanz.** 26 bestanden, 27 über Budget, 4 mit Zeitlimit, 0 mit abweichender Beobachtungszahl, 0 mit Solverfehler.

Beim Stiftpendel ist eine kleine Zeitabweichung von einer falschen Kontaktfolge zu unterscheiden. Die kartesische Bindungsprüfung in Kapitel 13 ist ein zusätzlicher Versuchsaufbau.


<!-- Buchseite -->

<a id="fb-runC09a"></a>

### C09 · 54 Quantisierungen und drei Kontrollen

<a id="tab-ab-04"></a>

| Verfahren | 0,005 | 0,001 | 0,0002 |
|---|---|---|---|
| CHEQSS1 | G 1,26 | B 0,0517 | B 0,00158 |
| CHEQSS2 | G 2,37 | B 0,416 | B 0,0582 |
| CHEQSS3 | G 2,3 | B 0,409 | B 0,0652 |
| CQSS1 | B 0,038 | B 0,00194 | B 7,8e-5 |
| ELIQSS1 | G 1,26 | B 0,0517 | B 0,00158 |
| ELIQSS2 | G 2,4 | B 0,44 | B 0,0714 |
| ELIQSS3 | G 2,38 | B 0,451 | B 0,0816 |
| LIQSS-BDF | G 1,12 | B 0,221 | B 0,042 |
| LIQSS1 | B 0,923 | B 0,138 | B 0,0269 |
| LIQSS2 | G 2,6 | B 0,514 | B 0,0994 |
| LIQSS3 | G 2,58 | B 0,517 | B 0,103 |
| MLIQSS1 | B 0,923 | B 0,138 | B 0,0269 |
| MLIQSS2 | G 2,6 | B 0,514 | B 0,0994 |
| MLIQSS3 | G 2,58 | B 0,517 | B 0,103 |
| QSS1 | B 0,539 | B 0,129 | B 0,0265 |
| QSS2 | B 0,0117 | B 0,0117 | B 0,0117 |
| QSS3 | B 0,00015 | B 0,00015 | B 0,00015 |
| QSS4 | B 4,42e-6 | B 4,42e-6 | B 4,42e-6 |

**Klassische Kontrollen.** EULER B 0,0265, RK4 B 2,19e-11, RK45 B 4,02e-9.

**Statusbilanz.** 46 bestanden, 11 über Budget, 0 mit Zeitlimit, 0 mit abweichender Beobachtungszahl, 0 mit Solverfehler.

Das Raster bewertet 16 Abtastzeiten. Für die langen Plateaus der veröffentlichten Reglerkurve führt Kapitel 14 eine gesonderte Prüfung in Zentimetern durch.


<!-- Buchseite -->

<a id="fb-runC11a"></a>

### C11 · 54 Quantisierungen und drei Kontrollen

<a id="tab-ab-05"></a>

| Verfahren | 0,005 | 0,001 | 0,0002 |
|---|---|---|---|
| CHEQSS1 | B 0,494 | B 0,0255 | T 0,00258 |
| CHEQSS2 | B 0,302 | B 0,089 | B 0,0161 |
| CHEQSS3 | G 1,32 | B 0,213 | B 0,0284 |
| CQSS1 | B 0,287 | B 0,0309 | B 0,00262 |
| ELIQSS1 | B 0,494 | B 0,0255 | T 0,00258 |
| ELIQSS2 | B 0,483 | B 0,116 | B 0,0186 |
| ELIQSS3 | G 1,42 | B 0,266 | B 0,0468 |
| LIQSS-BDF | B 0,000374 | B 0,000181 | B 0,000181 |
| LIQSS1 | B 0,45 | B 0,084 | T |
| LIQSS2 | B 0,999 | B 0,21 | B 0,04 |
| LIQSS3 | G 1,52 | B 0,307 | B 0,0619 |
| MLIQSS1 | B 0,45 | B 0,084 | T |
| MLIQSS2 | B 0,999 | B 0,21 | B 0,04 |
| MLIQSS3 | G 1,52 | B 0,307 | B 0,0619 |
| QSS1 | B 0,693 | B 0,167 | B 0,0371 |
| QSS2 | B 0,482 | B 0,0852 | B 0,019 |
| QSS3 | B 0,0576 | B 0,0437 | B 0,00488 |
| QSS4 | B 0,00201 | B 0,00201 | B 0,00201 |

**Klassische Kontrollen.** EULER B 0,192, RK4 B 1,73e-11, RK45 B 1,71e-8.

**Statusbilanz.** 49 bestanden, 4 über Budget, 4 mit Zeitlimit, 0 mit abweichender Beobachtungszahl, 0 mit Solverfehler.

Bei LIQSS1 und dem kleinsten Quantum steht ein Zwischenwert von 0,0294 im Archiv. Das Zeitlimit beendet die Messung. Der Status T bleibt erhalten.


<!-- Buchseite -->

<a id="fb-runC12a"></a>

### C12 · 54 Quantisierungen und drei Kontrollen

<a id="tab-ab-06"></a>

| Verfahren | 0,005 | 0,001 | 0,0002 |
|---|---|---|---|
| CHEQSS1 | B 1,78e-12 | B 1,78e-12 | T |
| CHEQSS2 | B 0 | B 0 | B 0 |
| CHEQSS3 | B 0 | B 0 | B 0 |
| CQSS1 | B 0 | B 0 | T 2,59e-10 |
| ELIQSS1 | B 1,78e-12 | B 1,78e-12 | T |
| ELIQSS2 | B 0 | B 0 | B 0 |
| ELIQSS3 | B 0 | B 0 | B 0 |
| LIQSS-BDF | B 8,88e-13 | B 4,44e-13 | B 2,22e-13 |
| LIQSS1 | B 1,78e-12 | T | T |
| LIQSS2 | B 0 | B 0 | B 0 |
| LIQSS3 | B 0 | B 0 | B 0 |
| MLIQSS1 | B 1,78e-12 | B 1,78e-12 | T |
| MLIQSS2 | B 0 | B 0 | B 0 |
| MLIQSS3 | B 0 | B 0 | B 0 |
| QSS1 | B 2,66e-12 | B 2,66e-12 | B 3,27e-10 |
| QSS2 | B 0 | B 0 | B 0 |
| QSS3 | B 0 | B 0 | B 0 |
| QSS4 | B 0 | B 0 | B 0 |

**Klassische Kontrollen.** EULER B 2e-11, RK4 B 2e-11, RK45 B 0.

**Statusbilanz.** 51 bestanden, 0 über Budget, 6 mit Zeitlimit, 0 mit abweichender Beobachtungszahl, 0 mit Solverfehler.

Eine nahezu verschwindende Fehlerzahl passt zu den geradlinigen Flugbahnen im elastischen Fenster. Für unelastische oder zufallsabhängige Stöße ändern sich die Zielgrößen.


<!-- Buchseite -->

<a id="fb-runC13a"></a>

### C13 · 54 Quantisierungen und drei Kontrollen

<a id="tab-ab-07"></a>

| Verfahren | 0,005 | 0,001 | 0,0002 |
|---|---|---|---|
| CHEQSS1 | G 20,1 | T | T |
| CHEQSS2 | G 93,2 | G 27,3 | G 6,2 |
| CHEQSS3 | G 51,3 | G 11,1 | G 2,52 |
| CQSS1 | F | F | F |
| ELIQSS1 | G 20,1 | T | T |
| ELIQSS2 | G 67,2 | G 28,9 | T 5,52 |
| ELIQSS3 | G 92,4 | G 19,6 | G 2,74 |
| LIQSS-BDF | G 179 | T | T |
| LIQSS1 | G 134 | T | T |
| LIQSS2 | G 181 | G 77,1 | T |
| LIQSS3 | G 474 | G 49,4 | G 7,45 |
| MLIQSS1 | G 134 | T | T |
| MLIQSS2 | G 139 | G 72,7 | T |
| MLIQSS3 | G 366 | G 35,8 | G 7,21 |
| QSS1 | G 130 | G 23,5 | F |
| QSS2 | G 148 | G 33,7 | G 7,02 |
| QSS3 | G 53,4 | G 10,1 | G 2,22 |
| QSS4 | G 49,1 | G 19,5 | G 3,26 |

**Klassische Kontrollen.** EULER G 85,7, RK4 B 2,61e-5, RK45 B 2,06e-5.

**Statusbilanz.** 2 bestanden, 38 über Budget, 13 mit Zeitlimit, 0 mit abweichender Beobachtungszahl, 4 mit Solverfehler.

Hier bestehen zwei der drei klassischen Einstellungen. Das mittlere Quantum von CHEQSS1 enthält trotz Zeitlimit einen gespeicherten Zwischenwert. Die Abnahme erfordert das vollständige Pulsfenster.


<!-- Buchseite -->

<a id="fb-runC21a"></a>

### C21 · 54 Quantisierungen und drei Kontrollen

<a id="tab-ab-08"></a>

| Verfahren | 0,005 | 0,001 | 0,0002 |
|---|---|---|---|
| CHEQSS1 | B 0,00885 | B 0,00171 | T |
| CHEQSS2 | B 9,77e-10 | B 7,27e-10 | B 6,09e-10 |
| CHEQSS3 | B 2,29e-10 | B 2,29e-10 | B 2,29e-10 |
| CQSS1 | B 0,00456 | B 0,000499 | B 1,98e-5 |
| ELIQSS1 | B 0,00885 | B 0,00171 | T |
| ELIQSS2 | B 1,2e-9 | B 1,86e-10 | B 9,5e-10 |
| ELIQSS3 | B 2,29e-10 | B 2,29e-10 | B 2,29e-10 |
| LIQSS-BDF | B 2,02e-9 | B 5,85e-10 | B 2,27e-9 |
| LIQSS1 | G 17,1 | G 3,42 | T |
| LIQSS2 | B 9,99e-11 | B 1,71e-9 | B 7,37e-11 |
| LIQSS3 | B 2,29e-10 | B 2,29e-10 | B 2,29e-10 |
| MLIQSS1 | G 17,1 | G 3,42 | T |
| MLIQSS2 | B 9,99e-11 | B 1,71e-9 | B 7,37e-11 |
| MLIQSS3 | B 2,29e-10 | B 2,29e-10 | B 2,29e-10 |
| QSS1 | G 17,1 | G 3,43 | B 0,685 |
| QSS2 | B 4,05e-7 | B 1,68e-7 | B 7,06e-8 |
| QSS3 | B 2,29e-10 | B 2,29e-10 | B 2,29e-10 |
| QSS4 | B 6,15e-6 | B 6,15e-6 | B 6,15e-6 |

**Klassische Kontrollen.** EULER G 12, RK4 B 2,44e-11, RK45 B 1,17e-10.

**Statusbilanz.** 46 bestanden, 7 über Budget, 4 mit Zeitlimit, 0 mit abweichender Beobachtungszahl, 0 mit Solverfehler.

Dieser Tabellenausschnitt behandelt den springenden Ball. Der eigenständige Diodenvergleich und der Nachweis des algebraischen Lösungszweigs sind in Kapitel 13 zu finden.

<a id="fb-absB-2"></a>

## B.2 · Ereignisschranken, Stabilität und DAE-Astfortsetzung

### B.2.1  Eine Wurzel nachweisen und ihre Lage einschließen

Ein Positionssensor begrenzt den Wert eines Wächters nur auf ein Intervall. Wie sicher muss das Vorzeichen an beiden Enden sein? Sei $G(t)=g(t,x(t))$ stetig auf $[a,b]$ und seien seine beiden Endwerte durch Intervalle vollständig eingeschlossen. Liegt die obere Schranke von $G(a)$ unter null und die untere von $G(b)$ über null, garantiert der Zwischenwertsatz mindestens einen Durchgang. Gilt außerdem $G'\ge m>0$ im ganzen Intervall, ist er eindeutig.
Für eine berechnete Nullstelle $\hat t$ mit $|G(\hat t)|\le\varepsilon$ liefert der Mittelwertsatz $|\hat t-t_*|\le\varepsilon/m$. Bei $m=0{,}2\,\mathrm{m/s}$ und $\varepsilon=0{,}1\,\mathrm{mm}$ sind das 0,5 ms. Sind die Werte an beiden Enden positiv, kann es innen zwei Durchgänge geben. Dann helfen mehrere isolierte Intervalle oder eine Einschließung der Extrema.

### B.2.2  Stationärer Ast und Verlust der Regularität

Sei $g(t,x,z)=0$ stetig differenzierbar und $g_z$ am Start invertierbar. Der Satz über implizite Funktionen liefert lokal einen eindeutigen Ast $z=\zeta(t,x)$. Entlang einer glatten Lösung folgt $z'=-g_z^{-1}(g_t+g_x\,x')$, wobei $g_x\,x'$ das Produkt der Jacobi-Matrix $g_x$ mit $x'$ bezeichnet. Eine uniforme Schranke der Inversen, eine kompakte Einschließung in der regulären Umgebung und kontrollierte Startdaten erlauben die schrittweise Fortsetzung. Für $g=z^2-x$ verschmelzen die beiden Äste bei $x=z=0$. Dort scheitert diese Begründung. Die Diodenrechnung grenzt den tatsächlich durchlaufenen Ast [C21 · Bleibt die Diodenspannung vor der Falte?](../lehrbuch_numerische_simulation.md#fb-befunddiode) ein.

### B.2.3 · Eine schnelle Störung über viele Schritte

Im Reaktionsversuch aus Kapitel 1 genügt es, die Differenzmode zu betrachten. Sie erfüllt $d'=-a d$ mit $a=1000\,\mathrm{s^{-1}}$. Zwei Bahnen mit verschiedenen Anfangsdaten haben nach einem exakten Schritt den Abstand $e^{-ah}|\delta_0|$. Bei einem linearen Einschrittverfahren beträgt der Abstand nach $n$ Schritten $|R(-ah)|^n|\delta_0|$. Dies folgt durch Subtraktion der beiden Schrittgleichungen und Induktion. Für eine feste Schrittweite wachsen Anfangsstörungen genau dann nicht an, wenn $|R(-ah)|\le1$. Für das Abklingen jeder Anfangsstörung muss der Betrag echt kleiner als eins sein.

Bei $h=3\,\mathrm{ms}$ gilt für den expliziten Euler-Schritt $R=1-ah=-2$. Die Vorzeichen wechseln, und jeder Schritt verdoppelt den Betrag. Impliziter Euler hat $R=1/(1+ah)=1/4$. Die schnelle Störung klingt ab, jedoch langsamer als mit dem exakten Faktor $e^{-3}$. Diese drei Zahlen erklären, weshalb ein bestandener Stabilitätstest noch eine Prüfung des zeitlichen Fehlers braucht. Das Labor `beispiele/reaktionen.py` vergleicht die gerechneten Einzelkonzentrationen, die daraus gebildete Differenz und beide Verstärkungsfaktoren.

**Warum der Astparameter zählt.** Beim Beispiel $z^2-x=0$ wächst $|\mathrm dz/\mathrm dx|=1/(2|z|)$ auf jedem der beiden offenen Äste ohne Grenze, wenn $z$ gegen null geht. Die Kurve selbst lässt sich glatt durch $z=s,\ x=s^2$ parametrisieren. Das ist eine Fortsetzung der geometrischen Lösungskurve. Ob eine physikalische, in der Zeit orientierte DAE-Lösung die Falte erreicht oder passiert, entscheidet zusätzlich ihre Differentialgleichung. Kapitel 13 liefert für die konkrete Anregung der Diode eine eigene Astschranke.

<a id="fb-absB-3"></a>

## B.3 · Intervallarithmetik für dichte Polynomausgaben

### B.3.1  Vom Näherungspolynom zur garantierten Schranke

Bei Radau entsteht das Stufenpolynom aus der Kollokation. RK45 besitzt in SciPy eine quartische dichte Ausgabe. Bei BDF entsteht das Interpolationspolynom aus der verfügbaren Differenzenhistorie in der aktuellen Ordnung. Übersetzen Sie die Koeffizienten mitsamt ihrer Rundungsunsicherheit in eine gemeinsame Variable $s=(t-t_n)/h$. Für $p(s)=\sum a_ks^k$ liefert das Horner-Schema mit nach außen gerundeten Intervalloperationen eine Einschließung aller Werte von $p$ auf einem Teilintervall $I$. Intervallkoeffizienten benötigen dieselbe Rundung.
Betrachten wir $p(s)=s^2-s+3/16$, das die Nullen 1/4 und 3/4 besitzt. Auf $[0,1]$ ergibt Horner zunächst die grobe Hülle $[-13/16,3/16]$. Auf $[1/8,3/8]$ haben die Funktionswerte an den Grenzen verschiedene Vorzeichen und $2I-1$ liegt strikt unter null. Damit ist die erste Wurzel isoliert. Die Unterteilung schärft sowohl die Werte- als auch die Ableitungsaussage.

### B.3.2  Die zusätzliche Schranke für die wirkliche Bahn

Der tatsächliche Zustand $x$ hat einen zweiten Fehlerweg. Kennt man einen Defekt $\|p'-f(t,p)\|\le d$ in physikalischer Zeit, eine Anfangsschranke $e_0$ und eine Lipschitz-Konstante $L>0$ in einem umschließenden Gebiet, folgt $\|x(t)-p(t)\|\le e^{Lt}e_0+d(e^{Lt}-1)/L$ für die seit Schrittbeginn verstrichene Zeit. Für $L=0$ gilt $e_0+dt$. Erst mit dieser zusätzlichen Hülle darf man aus dem eingeschlossenen numerischen Polynom auf die modellierte Bahn schließen. Bei DAEs kommt die Kontrolle der algebraischen Bindungen hinzu.

[FLINT, Einschließung einfacher Wurzeln](https://flintlib.org/doc/tutorials/numerics/interval-newton.html) · [Fehlerschranken im Lehrversuch](../lehrbuch_numerische_simulation.md#t1-k2).

<a id="fb-absB-4"></a>

## B.4 · Python- und C++-Schnittstellenverträge

### B.4.1  Ein identischer ODE-Vertrag für zwei Implementierungen

Der Versuch $y'=-2y,\,y(0)=1$ hat einen unabhängigen Endwert $e^{-2}$. Die ausführbare Python-Schnittstelle übergibt eine Funktion und den vollständigen Anfangszustand. Die vom Integrator ausgewählten Zwischenzeiten dürfen sich wiederholen, etwa bei einem verworfenen Schritt.

```python
from math import exp
from argesim_benchmarks.ivp import InitialValueProblem
from argesim_benchmarks.runtime import solve_ivp

problem = InitialValueProblem(lambda t, y: (-2*y[0],),
                              0.0, (1.0,), 1.0)
run = solve_ivp(problem, "rk4", options={"step": 0.01})
assert abs(run.final_state[0] - exp(-2.0)) < 1e-8
```

Als C++20-Gegenstück eignet sich eine Modellsignatur mit festen Ausgabespeichern. Der folgende ausführbare Lehrtest prüft das Modell an einem Zwischenzustand. Der vollständige Integrator ist hier die Python-Referenz.

<a id="revision-ab-01"></a>

Der folgende Block ist die kompilierbare Quelldatei `rechenlabor/rhs_vertrag.cpp`. Die Gegenprobe extrahiert beim Buchtest den abgedruckten Block, vergleicht ihn bytegenau mit der Datei, übersetzt ihn mit C++20 und führt ihn aus. Der Test prüft die Rate am Zwischenzustand und den unveränderten Eingabewert.


```cpp
#include <array>
#include <cassert>
#include <span>

void rhs(double, std::span<const double, 1> y,
         std::span<double, 1> rate) { rate[0] = -2.0 * y[0]; }

int main() {
    std::array<double, 1> y{0.5}, rate{};
    rhs(0.25, y, rate);
    assert(rate[0] == -1.0 && y[0] == 0.5);
}
```

### Ein Endwertbudget für die Rechnung ohne Zusatzpakete

Der skalare Laboraufruf in `rechenlabor/rk4_vertrag.py` realisiert dieselbe Anfangswertaufgabe mit klassischem RK4. Für einen Schritt mit $h=0{,}01$ gilt $y_{n+1}=R(-2h)y_n$, wobei $R$ das Taylorpolynom vierten Grades der Exponentialfunktion ist. Da $0<R(-2h),e^{-2h}<1$, beträgt die Differenz der Potenzen nach $N$ Schritten höchstens $N|R(-2h)-e^{-2h}|$. Der Taylorrest auf der negativen reellen Achse liefert somit $N(2h)^5/120$. Für $N=100$ sind das rund $2{,}67$ mal $10^{-9}$. Der Test addiert eine Rundungsreserve von 32 Einheiten am letzten Binärplatz von eins pro Schritt. Auf diese Weise lässt sich ein zu großer Endfehler bis zum Fehler eines einzelnen Schrittes zurückverfolgen.

### B.4.2  Was der Aufrufer beobachten kann


<a id="revision-ab-02"></a>

Die Python-API `InitialValueProblem` verlangt einen endlichen, nichtleeren Anfangszustand und überprüft beim Auswerten die Länge und Endlichkeit der Ableitung. Als Negativprobe erhält sie einen NaN-Startwert und anschließend eine Modellfunktion mit zwei Ableitungen für einen einzigen Zustand. Beide Aufrufe müssen zurückgewiesen werden. Das skalare RK4-Lehrskript prüft den integrierten Endwert und sein Fehlerbudget. Der C++20-Block verwendet Speicher mit fester Länge eins und prüft einen gültigen Einzelaufruf. Eine API mit dynamischen Puffern müsste deren Größe an ihrer eigenen Aufrufgrenze prüfen.


## B.5 · Eine Einschließung mit exakter Arithmetik nachrechnen

Für das Polynom $q(s)=s^2-s+3/16$ haben die Randwerte auf dem ganzen Schritt dasselbe Vorzeichen. Auf $[1/8,3/8]$ ist die Ableitung $2s-1$ hingegen durchgehend negativ, auf $[5/8,7/8]$ durchgehend positiv. In jeder der beiden Klammern wechseln die Funktionswerte das Vorzeichen. Stetigkeit liefert jeweils Existenz, strenge Monotonie liefert Eindeutigkeit. An den Mittelpunkten $1/4$ und $3/4$ verschwindet das Polynom exakt.

`beispiele/benchmarkbilanz.py` berechnet die benötigten Vorzeichen und Mittelpunkte als rationale Zahlen. Wer denselben Beweis mit Gleitkommaintervallen führt, muss jede Intervalloperation nach außen runden. Eine enge Nullstellenklammer des Ausgabepolynoms sagt etwas über die physikalische Kontaktzeit, sobald zusätzlich der in B.3 hergeleitete Bahnfehler und eine untere Schranke für die Durchgangsgeschwindigkeit vorliegen.

**Übertragung in C++.** `rechenlabor/rhs_vertrag.cpp` enthält das vollständige Beispiel aus B.4. Es lässt sich aus dem entpackten Paket mit `c++ -std=c++20 rechenlabor/rhs_vertrag.cpp -o rhs_vertrag` übersetzen. `./rhs_vertrag` prüft, dass die Ausgabe den erwarteten Wert trägt und die übergebene Eingabe ihren Wert behält. Der Python-Test zum Endwert prüft zusätzlich die Integration bis zur vereinbarten Endzeit.

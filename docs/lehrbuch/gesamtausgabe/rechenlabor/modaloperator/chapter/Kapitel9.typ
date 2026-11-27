#let diff = $∂$
#let teal = rgb("#087b74")
#let ink = rgb("#182d38")
#let soft = rgb("#586a70")
#set page(paper: "a4", margin: (x: 20mm, top: 21mm, bottom: 20mm),
  header: context [
    #set text(font: "Noto Sans", size: 8pt, fill: soft)
    NUMERISCHE SIMULATION DYNAMISCHER SYSTEME #h(1fr) KAPITEL 9
    #v(2pt)#line(length: 100%, stroke: 0.45pt + rgb("#aac3c0"))
  ],
  footer: context [
    #line(length: 100%, stroke: 0.4pt + rgb("#b9cac7"))#v(4pt)
    #set text(font: "Noto Sans", size: 7.8pt, fill: soft)
    ARGESIM · Vergleichsstudie zu PR 91 #h(1fr) #counter(page).display("1")
  ])
#set text(font: "Noto Serif", size: 12pt, fill: ink, lang: "de", hyphenate: true)
#set par(justify: true, leading: 0.68em, spacing: 1.02em)
#set block(spacing: 1.02em)
#set heading(numbering: none)
#show heading.where(level: 1): it => block(above: 1mm, below: 5mm)[
  #set text(font: "Noto Sans", size: 29pt, weight: "bold", fill: ink, hyphenate: false)
  #set par(justify: false, leading: 0.23em)
  #it.body
]
#show heading.where(level: 2): it => block(above: 0pt, below: 4mm)[
  #set text(font: "Noto Sans", size: 21pt, weight: "bold", fill: ink, hyphenate: false)
  #set par(justify: false, leading: 0.32em)
  #it.body
]
#show strong: set text(weight: "bold", fill: ink)
#show link: set text(fill: teal)
#show raw: set text(font: "Noto Sans Mono", size: 10pt)
#set table(inset: (x: 5pt, y: 4pt), stroke: none,
  fill: (x,y) => if y == 0 {rgb("#d8eae7")} else if calc.even(y) {rgb("#f1f6f5")} else {white})
#show table: set text(font: "Noto Sans", size: 10pt)
#show table: set par(justify: false, leading: 0.4em)
#show table.cell.where(y: 0): set text(weight: "bold")
#set figure(gap: 4pt)
#show figure.caption: set text(font: "Noto Sans", size: 9pt, fill: soft)
#show figure.caption: set par(justify: false)
#show math.equation.where(block: true): set block(above: 0.72em, below: 0.72em)

= Wie viel Physik muss ein neuronaler Operator lernen?
<wie-viel-physik-muss-ein-neuronaler-operator-lernen>
#strong[Ergänzung zu Kapitel 9.43 · Numerische Simulation dynamischer Systeme]

Zwei dünne, übereinanderliegende Platten können Wärme über ihre gemeinsame Fläche austauschen. Die Ränder halten wir auf der Referenztemperatur null. Zu Beginn erwärmen wir nur die untere Platte in der Mitte. Wie viel von diesem Muster finden wir wenig später in der oberen Platte wieder? Diese Frage ist anspruchsvoller, als zwei plausible Temperaturbilder zu zeichnen. Sie verlangt, dass das Modell den Einfluss eines Feldes auf das andere richtig wiedergibt.

#figure([#box(width: 98%, image("figures/austausch.png"));],
  caption: [
    Analytische Referenz für den Sinusmodus \(1,1). Alle drei Bilder verwenden dieselbe Farbskala. Die Zahlen in den Bildern sind die Temperaturen im Mittelpunkt.
  ]
)

Im Versuch aus Abschnitt 9.43 variiert die anfängliche Temperaturverteilung. Ihre räumlichen Bausteine, die Materialeigenschaften und der Beobachtungszeitpunkt sind fest. Eine überraschende Gegenprobe besteht darin, dem Modell nur die sechs räumlichen Bausteine zu verraten. Wie viel Wärme zwischen den Platten fließt, muss es weiterhin aus Beispielen bestimmen.

#strong[Gemessener Ausgangspunkt.] Auf 32 ungesehenen Feldpaaren reproduziert diese Konstruktion mit 24 gelernten Zahlen relative Feldfehler von $"2,55" dot.op 10^(- 8)$ und $"2,53" dot.op 10^(- 8)$. Beträgt der Fehler auch dann so wenig, wenn wir ein anderes Muster aufprägen? Ein Versuch mit drei neuen Moden, ein Versuch mit anderem Material und ein Versuch mit längerer Beobachtungszeit geben drei verschiedene Antworten.

#strong[Gesamtlaufzeit.] Die vollständige Ausgangsstudie dauerte 12 min 39,33 s. Für 32 neue nominale Feldpaare brauchte der einsatzbereite Modaloperator im laufenden Prozess 0,34 ms, D2Q5-LBM 12,60 ms. Die Tabellen ab Seite 7 zeigen auch Prozessstart, Neutraining und die Kavitätsmessungen.

#pagebreak()
== Von der Wärmebilanz zur exakten Gegenprobe
<von-der-wärmebilanz-zur-exakten-gegenprobe>
Auf dem Einheitsquadrat $Omega = (0 , 1)^2$ seien $u$ und $v$ die Temperaturabweichungen. Höhere Temperatur im Nachbarfeld führt lokal zu einem positiven Wärmestrom. Mit Diffusivitäten $d_u , d_v > 0$ und Austauschrate $kappa gt.eq 0$ folgt

$ diff_t u = d_u Delta u + kappa (v - u) , #h(2em) diff_t v = d_v Delta v + kappa (u - v) , #h(2em) u = v = 0 quad upright("auf ") diff Omega . $

Multiplikation mit $u$ bzw. $v$, Integration und partielle Integration liefern eine Kontrolle für das Vorzeichen der Kopplung. Der Randterm verschwindet und $u (v - u) + v (u - v) = - (u - v)^2$. Damit gilt

$ 1 / 2 thin frac(d, d t) (parallel u parallel_2^2 + parallel v parallel_2^2) = - d_u parallel nabla u parallel_2^2 - d_v parallel nabla v parallel_2^2 - kappa parallel u - v parallel_2^2 . $

Der Ansatz $phi.alt_(m n) = sin (m pi x) sin (n pi y)$ erfüllt die Randwerte. Zweimaliges Ableiten ergibt $Delta phi.alt_(m n) = - lambda phi.alt_(m n)$ mit $lambda = pi^2 (m^2 + n^2)$. Schreiben wir $(u , v) = sum_k phi.alt_k z_k$ mit $z_k = (a_k , b_k)^tack.b$, ergibt der Koeffizientenvergleich für jede Mode eine eigene Zweifeldgleichung

$ dot(z)_k = A_lambda z_k , #h(2em) A_lambda = mat(delim: "(", - lambda d_u - kappa, kappa; kappa, - lambda d_v - kappa) , #h(2em) z_k (T) = E_lambda (T) z_k (0) . $

Für die Gegenrechnung setzen wir $s = kappa + lambda (d_u + d_v) \/ 2$, $delta = lambda (d_v - d_u) \/ 2$ und $omega = (delta^2 + kappa^2)^(1 \/ 2)$. Bei $B = A_lambda + s I$ sind die Diagonaleinträge $delta , - delta$ und die Nebendiagonalen $kappa$. Die Kreuzterme heben sich beim Quadrieren auf, also $B^2 = omega^2 I$. Die geraden und ungeraden Glieder der Exponentialreihe liefern

$ E_lambda (T) = e^(- s T) [cosh (omega T) I + frac(sinh (omega T), omega) B] . $

Bei $omega = 0$ hat der Quotient den Grenzwert $T$. Für $(m , n) = (1 , 1)$ und $(d_u , d_v , kappa , T) = ("0,03" , "0,06" , "1,25" , "0,4")$ ergibt sich $E_11 = "0,5351233"$, $E_22 = "0,4299266"$ und $E_12 = E_21 = "0,2220552"$. Eine zusätzliche Einheit im unteren Feld erhöht das obere Feld im Mittelpunkt folglich um $"0,2220552"$. Das ist die Antwort, die der Kopplungstest abfragt.

#pagebreak()
== Vier Zahlen pro Mode aus Bildern bestimmen
<vier-zahlen-pro-mode-aus-bildern-bestimmen>
Das Training kennt die Moden $(1 , 1) , (2 , 1) , (1 , 2) , (2 , 2) , (3 , 1) , (1 , 3)$. Jede kann in beiden Feldern unabhängig angeregt sein. Sechs räumliche Basisfunktionen liefern also zwölf freie Anfangskoeffizienten pro Feldpaar. Der Modaloperator kennt die Basis, die Linearität und die Unabhängigkeit verschiedener Moden. Die vier Einträge jedes Übertragungsblocks sind frei.

Ein Quadratgitter mit $n$ Knoten je Achse hat Innenindizes $i = 1 , dots.h , n - 2$. Für auflösbare Frequenzen gilt $sum_i sin (m pi i \/ (n - 1)) sin (p pi i \/ (n - 1)) = (n - 1) delta_(m p) \/ 2$. Die Identität folgt aus $2 sin a sin b = cos (a - b) - cos (a + b)$ und der endlichen geometrischen Summe der komplexen Exponentialfunktionen. Das zweidimensionale Skalarprodukt zerfällt in ein Produkt dieser Summen. Daraus folgt für ein abgetastetes Bild $f$

$ hat(f)_(m n) = 4 / (n - 1)^2 sum_(i , j = 1)^(n - 2) f_(i j) phi.alt_(m n) (x_i , y_j) . $

Für Mode $k$ schreiben wir die beiden Anfangsamplituden von Beispiel $j$ als Zeile $X_(j :)$ und die beiden Zielamplituden als $Y_(j :)$. Eine Matrix $M_k$ wirkt auf Spalten, also gilt in dieser Zeilenschreibweise $Y = X M_k^tack.b$. Minimieren wir $parallel X M_k^tack.b - Y parallel_F^2$, ergibt das Nullsetzen der Ableitung $X^tack.b X M_k^tack.b = X^tack.b Y$. Bei Rang zwei ist der Minimierer eindeutig. Das Labor löst das Ausgleichsproblem mit `lstsq`, ohne $X^tack.b X$ zu bilden.

$ hat(M)_k^tack.b = X^dagger Y , #h(2em) hat(bold(u)) (T) = sum_(k = 1)^6 phi.alt_k thin hat(M)_k vec(hat(u)_k (0), hat(v)_k (0)) . $

#strong[Warum können zwei Beispiele genügen?] Zwei Feldpaare liefern pro Mode zwei Zeilen mit je zwei Ausgangswerten. Sind ihre Anfangsamplituden linear unabhängig, identifizieren sie alle vier Einträge. Heizen beide Beispiele die Platten stets im gleichen Verhältnis, bleibt eine Eingangsrichtung unbeobachtet. Die Rangprüfung im Labor weist diesen Fall zurück. Beinahe parallele Zeilen verstärken Messfehler, selbst bei formal vollem Rang.

#strong[Wo endet diese Folgerung?] Ein reines Muster außerhalb der sechs Funktionen hat Projektion null. Der trainierte Operator gibt für dieses Muster auf einem auflösenden Gitter näherungsweise null zurück. Ein feineres Gitter liefert mehr Abtastpunkte für dieselben sechs Projektionen. Erst ein Zusammenhang zwischen #emph[verschiedenen] Moden gibt dem Modell eine Fortsetzungsvorschrift.

#pagebreak()
== Zwei Möglichkeiten, Physik zwischen den Moden zu teilen
<zwei-möglichkeiten-physik-zwischen-den-moden-zu-teilen>
#strong[Ein gelernter Generator.] In $A_lambda$ tauchen über alle Moden dieselben drei Materialparameter auf. Bei bekanntem $T > 0$ und exakt beobachtetem Block gibt es eine direkte Herleitung. Da $E$ symmetrisch positiv definit ist, gilt $A = T^(- 1) log E$. Die Eigenzerlegung $E = Q thin upright(d i a g) (eta_i) thin Q^tack.b$ liefert $log E = Q thin upright(d i a g) (log eta_i) thin Q^tack.b$. Damit lesen wir $kappa = A_12$, $d_u = (- A_11 - kappa) \/ lambda$ und $d_v = (- A_22 - kappa) \/ lambda$ ab.

Im Experiment schätzen wir die drei Größen gemeinsam aus allen sechs Moden. Die Zielfunktion summiert $parallel E_lambda (T ; theta) z_j (0) - z_j (T) parallel_2^2$ über Beispiele und Moden. Eine nichtnegative Ausgleichsrechnung startet bei $("0,05" , "0,05" , "0,75")$. Der Ansatz nutzt die PDE-Form und die bekannte Trainingszeit. Bei der Vorhersage bekommt er nur den gewünschten Zeitpunkt. Die geschätzten Materialwerte bleiben fest. Auf den 96 Nominalfeldern ergibt der Fit $("0,02999999997" , thin "0,06000000005" , thin "1,25000000053")$. Die Modellklasse enthält hier das Gesetz des synthetischen Datengenerators. Der Transfer auf neue Frequenzen prüft diese Annahme innerhalb derselben PDE-Familie.

#strong[Ein Physik-Layer mit absichtlichem Näherungsfehler.] Für einen echten Residualversuch soll die Grundrechnung einen messbaren Fehler haben. Schreibe $D = - lambda thin upright(d i a g) (d_u , d_v)$ und $K = kappa mat(delim: "(", - 1, 1; 1, - 1)$. Ein Strang-Schritt führt nacheinander halbe Diffusion, vollen Austausch und halbe Diffusion aus. Mit $H = upright(d i a g) (e^(- lambda d_u T \/ 2) , e^(- lambda d_v T \/ 2))$ und $b = (1 - e^(- 2 kappa T)) \/ 2$ folgt

$ S_lambda (T) = e^(T D \/ 2) e^(T K) e^(T D \/ 2) = H mat(delim: "(", 1 - b, b; b, 1 - b) H . $

Die Austauschmatrix folgt aus den Eigenrichtungen $(1 , 1)$ und $(1 , - 1)$ mit Eigenwerten $0$ und $- 2 kappa$ für $K$. Eine diskrete Sinustransformation vom Typ I wendet $S$ auf #strong[alle] aufgelösten Moden an. Für $[D , K] = D K - K D$ ist der obere Nebendiagonaleintrag $lambda kappa (d_v - d_u)$. Kommutieren beide Matrizen, ist die Aufspaltung exakt. Ausmultiplizieren der drei Reihen ergibt die Terme $I + T (D + K) + T^2 (D + K)^2 \/ 2$. In Ordnung drei hat etwa $D^2 K$ den Koeffizienten $1 \/ 8$ statt $1 \/ 6$ und $D K D$ den Koeffizienten $1 \/ 4$ statt $1 \/ 6$. Das Zusammenfassen aller Terme ergibt den Splittingfehler. Der kubische Term von $S - E$ lautet

$ T^3 (- [D , [D , K]] \/ 24 + [K , [K , D]] \/ 12) . $

Diese Aussage gilt pro fester Mode für kleine $T$. Hohe Frequenzen vergrößern $lambda$. Ein großer Einzelschritt kann dort entsprechend ungenau werden. #link("https://doi.org/10.1137/0705041")[Strang \(1968)]

#pagebreak()
== Was die Modelle während des Trainings sehen
<was-die-modelle-während-des-trainings-sehen>
#figure(
align(center)[#table(
  columns: 2,
  align: (col, row) => (left,left,).at(col),
  inset: 6pt,
  [Modell], [Eingebaute Information und gelernter Anteil],
  [FNO / UNO / CoDA-NO],
  [FNO lernt Faltungen im Fourierraum. UNO wechselt hier zwischen zwei Auflösungen. CoDA-NO wendet Attention auf Feldvariablen an. Der PR verwendet für alle eine ungerade Fortsetzung und Rückprojektion am Rand.],
  [Modal24 / Generator3],
  [Sechs freie $2 times 2$-Blöcke bzw. drei gemeinsame Materialparameter. Beide Schätzungen sehen nur die Trainingsfeldpaare. Generator3 kennt zusätzlich die PDE-Form und $T$.],
  [Strang],
  [Bekannte $d_u , d_v , kappa , T$. Der Einzelschritt liefert die Vergleichsbasis für beide Residualmodelle.],
  [Strang + R24],
  [Addiert sechs gelernte Matrizen für den Rest $y - S x$. Die Korrektur ist außerhalb des bekannten Modenraums null.],
  [Strang + FNO],
  [Addiert das FNO derselben Breite wie im PR. Es lernt $(y - S x) \/ s_R$, mit $s_R$ als RMS des Trainingsrests. Bei Inferenz wird mit $s_R$ zurückskaliert. Der Ausgabekopf startet bei null.],
)]
)

#strong[Getrennte Daten.] Die drei PR-Seeds 42201, 42202 und 42203 erzeugen 96 Trainings-, 24 Validierungs- und 32 Testfeldpaare. Für die $j$-te Mode in der vorgegebenen Reihenfolge hat jeder Kanal unabhängige Standardnormalamplitude geteilt durch $j^("1,2")$. Training und Validierung laufen auf $13 times 13$. Dieselben Testkoeffizienten werden auf $13 times 13$ und $25 times 25$ ausgewertet. Alle Nominalfelder stimmen im Test elementweise mit dem PR-Generator überein. Die Feldpaare werden in Float32 gespeichert. Projektion, Matrixfit und spektrale Physik rechnen in Float64.

#strong[Optimierung.] Adam, Lernrate $"0,003"$, Batchgröße 16, 40 Epochen, Auswahl nach Validierungs-MSE. Das FNO-Residual darf bei Epoche null bleiben. Alle Vergleichsnetze werden von Grund auf trainiert. Sie nutzen die Originalimplementierungen aus NeuralOperator 2.0.0. Deren Modellklassen sind in den Primärarbeiten beschrieben. #link("https://arxiv.org/abs/2010.08895")[FNO] · #link("https://arxiv.org/abs/2204.11127")[U-NO] · #link("https://arxiv.org/abs/2403.12553")[CoDA-NO]

#strong[Drei Messgrößen.] $e_u$ und $e_v$ sind pro Kanal die Mittelwerte von $parallel hat(y)_j - y_j parallel_2 \/ parallel y_j parallel_2$ über 32 Feldpaare. Für $e_Delta$ setzen wir $u_0 = phi.alt_11$ fest, wechseln $v_0$ von null auf $phi.alt_11$ und vergleichen die Änderungen im gesamten $u$-Feld. Der skalare Fehler $lr(|hat(M)_12 \/ E_12 - 1|)$ misst nur einen Matrixeintrag. Schreiben wir $Delta u_f = f_u (phi.alt_11 , phi.alt_11) - f_u (phi.alt_11 , 0)$ und $Delta u$ für die Referenz, so ist $e_Delta = parallel Delta u_f - Delta u parallel_2 \/ parallel Delta u parallel_2$. Bei verschwindender Referenzantwort protokolliert das Labor die absolute diskrete Norm.

#pagebreak()
== Feldfehler, Kopplung und Rechenzeit
<feldfehler-kopplung-und-rechenzeit>
#figure(
align(center)[#table(
  columns: 7,
  align: (col, row) => (auto,right,right,right,right,right,right,).at(col),
  inset: 6pt,
  [Modell], [Gewichte], [$e_u$ / %], [$e_v$ / %], [$e_Delta$ / %], [Fit / s], [Paar / ms],
  [FNO],
  [1034],
  [32,69],
  [46,00],
  [38,11],
  [2,87],
  [1,021],
  [UNO],
  [1034],
  [30,34],
  [44,38],
  [38,05],
  [3,13],
  [1,323],
  [CoDA-NO],
  [1051],
  [59,61],
  [70,50],
  [132,00],
  [60,51],
  [14,476],
  [Modal24],
  [24],
  [2,55·10⁻⁶],
  [2,53·10⁻⁶],
  [1,11·10⁻⁵],
  [0,00012],
  [0,008],
  [Generator3],
  [3],
  [2,55·10⁻⁶],
  [2,53·10⁻⁶],
  [1,11·10⁻⁵],
  [0,00352],
  [0,080],
  [Strang],
  [0],
  [1,50],
  [1,26],
  [0,23],
  [–],
  [0,095],
  [Strang + R24],
  [24],
  [2,55·10⁻⁶],
  [2,53·10⁻⁶],
  [1,11·10⁻⁵],
  [0,00080],
  [0,091],
  [Strang + FNO],
  [1034],
  [0,41],
  [0,91],
  [0,44],
  [2,79],
  [1,380],
)]
)

Alle Fehler sind Prozentwerte auf $25 times 25$. Bei den Netzen stehen arithmetische Mittel über die drei Initialisierungen 2027, 73 und 3917, bei den linearen und physikalischen Fits die Originaltrainingsfelder mit Seed 42201. Die Spalte für die Anpassung enthält bei Netzen den Median der drei Laufzeiten einschließlich Validierung und Wiederherstellung des gewählten Zustands. Bei direkten Fits ist sie der Median von 21 Anpassungen. Die Einzelfeldzeit umfasst ein komplettes Zweifeldpaar, drei Aufwärmaufrufe und 21 gemessene Aufrufe je Modell. Gitterabhängige Faktoren sind warm. Die CPU war ein Intel Xeon Platinum 8573C mit einem Rechenthread je Lauf. Die 42 Netztrainings benötigten zusammen 516 s Anpassungszeit. Datenerzeugung und Dateizugriffe liegen außerhalb der Messung.

#strong[Nachrechnung am ersten Kopplungsblock.] Bei Modal24 beträgt der relative Fehler des skalaren Eintrags $"2,2700" dot.op 10^(- 9)$. Für die PR-Feldgegenprobe beträgt er $"1,1107" dot.op 10^(- 7)$ als dimensionsloses Verhältnis. Zwei einzeln auf Float32 gerundete Zielbilder werden hier voneinander abgezogen. Dazu kommt die Projektion der gerundeten Eingangsbilder. Beide Fehler sind mit ihrem jeweiligen Nenner zu lesen.

#strong[Archiv und neuer Lauf.] Der PR meldet für FNO, UNO und CoDA-NO 38,11 %, 38,05 % und 132,04 % Kopplungsfehler. Die unabhängigen Neutrainings ergeben 38,11 %, 38,05 % und 132,00 %. Die kleine Abweichung bei CoDA-NO ist im Einzelvergleich sichtbar. Die Zahlen im Archiv und die hiesigen Zeiten wurden auf getrennten Ausführungen erhoben.

#strong[Was trägt der Physikanteil?] Strang allein macht bei $u$ rund $"1,50" thin %$ Fehler. Das FNO lernt den verbleibenden Rest bei unveränderter Zahl seiner trainierbaren Gewichte. Sein Trainings-RMS ist ein zusätzlicher gespeicherter Skalar. Der Kopplungsfehler steigt jedoch von 0,23 % auf 0,44 %. Strang + R24 erreicht auf den bekannten Moden den Genauigkeitsbereich des direkten Modaloperators. Algebraisch kann ein freier Residualblock dort den gesamten Fehler von $S_lambda$ aufnehmen.

#pagebreak()
== Was kostet der vollständige Lauf?
<was-kostet-der-vollständige-lauf>
#strong[12 min 39,33 s] dauerte die vollständige Wiederholung der Vergleichsstudie zu PR 91 auf einem CPU-Thread. Die Uhr lief vor dem Start des ersten Unterprozesses an und nach der Ausgabe des Kapitels ab. Alle 42 Netze wurden neu trainiert. Diese Dauer ist der Aufwand des gesamten Forschungsversuchs mit zwölf Testszenarien. Wer einen einzigen Operator für eine Anwendung braucht, trainiert nur das gewählte Modell.

#figure(
align(center)[#table(
  columns: 2,
  align: (col, row) => (auto,right,).at(col),
  inset: 6pt,
  [Messabschnitt], [Laufzeit],
  [Tests, Trainingsdaten, Fits, Auswertung und Ergebnisdateien],
  [12 min 35,71 s],
  [Tabellen, Abbildungen und PDF der Ausgangsstudie],
  [3,62 s],
  [Gesamte Ausgangsstudie, äußere Stoppuhr],
  [12 min 39,33 s],
  [Davon innerhalb der 42 Trainingsschleifen],
  [8 min 36,33 s],
  [Zusätzliche LBM- und Operatorvergleiche dieses Nachtrags],
  [3 min 18,47 s],
)]
)

Der Zusatzversuch umfasst das Übersetzen beider LBM-Kerne, drei frische Prozesse je Verfahren und Aufgabe, die Fehlerberechnung und die Gitterverfeinerung. Die beiden nacheinander gemessenen Versuchsblöcke ergeben zusammen #strong[15 min 57,81 s];. Installation, Archivtransfer und Satz dieser erweiterten Fassung liegen außerhalb der beiden Zeitfenster.

#strong[Was bedeutet Gesamtzeit für einen Anwender?] #emph[Neu] beginnt beim Start des Python-Prozesses. Ein lernendes Verfahren erzeugt seine Trainingsdaten, passt die Gewichte an, speichert und lädt den Zustand. Danach löst es sämtliche Feldaufträge, schreibt die Ergebnisse und beendet den Prozess. #emph[Geladen] umfasst denselben Prozessstart, das Laden vorhandener Gewichte, alle Feldaufträge, die Dateiausgabe und das Prozessende. Direkte Solver rechnen in beiden Fällen mit derselben bereits übersetzten Bibliothek. Deren gemeinsamer einmaliger Bau dauerte 0,91 s.

#emph[Warm] misst alle Feldaufträge hintereinander im laufenden Prozess bei Batchgröße eins. Angegeben ist der Median über neun vollständige Blöcke nach zwei Aufwärmblöcken, jeweils bis zur Rückgabe der Felder im Speicher. Je Kaltstartvariante wurde ein Durchlauf gemessen. Die Testeingaben liegen vor dem Prozessstart auf der Platte. Die analytische Bewertung geschieht anschließend außerhalb der Anwendungszeit.

#pagebreak()
== Lattice Boltzmann für zwei Diffusionsfelder
<lattice-boltzmann-für-zwei-diffusionsfelder>
Wie rechnet ein klassischer Solver dieselben Platten? Für jedes Feld speichern wir pro Knoten fünf Populationen $f_i$. Eine ruht, vier bewegen sich zum nächsten Achsennachbarn. Die Temperatur ist $phi.alt = sum_i f_i$. In der lokalen BGK-Kollision relaxieren die Populationen zum Gleichgewicht $w_i phi.alt$. Es gilt $w_0 = 1 \/ 3$ und $w_(1 , dots.h , 4) = 1 \/ 6$. Anschließend werden die Populationen um jeweils einen Gitterschritt verschoben.

$ f_i^(\*) = f_i + (w_i phi.alt - f_i) \/ tau , #h(2em) D = 1 / 3 (tau - 1 / 2) frac(h^2, Delta t) . $

Die Momentrelation $sum_i w_i e_(i x)^2 = 1 \/ 3$ liefert den Vorfaktor. Für jede Platte wählen wir $tau = 1 \/ 2 + 3 D Delta t \/ h^2$. Der Austausch erhält $u + v$ und multipliziert $u - v$ in einem halben Zeitschritt mit $exp (- kappa Delta t)$. Wir wenden ihn je zur Hälfte vor und nach dem Diffusionsschritt an. An den Rändern setzen wir die Populationen ungerade über die Gitterwand fort. Die Summe am Rand ist dadurch null. #link("https://doi.org/10.1103/PhysRevE.102.043305")[D2Q5-Diffusion und Reaktionssplitting]

#strong[Kontrollrechnung.] Wir halbieren $h = 1 \/ (n - 1)$ bei identischen acht Anfangsfeldpaaren und gleichem Endzeitpunkt. Mit $K = max (1 , ⌈ 6 max (D_u , D_v) thin T \/ h^2 ⌉)$ und $Delta t = T \/ K$ endet jede Rechnung genau bei $T$. Die Fehler beziehen sich auf die analytischen Sinuslösungen.

#figure(
align(center)[#table(
  columns: 4,
  align: (col, row) => (auto,right,right,right,).at(col),
  inset: 6pt,
  [Knoten je Achse], [LBM-Takte], [Fehler $u$ · %], [Fehler $v$ · %],
  [13],
  [21],
  [1,961],
  [1,073],
  [25],
  [83],
  [0,487],
  [0,264],
  [49],
  [332],
  [0,122],
  [0,066],
  [97],
  [1328],
  [0,030],
  [0,016],
)]
)

Mit jeder Verfeinerung fallen die Feldfehler näherungsweise um den Faktor vier. Der Zeitvergleich der nächsten Seite verwendet das 25er-Gitter. Die Raumschritte, Zeitschritte und Fehler der feineren Gitter gehören ausschließlich zur Konvergenzprüfung.

#pagebreak()
== Gleiche 32 Aufträge bei festem Material
<gleiche-32-aufträge-bei-festem-material>
Jeder Auftrag besteht aus den beiden Anfangstemperaturen auf $25 times 25$ Knoten. Gesucht sind beide Endfelder bei $T = "0,4"$. Alle Modelle erhalten dieselben 32 Testeingaben. D2Q5 führt 83 Takte je Feldpaar aus. Die Tabelle gibt die Gesamtzeit #strong[für alle 32 Paare] an. Der Fehler ist das Mittel aus den kanalweisen relativen Feldfehlern auf den gleichen 32 Paaren.

#figure(
align(center)[#table(
  columns: 5,
  align: (col, row) => (auto,right,right,right,right,).at(col),
  inset: 6pt,
  [Verfahren], [Neu · s], [Geladen · s], [Warm · ms], [Fehler · %],
  [D2Q5],
  [0,163],
  [0,152],
  [12,60],
  [0,345],
  [FNO],
  [7,391],
  [2,658],
  [41,02],
  [55,835],
  [UNO],
  [7,837],
  [2,743],
  [53,12],
  [18,036],
  [CoDA-NO],
  [77,266],
  [5,714],
  [726,89],
  [61,727],
  [Modal24],
  [0,531],
  [0,558],
  [0,34],
  [$"2,54" dot.op 10^(- 6)$],
  [Generator3],
  [0,561],
  [0,521],
  [4,06],
  [$"2,54" dot.op 10^(- 6)$],
  [Strang],
  [0,511],
  [0,495],
  [3,28],
  [1,381],
  [Strang + R24],
  [0,531],
  [0,482],
  [4,48],
  [$"2,54" dot.op 10^(- 6)$],
  [Strang + FNO],
  [7,383],
  [2,660],
  [58,47],
  [0,906],
)]
)

#strong[Ein einzelner Auftrag.] Vom Prozessstart bis zum ersten fertigen Feldpaar im Speicher vergingen bei einsatzbereitem D2Q5 0,120 s, bei Modal24 0,489 s und beim geladenen FNO 2,236 s. Die Messgrenze für diese drei Zahlen liegt vor der Ausgabe der restlichen Aufträge auf die Platte.

#strong[Warum ist die Modellwahl hier so folgenreich?] Bei Modal24 reichen sechs Projektionen und sechs kleine Matrixprodukte für das gesamte Zeitintervall. D2Q5 transportiert zehn Populationen an jedem Knoten durch 83 Takte. Die sechs trainierten Moden decken hier sämtliche Testeingaben ab. Der Abschnitt über unbekannte Moden prüft die Kosten dieses Vorwissens für die Vorhersagequalität.

Die Netze verwenden Seed 2027, 96 Trainings- und 24 Validierungsfelder. Beim Kaltstart lädt der Einstieg von Modal24 NumPy und SciPy, D2Q5 lädt NumPy und den nativen Kern. Der Unterschied gehört zur hier gemessenen Software. Die beiden Kaltstartspalten stammen aus unabhängigen Einzelmessungen.

#pagebreak()
== Wechselnde Parameter und wiederholte Aufträge
<wechselnde-parameter-und-wiederholte-aufträge>
Die zweite Serie verwendet wieder 32 Feldpaare auf $25 times 25$. Für jedes Paar ändern sich Diffusivitäten, Kopplung und Endzeit. D2Q5 übernimmt die vier gegebenen Zahlen und bestimmt damit die Taktzahl. Die beiden konditionierten Netze erhalten dieselben vier Werte zusätzlich zu den Anfangsfeldern. Strang verwendet die Parameter im Physikschritt.

#figure(
align(center)[#table(
  columns: 5,
  align: (col, row) => (auto,right,right,right,right,).at(col),
  inset: 6pt,
  [Verfahren], [Neu · s], [Geladen · s], [Warm · ms], [Fehler · %],
  [D2Q5],
  [0,161],
  [0,149],
  [15,00],
  [0,335],
  [FNO kond.],
  [7,448],
  [2,795],
  [46,81],
  [65,413],
  [Strang],
  [0,527],
  [0,507],
  [3,33],
  [1,257],
  [Strang + FNO kond.],
  [6,737],
  [2,856],
  [56,67],
  [1,312],
)]
)

Die Fehler sind wieder kanalweise relative Feldfehler gegen die analytische Lösung. Die Auswertung benutzt dieselben Eingaben und Parametersätze für alle vier Verfahren. Ein längerer Zeithorizont kostet D2Q5 weitere Takte. Ein einzelner Aufruf des konditionierten Netzes umfasst stets dieselbe Zahl von Schichten.

#strong[Ab welcher Stückzahl lohnt sich eine Anpassung?] Für einen dauerhaft laufenden Dienst mit $N$ einzeln eintreffenden Aufträgen setzen wir näherungsweise $T_i (N) = A_i + N ell_i$. Wir messen $A_i$ vom Start des Prozesses bis unmittelbar vor dem ersten Vorwärtsaufruf einschließlich einer nötigen Anpassung und $ell_i$ als warme Blockzeit pro Feldpaar. Bei $ell_m < ell_b$ ist ein Kandidat $m$ schneller als die Basis $b$, sobald

$ N > frac(A_m - A_b, ell_b - ell_m) . $

Für Modal24 gegenüber D2Q5 bei festem Material beträgt der gemessene Zeitvorteil pro zusätzlichem Feldpaar 0,383 ms. Das lineare Modell ergibt ab 890 Aufträgen eine kleinere Gesamtdauer für Modal24. Diese Schwelle ist eine Rechnung aus den Messwerten. Direkt gestoppt wurden die Blöcke mit 32 Feldern. Der Wert gilt für diesen Softwarestand, dieselbe Hardware und die Ausgabe im Speicher. Eine Anwendung muss zusätzlich angeben, welchen Feldfehler sie toleriert.

#pagebreak()
== Kavität im Kleinversuch und auf dem Vollgitter
<kavität-im-kleinversuch-und-auf-dem-vollgitter>
#strong[Direkter Vergleich am trainierten Einsatzpunkt.] Bei $upright(R e) = 1000$ und Deckelgeschwindigkeit $"0,1"$ sagen alle drei Verfahren die beiden Geschwindigkeitskomponenten auf $17 times 17$ nach genau 16 D2Q9-Takten voraus. Die 24 Testdichtefelder stimmen mit der veröffentlichten Testziehung überein. Die Spalte #emph[Geladen] verwendet beim Residual-FNO den veröffentlichten CP2-Modellzustand. #emph[Neu] erzeugt 96 Trainings- und 16 Validierungspaare mit der NumPy-Referenz und trainiert 80 Epochen.

#figure(
align(center)[#table(
  columns: 5,
  align: (col, row) => (auto,right,right,right,right,).at(col),
  inset: 6pt,
  [Verfahren], [Neu · s], [Geladen · s], [Warm · ms], [Fehler · %],
  [D2Q9],
  [0,211],
  [0,168],
  [2,41],
  [$"2,29" dot.op 10^(- 6)$],
  [D2Q9 NumPy],
  [0,176],
  [0,179],
  [43,28],
  [0],
  [Residual-FNO],
  [18,423],
  [2,780],
  [57,87],
  [0,070],
)]
)

Die Feldfehler beziehen sich auf den Geschwindigkeitsvektor im Fluidinneren gegen die unabhängige Ausführung der CP2-NumPy-Referenz. Deren eigener Fehler ist daher definitionsgemäß null. Der C++-Solver war warm um den Faktor 23,98 schneller als der geladene Residual-FNO. Beide Zeitangaben schließen das gesamte Vorhersageverfahren samt Startdichte und Ausgabe beider Komponenten ein.

#strong[Archiviertes Vollgitter.] Ein einziger CP2-Fall mit $257 times 257$ Knoten läuft bei $upright(R e) = 1000$ bis Takt 350 000, entsprechend $t^(\*) = "136,71875"$. Die Gesamtuhr umfasst MPI-Start, Rechenkern, Zusammenführen der Teilfelder und Dateiausgabe. Plattform AMD EPYC 9V45, ein Lauf je Prozesszahl.

#figure(
align(center)[#table(
  columns: 4,
  align: (col, row) => (auto,right,right,right,).at(col),
  inset: 6pt,
  [MPI-Prozesse], [Rechenkern · s], [Gesamt · s], [Speedup gesamt],
  [1],
  [49,389],
  [49,657],
  [1,00],
  [2],
  [28,456],
  [28,726],
  [1,73],
  [4],
  [21,998],
  [22,275],
  [2,23],
  [8],
  [19,346],
  [19,674],
  [2,52],
)]
)

Alle vier Endfelder haben dieselbe SHA-256-Prüfsumme. Acht Prozesse verkürzten den Gesamtauftrag um den Faktor 2,52. Das feste CP2-Netz akzeptiert ausschließlich das 17er-Gitter und wurde für 16 Takte trainiert. Das zusätzliche parametrisierte CP2-Modell deckt Gitter 17, 25, 33 und Endtakte 8, 16, 24 ab. Für diesen Residual-FNO fehlt ein validierter Lauf auf dem 257er-Gitter. Für sieben Felder auf diesem Gitter benötigt die räumliche 2D-Fourierschicht aus Kapitel 16 direkt 0,238 CPU-s, mit Grobgitterkorrektur 6,511 CPU-s. Die größten lokalen Abweichungen von D2Q9 betragen 66,9 % und 51,7 % der Deckelgeschwindigkeit. Die MPI-Tabelle misst die Wandzeit für den gesamten Endfeldauftrag. #link("https://github.com/5H3LL3H5/argesim-hyperposition-benchmarks/blob/72d670b51c94c8366ca5f1e070fc4730c78d0d52/docs/lehrbuch/studienbuch/material/cp2_genauigkeit/kavitaet.npz")[CP2-Modellzustand] · #link("https://github.com/5H3LL3H5/argesim-hyperposition-benchmarks/tree/5e73ade08e753223c59619118f23d24036bdc029/docs/lehrbuch/gesamtausgabe/rechenlabor/pdes_partitionierung")[Vollgitter-Messungen]

#pagebreak()
== Wie viele Trainingsfelder werden gebraucht?
<wie-viele-trainingsfelder-werden-gebraucht>
#figure([#box(width: 100%, image("figures/lerndaten.png"));],
  caption: [
    Lernkurven für den mittleren Kanalfehler auf den 32 nominalen Testfeldern. Links ist die Fehlerachse in Millionsteln eines Prozents angegeben, rechts logarithmisch in Prozent. Punkte stehen für ausgeführte Läufe.
  ]
)

Die Teilmengen $N = 2 , 8 , 24 , 96$ sind geschachtelte Präfixe derselben Trainingsfolge. Bei den Netzen bleibt die Initialisierung 2027 fest. Die 24 zusätzlichen sauberen Validierungsfelder werden für die Netzauswahl verwendet. Der direkte Modalfit und der Generator benötigen diese Auswahl nicht. Schon bei $N = 2$ misst Modal24 $"4,24" dot.op 10^(- 8)$ für $u$ und $"4,65" dot.op 10^(- 8)$ für $v$. Das ist ein Ergebnis genau dieser zwei unabhängigen Anregungen.

#strong[Ist jede Verbesserung ein Dateneffekt?] Bei Batchgröße 16 bedeuten 40 Epochen mit acht Feldern 40 Adam-Schritte, mit 96 Feldern dagegen 240. Deshalb wiederholen wir den Acht-Felder-Versuch mit 240 Schritten. Der Eintrag ist $100 (e_u + e_v) \/ 2$, jeweils mit derselben Initialisierung und denselben 32 Tests.

#figure(
align(center)[#table(
  columns: 4,
  align: (col, row) => (auto,right,right,right,).at(col),
  inset: 6pt,
  [Modell], [8 Felder · 40 Schritte], [8 Felder · 240 Schritte], [96 Felder · 240 Schritte],
  [FNO],
  [87,97],
  [60,32],
  [55,83],
  [UNO],
  [93,90],
  [18,43],
  [18,04],
  [CoDA-NO],
  [91,22],
  [83,71],
  [61,73],
  [Strang + FNO],
  [1,22],
  [0,97],
  [0,91],
)]
)

Bei gleichem Schrittbudget verarbeitet der Lauf mit acht Feldern 1 920 Beispielpräsentationen, der mit 96 Feldern 3 840. Die kleinen Teilmengen wurden mit einer Netzinitialisierung geprüft. Über die Streuung dieser Lernkurven bei anderen Initialisierungen geben die Punkte keine Auskunft.

#pagebreak()
== Was geschieht mit einer räumlich neuen Anregung?
<was-geschieht-mit-einer-räumlich-neuen-anregung>
Wir erzeugen weitere unabhängige Anfangskoeffizienten für $(3 , 2) , (2 , 3) , (4 , 1)$ mit Seed 62203. Ihre Laplace-Eigenwerte $13 pi^2$ und $17 pi^2$ kamen im Training nicht vor. Alle Moden sind bereits auf dem groben Gitter auflösbar. Der reine Test enthält nur die drei neuen Muster. Der Mischtest addiert bekannte und neue Anfangsfelder, jeweils mit dem Faktor $1 \/ sqrt(2)$. Die tatsächlich verbleibende Energie hängt danach von der Diffusion und vom Kanal ab.

#figure(
align(center)[#table(
  columns: 5,
  align: (col, row) => (auto,right,right,right,right,).at(col),
  inset: 6pt,
  [Modell], [rein · $u$], [rein · $v$], [gemischt · $u$], [gemischt · $v$],
  [FNO],
  [179,66],
  [630,33],
  [59,24],
  [90,91],
  [UNO],
  [197,86],
  [575,42],
  [66,79],
  [85,54],
  [CoDA-NO],
  [304,12],
  [1130,57],
  [87,30],
  [120,47],
  [Modal24],
  [100,00],
  [100,00],
  [31,75],
  [12,18],
  [Generator3],
  [2,65·10⁻⁶],
  [3,17·10⁻⁶],
  [2,57·10⁻⁶],
  [2,60·10⁻⁶],
  [Strang],
  [5,95],
  [9,06],
  [2,20],
  [1,75],
  [Strang + R24],
  [5,95],
  [9,06],
  [1,65],
  [1,11],
  [Strang + FNO],
  [2,53],
  [11,14],
  [0,80],
  [1,70],
)]
)

Die Tabelle zeigt den mittleren relativen Fehler in Prozent. Die Spalte „rein“ prüft eine Vorhersage ohne jeden bekannten Modenanteil. FNO, UNO, CoDA-NO und der FNO-Hybrid sind wieder Mittelwerte der drei nominal trainierten Netze. Große Prozentwerte sind bei stark gedämpften Zielmoden möglich. Im Rohdatensatz ist jeder Feldfehler einzeln verfügbar.

#strong[Erklärung aus der Projektion.] Zerlegen wir das Ziel orthogonal als $y = y_parallel + y_tack.t$, so beträgt der relative Fehler eines auf den bekannten Moden exakten Projektors $parallel y_tack.t parallel \/ sqrt(parallel y_parallel parallel^2 + parallel y_tack.t parallel^2)$. Beim reinen Test ergibt dies eins. Die hier gelernte Materialgleichung berechnet für eine neue Frequenz dagegen einen neuen Block aus $lambda$. Sie lässt sich auf genau dieselbe lineare PDE fortsetzen.

#strong[Erklärung aus dem Residual.] Strang + R24 fällt bei einem reinen unbekannten Muster auf die Physikrechnung zurück. Der FNO-Rest verändert auf den neuen Moden den Fehler in $u$ von 5,95 % auf 2,53 % und in $v$ von 9,06 % auf 11,14 %. Aus der guten Korrektur eines bekannten Musters folgt deshalb keine garantierte Verbesserung für beide neuen Felder.

#pagebreak()
== Gleiche Anfangsfelder, anderes Material
<gleiche-anfangsfelder-anderes-material>
Wir halten die Anfangsbilder fest und wechseln jeweils nur eine physikalische Einstellung. Bei „Diffusion“ tauschen $d_u$ und $d_v$ die Werte. In der Tabelle steht $100 (e_u + e_v) \/ 2$. Der Datensatz enthält außerdem $kappa = 0$, $T = 0$ und alle Einzelkanäle.

#figure(
align(center)[#table(
  columns: 6,
  align: (col, row) => (auto,right,right,right,right,right,).at(col),
  inset: 6pt,
  [Modell], [Diffusion], [$kappa = "0,45"$], [$kappa = "2,5"$], [$T = "0,2"$], [$T = "0,8"$],
  [FNO],
  [48,04],
  [70,83],
  [32,92],
  [59,91],
  [84,01],
  [UNO],
  [48,26],
  [68,18],
  [33,00],
  [57,31],
  [82,77],
  [CoDA-NO],
  [67,47],
  [53,12],
  [102,62],
  [49,71],
  [180,08],
  [Modal24],
  [34,22],
  [41,78],
  [43,88],
  [39,73],
  [104,06],
  [Generator3],
  [34,22],
  [41,78],
  [43,88],
  [2,54·10⁻⁶],
  [2,56·10⁻⁶],
  [Strang fest],
  [35,71],
  [41,58],
  [44,19],
  [39,61],
  [104,04],
  [Strang],
  [1,39],
  [0,25],
  [4,31],
  [0,22],
  [8,33],
  [Strang + R24],
  [2,81],
  [0,92],
  [2,64],
  [0,71],
  [5,67],
  [Strang + FNO],
  [2,54],
  [0,82],
  [3,17],
  [0,65],
  [6,49],
)]
)

Ein deterministisches Modell $f (x)$ erhält bei gleichen Bildern $x$ unter zwei Materialgesetzen dieselbe Eingabe. Aus der Dreiecksungleichung folgt $max_i parallel f (x) - G_i (x) parallel gt.eq parallel G_1 (x) - G_2 (x) parallel \/ 2$. Geänderte Parameter sind also eine Informationsfrage. Modal24 sowie die originalen Netze bekommen keine Materialangabe. Generator3 bekommt den neuen Zeitpunkt. Strang und seine Hybride erhalten auch die neuen Materialwerte. „Strang fest“ verwendet als Kontrolle überall die Nominalwerte.

#strong[Gleiche Information für beide Netze.] Ein zweiter Versuch trainiert FNO und Strang + FNO auf denselben 96 variablen Parametersätzen. Die vier unabhängigen Gleichverteilungen haben die Intervalle $["0,018" ; "0,045"]$, $["0,04" ; "0,09"]$, $["0,6" ; "1,8"]$ und $["0,25" ; "0,55"]$ für $d_u , d_v , kappa , T$. Vier zusätzliche Eingabekanäle tragen $(p_i \/ p_(i , 0) - 1) phi.alt_11$. Der Faktor erhält die Randbedingung. Beide Netze sehen identische Informationen, der Hybrid setzt sie zusätzlich in der Rechnung ein. 24 Validierungs- und 32 Testparameter werden mit unabhängigen Seeds gezogen.

#strong[Gemessen auf den 32 ungesehenen Parametersätzen.] Bei jeweils 1 050 trainierbaren Gewichten erreicht das konditionierte FNO 65,09 % mittleren Kanalfehler, der konditionierte Hybrid 1,30 %. Strang allein erreicht 1,26 %. Die Netzwerte sind Mittel über drei Initialisierungen. Hier erhöht der gelernte Rest den Fehler der Physikbasis geringfügig. Der große Abstand zum reinen FNO entsteht überwiegend durch den Physik-Layer.

Die Differenz Strang minus Hybrid beträgt -0,04 Prozentpunkte \(95-%-Bootstrapintervall -0,25 bis 0,18). Resampling-Einheit sind die 32 gepaarten Testfälle, nach Mittelung über die drei Netzstarts. Das Intervall beschreibt die Streuung der Testfälle bei diesen trainierten Modellen.

#pagebreak()
== Wie verändert Rauschen die Rangrechnung?
<wie-verändert-rauschen-die-rangrechnung>
Im ersten Rauschversuch stören wir ausschließlich die Trainingsziele. Eingaben, Validierung und Tests bleiben sauber. Das Rauschniveau $rho$ bezeichnet den erwarteten RMS des additiven Fehlers, relativ zum RMS des jeweiligen Zielkanals auf den inneren Gitterpunkten. Der Rand bleibt exakt null. Bei räumlich weißem Rauschen ziehen wir für jeden inneren Knoten eine unabhängige Normalvariable. Als Gegenprobe verteilen wir die gleiche erwartete Störleistung ausschließlich auf die sechs bekannten Sinusmoden.

#figure(
align(center)[#table(
  columns: 6,
  align: (col, row) => (auto,right,right,right,right,right,).at(col),
  inset: 6pt,
  [Modell], [1 % Pixel / 96], [5 % Pixel / 96], [5 % modal / 96], [5 % Pixel / 8], [5 % modal / 8],
  [Modal24],
  [0,055],
  [0,27],
  [1,11],
  [0,98],
  [3,84],
  [Generator3],
  [0,021],
  [0,10],
  [0,34],
  [0,26],
  [1,15],
  [Strang + R24],
  [0,055],
  [0,27],
  [1,11],
  [0,98],
  [3,84],
)]
)

Jeder Eintrag ist der mittlere Kanalfehler in Prozent. Bei den strukturierten Fits ist dies der Mittelwert über drei unabhängige Trainingsziehungen mit Seeds 42201, 42211 und 42221. Alle sehen dieselben sauberen Tests. Die Werte in den neuronalen Störversuchen stammen aus einem Start. Ein Datensatz pro Rauschrealisierung liefert hier deskriptive Vergleiche.

#strong[Warum hilft die Projektion gegen Pixelrauschen?] Für einen Modenvektor $phi.alt$ und unabhängige Knotenfehler mit Varianz $sigma^2$ hat der Projektionsfehler Varianz $sigma^2 \/ parallel phi.alt parallel_2^2 = 4 sigma^2 \/ (n - 1)^2$. Bei bereits modaler Störung fehlt diese räumliche Mittelung. Für eine Zielspalte mit homoskedastischen modalen Störungen der Varianz $tau^2$ gilt $upright(C o v) (hat(beta) divides X) = tau^2 (X^tack.b X)^(- 1)$. Bei den verwendeten feldabhängigen Skalen tritt an ihre Stelle $X^dagger upright(d i a g) (tau_j^2) (X^dagger)^tack.b$. Schlecht angeregte Richtungen verstärken das Rauschen.

#strong[Neuronale Läufe mit 5 % Pixelrauschen und 96 Trainingspaaren.] Die gemessenen mittleren Kanalfehler betragen 55,83 % für FNO, 18,09 % für UNO, 61,91 % für CoDA-NO und 0,33 % für Strang + FNO. Die saubere Validierung steht auch den verrauscht trainierten Netzen zur Verfügung.

#strong[Reichweite der Messung.] Untersucht wurden ein Quadrat, homogene Dirichlet-Ränder, räumlich konstante Koeffizienten, synthetische Anfangsfelder sowie Rauschen in getrennten Ein- und Ausgangsversuchen. Bei ortsabhängiger Diffusivität koppelt bereits der Diffusionsterm verschiedene Sinusmoden. Die unabhängige $2 times 2$-Regression verliert dann ihre exakte Grundlage. Das ist eine Folgerung aus der Modellgleichung. Ein räumlich veränderliches Materialgesetz wurde in dieser Messreihe nicht erprobt.

#pagebreak()
== Wenn bereits die Eingangsfelder rauschen
<wenn-bereits-die-eingangsfelder-rauschen>
Eine Kamera kann eine verrauschte Anfangstemperatur liefern, selbst wenn die spätere Referenzmessung präzise ist. Wir wiederholen die nominalen Fits mit einer Störung von 5 % ausschließlich am Eingang des Trainings. Validierung und Test erhalten wieder saubere Bilder. Der Vergleich mit dem Zielrauschen verwendet dieselben Zufallsziehungen für die Störung und skaliert diese jeweils auf den RMS des betroffenen Kanals.

#figure(
align(center)[#table(
  columns: 5,
  align: (col, row) => (auto,right,right,right,right,).at(col),
  inset: 6pt,
  [Modell], [sauber], [Ziel · Pixel], [Eingang · Pixel], [Eingang · modal],
  [Modal24],
  [2,54·10⁻⁶],
  [0,27],
  [0,18],
  [0,89],
  [Generator3],
  [2,54·10⁻⁶],
  [0,10],
  [0,095],
  [0,29],
  [Strang + R24],
  [2,54·10⁻⁶],
  [0,27],
  [0,18],
  [0,89],
  [FNO],
  [55,83],
  [55,83],
  [55,79],
  [–],
  [UNO],
  [18,04],
  [18,09],
  [18,00],
  [–],
  [CoDA-NO],
  [61,73],
  [61,91],
  [59,68],
  [–],
  [Strang + FNO],
  [0,91],
  [0,33],
  [0,90],
  [–],
)]
)

Die Zahlen sind mittlere Kanalfehler in Prozent bei 96 Trainingspaaren. Die drei direkten Fits mitteln über drei Trainingsziehungen. Bei den vier Netzen ist der Start 2027 mit seinem sauberen Kontrolllauf gepaart. Die letzte Spalte wurde für die direkten Fits ausgeführt. Sie beschränkt das Eingangsrauschen vollständig auf die sechs Trainingsmoden.

#strong[Warum macht die Seite des Fehlers einen Unterschied?] Betrachten wir eine Mode mit wahren zentrierten Eingangsamplituden $x$, Ziel $M x$ und beobachtetem Eingang $x + eta$. Für zentrierten Fehler mit $bb(E) [eta divides x] = 0$ verschwindet der Kreuzterm $bb(E) [x eta^tack.b]$. Der Minimierer $L$ des erwarteten quadratischen Vorhersagefehlers erfüllt die Normalgleichung

$ L thin bb(E) [(x + eta) (x + eta)^tack.b] = M thin bb(E) [x (x + eta)^tack.b] , #h(2em) L = M Sigma_x (Sigma_x + Sigma_eta)^(- 1) . $

In einer skalaren Richtung mit Varianzen $s_x^2 , s_eta^2$ verkleinert sich die Steigung um den Faktor $s_x^2 \/ (s_x^2 + s_eta^2)$. Das ist eine Aussage über den Populationsfit. Beim Zielrauschen mit verschwindendem bedingtem Mittelwert liegt die wahre Steigung dagegen weiterhin im Zentrum des Fits. Der Trainingsfehler allein zeigt diesen Unterschied nicht. Ein separater Versuch mit verrauschten Eingaben #emph[auch während der Vorhersage] wäre eine andere Messfrage.

#pagebreak()
== Rechenlabor und Aufgaben mit Lösungen
<rechenlabor-und-aufgaben-mit-lösungen>
#strong[1 · Welches Experiment identifiziert den Transfer?] Zwei Messungen regen eine Mode mit $(1 , 0)$ und $(2 , 0)$ an. Kann man bestimmen, wie stark das zweite Feld das erste heizt?

#emph[Lösung.] Beide Zeilen von $X$ sind parallel zur ersten Koordinatenachse. Auch bei perfekten Zielen bleibt die zweite Spalte von $M$ frei. Eine zusätzliche Anregung $(0 , 1)$ liefert unmittelbar diese Spalte. Mit $(1 , 0)$ und $(1 , 1)$ ergibt ihre Differenz dieselbe Antwort. Genau das nutzt die Feldgegenprobe.

#strong[2 · Welche Aussage prüft der Kopplungstest beim Materialtausch?] Erklären Sie, wie Modal24 beim Tausch der beiden Diffusivitäten den Kopplungstest bestehen und gleichzeitig große Feldfehler haben kann.

#emph[Lösung.] Der Tausch ändert $delta$ in $- delta$. Die Größe $omega$ und die Nebendiagonale $e^(- s T) kappa sinh (omega T) \/ omega$ bleiben gleich. Die Diagonaleinträge wechseln ihre Plätze. Die Kopplungsantwort kann korrekt sein, während die Beiträge des eigenen Anfangsfeldes erheblich abweichen. Deshalb protokolliert die Studie Feldfehler #emph[und] Kopplung.

#strong[3 · Wann beschädigt eine Residualkorrektur eine exakte Basis?] Setzen Sie $kappa = 0$, behalten Sie die bei $kappa = "1,25"$ gelernten Gewichte und interpretieren Sie den Rückgabewert der relativen Kopplungsmetrik.

#emph[Lösung.] Bei $kappa = 0$ gilt $K = 0$ und $S = e^(T D)$. Die exakte Antwort auf eine zusätzliche Anregung im anderen Feld ist null. Der Quotient für den relativen Kopplungsfehler ist undefiniert. Ein bei der Nominalkopplung gelernter additiver Rest kann eine scheinbare Antwort erzeugen. Das Labor gibt dafür eine absolute diskrete Norm und ein leeres relatives Feld aus. Im Nullkopplungstest wurden für Strang genau 0 und für Strang + R24 rund 0,00612 absolute L2-Abweichung auf dem 25er-Gitter gemessen.

#strong[Den Befund nachrechnen.] Der Paket-Einstieg ist `README.md`. Die Datei `results/structured.csv` enthält die direkten Fits und die Physikkontrollen, `results/neural.csv` alle Netzmessungen. Jede Zeile identifiziert Trainingsfall, Seed, Testszenario und Metrik. `results/weights/` enthält die gewählten Netzzustände. Das Labor prüft den Referenzgenerator unter anderem mit einem separaten DOP853-Lauf und einer Padé-Matrixexponentialfunktion.

#strong[Quellstand.] Grundlage ist der am 27. November 2026 gemergte Vergleich in Kapitel 9.43, Commit `72d670b5`. Originalgenerator und archivierte Messdatei liegen mit SHA-256-Prüfung im Rechenlabor. #link("https://github.com/5H3LL3H5/argesim-hyperposition-benchmarks/pull/91")[PR 91] · #link("https://github.com/5H3LL3H5/argesim-hyperposition-benchmarks/blob/72d670b51c94c8366ca5f1e070fc4730c78d0d52/docs/lehrbuch/gesamtausgabe/rechenlabor/codano/austausch.py")[Originalgenerator] · #link("https://github.com/5H3LL3H5/argesim-hyperposition-benchmarks/blob/72d670b51c94c8366ca5f1e070fc4730c78d0d52/docs/lehrbuch/gesamtausgabe/rechenlabor/codano/messung_kapazitaet.json")[Originalmessungen]

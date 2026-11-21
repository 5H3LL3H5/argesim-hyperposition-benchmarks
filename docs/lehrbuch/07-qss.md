# QSS als numerisches Integrationsverfahren

Beim expliziten QSS1 hält jede Komponente ihren zuletzt gemeldeten Wert $q_i$ fest. Die kontinuierliche Näherung $x$ entwickelt sich gemäß $\dot x=f(q)$ für ein autonomes Modell. Solange $q$ festliegt, ist die rechte Seite konstant und $x$ verläuft stückweise linear. Für jede aktive Komponente lässt sich der nächste Zeitpunkt bestimmen, an dem $|x_i-q_i|$ ihr Quantum $\Delta_i$ erreicht. Das kleinste dieser Zeitintervalle bestimmt den nächsten Termin. Bei simultanen Treffern sind alle betroffenen Komponenten zu behandeln. [KJ](literatur.md#kj)

**Zurück zum Fühler.** Wir arbeiten wieder mit $u'=-u$, $u(0)=1$. Bei QSS1 mit $\Delta=0{,}2$ beträgt die erste Steigung −1. Nach 0,2 Zeiteinheiten erreicht $x$ den Wert 0,8 und sendet $q=0{,}8$. Der nächste Abfall um 0,2 dauert $0{,}2/0{,}8=0{,}25$. Bei $s=0{,}45$ ist $q=0{,}6$. Für $s=0{,}5$ ergibt sich deshalb $x=0{,}6-0{,}05\cdot0{,}6=0{,}57$. Euler lieferte mit einem Schritt 0,5, RK4 lieferte 0,606771, die exakte Lösung 0,606531. Das ist eine gemeinsame Momentaufnahme. Die Verfahren haben dafür verschieden viel Arbeit geleistet.

![Abb. 8 · Links bleibt die ausgegebene Temperatur stückweise konstant und steuert die Steigung der grünen Kurve. Rechts beendet der markierte Eingang die alte Vorhersage. Die Raute bei 3/8 bezeichnet einen abwärts gerichteten Nulldurchgang zwischen zwei Ausgaben.](abbildungen/zustandsquantisierung.svg)

Die Schranke $|x_i-q_i|\leq\Delta_i$ betrifft die beiden **numerischen** Darstellungen. Für den Fehler zur exakten ODE-Lösung sind zusätzlich Empfindlichkeit und Beobachtungszeit maßgebend. Ein gedämpftes System kann Störungen abbauen. Bei einem Oszillator kann eine kleine Frequenzverschiebung über viele Perioden eine große Phasenabweichung erzeugen. [CK](literatur.md#ck)

## Was höhere Ordnung und implizite Quantisierung ändern

Bei explizitem QSS der Ordnung $p$ beschreibt ein Polynom vom Grad $p-1$ die ausgegebene Komponente. Die lokale kontinuierliche Näherung besitzt den Grad $p$. QSS2 gibt Wert und Steigung weiter. Eine gleichförmige Bewegung lässt sich so über eine ganze Flugphase darstellen. Bei QSS3 kommt die Krümmung des Ausgangs hinzu. Die Kosten für höhere Ableitungen und die Suche nach der frühesten zulässigen Nullstelle lohnen sich vor allem auf hinreichend glatten Abschnitten. Ein Reset unterbricht die Gültigkeit der Koeffizienten. [Q2](literatur.md#q2) · [Q3](literatur.md#q3)

| Familie | Idee und erster Einsatz | Was Sie im Versuch kontrollieren |
|---|---|---|
| QSS1, QSS2, QSS3, QSS4 | Konstantes, lineares, quadratisches bzw. kubisches Ausgangspolynom. Höhere Ordnung kann freie glatte Abschnitte verlängern. QSS4 ist hier eine Referenzerweiterung. | Fehler der Flugbahn und aller Wächter, zusätzliche Ableitungsauswertungen. |
| CQSS1 und logarithmische Quanten | CQSS1 benutzt zentrierte Zellen. Eine relative Quantisierung skaliert die zulässige Zustandsänderung mit der Amplitude und benötigt einen absoluten Sockel. | Bei geometrischen Problemen Energie **und** Phase prüfen. Bei abklingenden Signalen den kleinen Restwert separat messen. |
| BQSS1 und LIQSS1–3 | BQSS1 bezieht das lokale Gleichgewicht in die Wahl des Ausgangswerts ein. LIQSS behandelt die eigene linearisierte Rückkopplung jeder Komponente implizit. | Hilfreich bei starker diagonaler Dämpfung. Prüfen, ob gegenseitige Kopplung die Stabilität oder den Aufwand bestimmt. |
| eLIQSS1–3 und CheQSS1–3 | Die Differenz zwischen Zustand und Ausgang wird über das Intervall gezielter verteilt. CheQSS nutzt dafür verschobene Tschebyscheff-Polynome. | Bei häufigen Änderungen durch Nachbarn werden geplante Intervalle verkürzt. Die beiden Varianten erster Ordnung sind mathematisch gleich. |
| mLIQSS1–3 und LIQSS-BDF | mLIQSS behandelt ausgewählte stark gekoppelte Paare gemeinsam. LIQSS-BDF übergibt eine gewählte steife Teilmenge an einen BDF-Schritt. | Aufwand der Paar- bzw. Blocklösung, Schnittstellenfehler und verworfene Schritte. mLIQSS3 ist hier eine experimentelle Erweiterung. |

Die Grenze eines diagonalen Ansatzes zeigt sich bei einer Drehung der Koordinaten. Dabei entstehen aus zwei unabhängigen Modi mit Eigenwerten −1 und −1000 zwei Gleichungen mit Diagonale −500,5 und Kopplung +499,5. Dieselben Eigenwerte führen nun zu anders verteilten Komponentenereignissen. Ein QSS-Verfahren arbeitet in den tatsächlich gewählten Zustandskoordinaten. Der [Methodenkatalog](../SOLVER_METHODS.md) erklärt die Formeln und Grenzen jedes implementierten Verfahrens einzeln. [BQ](literatur.md#bq) · [LI](literatur.md#li) · [GL](literatur.md#gl)

## Wann QSS als erstes Experiment sinnvoll ist

Bestimmen Sie vor der Solverwahl eine **Beobachtungsgröße**. Beispiele sind die Geschwindigkeit nach dem letzten Stoß, der Zeitpunkt des dritten Schalters oder die Phase nach vier Perioden. Zwei numerische Ergebnisse können beim Endwert übereinstimmen und vorher völlig verschiedene Ereignisse durchlaufen haben.

| Merkmal des Modells | Erste Kandidaten | Entscheidung am Ergebnis |
|---|---|---|
| Vereinzelte lokale Änderungen, lange geradlinige Abschnitte | QSS2 und adaptives RK45 | Erreicht QSS bei gleichen Kontaktzeiten und Rücksetzwerten sein Ziel mit weniger Arbeit? C12 liefert ein positives Beispiel. |
| Glatte, breit gekoppelte Schwingung | RK4 bei bekanntem Raster, sonst RK45; QSS2 als Vergleich | Phase und Amplitude über die volle Dauer messen. Der analytische Oszillator verfehlte mit QSS2 das hier vorgegebene Ziel bei allen drei Quanten. |
| Schneller, überwiegend diagonaler Zerfall bei langsamer Beobachtung | LIQSS/eLIQSS, ESDIRK oder Radau | Schnelle Anfangsschicht und späte Messwerte prüfen. Zulässigen Endfehler, Arbeit und Matrixaufwand gemeinsam lesen. |
| Starke gekoppelte Steifheit mit Schaltern | Radau, ESDIRK, BDF; geeignet gekoppelte QSS-Variante als Versuch | Zahl, Reihenfolge und Zeiten der Schaltungen sowie beide Endzustände testen. C05 zeigt Unterschiede sogar zwischen impliziten Verfahren. |
| Unaufgelöste algebraische Nebenbedingung | Residualverfahren für die passende Indexklasse | Startkonsistenz, Residuum und unabhängige Trajektorie prüfen. Eine QSS-DAE-Konstruktion erfordert eine eigene Behandlung der algebraischen Gleichung. |

Die publizierte Stand-alone-QSS-Architektur kann über einen Abhängigkeitsgraphen nur die betroffenen Ableitungen aktualisieren. Der Python-Referenzsolver dieses Projekts wertet die rechte Seite vielfach als ganzen Vektor aus. Wenige Quantisierungsereignisse bedeuten daher weder null Arbeit noch einen allgemein gültigen Laufzeitvorteil. Messen Sie Aufwand pro erfülltem Ziel auf derselben Maschine. [FK](literatur.md#fk) · [Vergleichsdaten](../SOLVER_SELECTION.md)

> **Aufgabe 7.** Für den kühlenden Fühler soll die dimensionslose Unterschreitung von 0,7 lokalisiert werden. Bestimmen Sie mit QSS1 bei $\Delta=0{,}2$ den Zeitpunkt auf der kontinuierlichen Näherung, den Zeitpunkt der nächsten gesendeten Meldung und den exakten Durchgang. Welchen Fehler erzeugt ein Regler, der nur auf Meldungen schaut? [Lösung](10-loesungen.md#a7)

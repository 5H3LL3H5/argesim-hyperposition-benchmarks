# Lösungen und Kontrollrechnungen

<a id="a1"></a>**1 · Abkühlen.** Für die normierte Temperatur lautet der Euler-Faktor bei 0,5 min Zeitschritt $1-0{,}5/2=0{,}75$. Nach zweimaliger Anwendung ist $T=20+60\cdot0{,}75^2=53{,}75$ °C. Der Abstand zur exakten Lösung von 56,392 °C beträgt 2,642 K statt 6,392 K beim vollen Minutenschritt. Wird die physikalische Zeitkonstante um 5 % größer angenommen, steigt auch die modellierte Schwellenzeit um 5 %, von 2,19722 auf 2,30709 min. Beliebig kleine Rechenschritte beheben einen falsch bestimmten Modellparameter nicht. [Zur Aufgabe](01-anfangswertproblem.md)

<a id="a2"></a>**2 · Adaptive Fehlerskala.** Für die Spannung beträgt der Nenner $0{,}001+0{,}001\cdot5=0{,}006$ V. Der normierte Beitrag ist $0{,}0005/0{,}006=0{,}08333$. Beim Strom beträgt er $5/1=5$. Der RMS-Fehler ist $\sqrt{(0{,}08333^2+5^2)/2}\approx3{,}536$. Der Schritt wird verworfen. Ein reiner Spannungstest hätte ihn akzeptiert. Eine pro Komponente gewählte absolute Toleranz verhindert, dass die Einheit oder die Nähe zum Nullpunkt über das Ergebnis entscheidet. [Zur Aufgabe](02-runge-kutta.md)

<a id="a3"></a>**3 · Schneller Modus.** Für den Betrag des Euler-Faktors höchstens eins gilt $h\leq2/10000=0{,}0002$ s. Für tatsächliche Dämpfung muss der Schritt kleiner sein. Bei 1 ms ist $z=-10$. Vorwärts Euler ergibt −9, rückwärts Euler $1/11\approx0{,}09091$, Trapez $-2/3$. Exakt wäre $e^{-10}\approx0{,}0000454$. Auch ein stabiles Verfahren hat hier einen beträchtlichen relativen Fehler am schnellen Anteil. Entscheidend ist, wie stark dieser Anteil die verlangte Messgröße beeinflusst. [Zur Aufgabe](03-steifheit.md)

<a id="a4"></a>**4 · Zwei Raum-Zeit-Schranken.** Für Diffusion ergibt sich $h\leq\Delta x^2/(2\alpha)=0{,}02^2/(2\cdot10^{-4})=2$ s. Bei reiner Advektion fordert die Aufwind-Euler-Bedingung $h\leq\Delta x/a=0{,}2$ s. Nach Halbierung der Gitterweite gelten 0,5 s beziehungsweise 0,1 s. Sind beide Prozesse zugleich aktiv, muss die Stabilität des **kombinierten** Schemas geprüft werden. Bei additivem Vorwärts-Euler mit genau den beiden hergeleiteten Raumoperatoren und $a>0$ sichert $\nu+2r\leq1$ nichtnegative Gewichte. [Zur Aufgabe](04-pde.md)

<a id="a5"></a>**5 · Konsistenz.** Bei $t=2\ln 2$ s ist $e^{-t/2}=1/2$. Es folgen $u=2{,}5$ V, $i=1{,}25$ mA und $\dot u=1{,}25$ V/s. Ein statisches Paar aus Startspannung und Startstrom besteht den Maschentest ebenso wie eine zu schnell durchlaufene Folge sonst zulässiger Punkte. Ein Test der Differentialgleichung oder ein Vergleich zu unabhängigen Zeitpunkten deckt diese Fehler auf. [Zur Aufgabe](05-dae.md)

## Von der Ereignisfolge zum Versuchsentscheid

<a id="a6"></a>**6 · Neuer Eingang.** Beim Wechsel steht $x=1/8$, die letzte Meldung ist $q=0$. Mit Steigung −1 fällt $x$ in weiteren $1/8$ auf null, also bei $t=1/4$. Nach weiteren $1/4$ erreicht $x$ die untere Quantisierungsgrenze. Die erste Meldung erfolgt bei $t=1/2$, die zweite bei $t=3/4$. Der ursprünglich bei $1/4$ geplante numerische Ausgang wurde gelöscht. Dass der physikalische Wächter nun genau zu diesem Zeitpunkt auslöst, macht ihn nicht zu einem numerischen Ausgang. [Zur Aufgabe](06-devs.md)

<a id="a7"></a>**7 · Melden oder lokalisieren.** Bei $s=0{,}2$ stehen $x=q=0{,}8$. Bis $x=0{,}7$ fehlen 0,1 bei einer Geschwindigkeit von 0,8. Also kreuzt $x$ bei $s=0{,}325$. Die Quantisierermeldung $q=0{,}6$ folgt erst bei $s=0{,}45$. Die exakte ODE kreuzt bei $-\ln(0{,}7)=0{,}356675$. Ein Regler, der nur die Meldungen prüft, reagiert 0,125 dimensionslose Zeiteinheiten später als ein Wächter auf der numerischen Trajektorie. Gegenüber der exakten ODE beträgt die Verspätung etwa 0,093325. Zur Umrechnung in Minuten sind beide Differenzen mit zwei zu multiplizieren. [Zur Aufgabe](07-qss.md)

<a id="a8"></a>**8 · Schaltmodell.** Die größte normierte Zeitabweichung ist $0{,}4/1=0{,}4$. Für die Endzustände folgen $0{,}0024/0{,}006=0{,}4$ und $0{,}0072/0{,}006=1{,}2$. Das Maximum ist 1,2, die Zielgenauigkeit ist verfehlt. Der zweite Versuch hat bereits die falsche Ereignisanzahl. Die Abweichung der Endzustände darf diesen strukturellen Fehler nicht verdecken. Er erhält den eigenen Status `event_mismatch`. [Zur Aufgabe](08-argesim.md)

<a id="a9"></a>**9 · Was ein Endwert verdeckt.** Verspätet sich der erste Stoß um 10 ms und finden alle drei Stöße bis zur Endzeit statt, kann die Endgeschwindigkeit wieder $(0,0,0,1)$ betragen. Schon der Test $|t_1-1\ \mathrm{s}|\leq0{,}001\ \mathrm{s}$ deckt diesen Fehler auf. Für eine allgemeine Regression vergleicht man zusätzlich Namen und Reihenfolge aller Kontakte, alle drei Zeiten und die vier Endgeschwindigkeiten. Beim Kostenvergleich gehören neben vollständigen RHS-Auswertungen auch Jacobi-Berechnungen, Faktorisierungen, lineare Lösevorgänge, verworfene Schritte und Ereignissuche ins Protokoll. [Zur Aufgabe](09-praktikum.md)

## Begriffe und Formelzeichen

| Begriff | Bedeutung im Lehrbuch |
|---|---|
| Anfangswertproblem (ODE) | Gesuchter zeitlicher Verlauf eines Zustandsvektors bei gegebener Ableitungsvorschrift und gegebenem Startzustand. |
| PDE / Linienmethode | Feldgleichung mit partiellen Ableitungen. Diskretisierung des Ortes liefert ein zeitabhängiges ODE- oder DAE-System. |
| DAE / Residuum | Gleichung mit Differential- und algebraischen Anteilen. Das Residuum misst die Verletzung der eingesetzten Gleichung. Einheiten und Skalierungen sind zu beachten. |
| DEVS | Formalismus zur Beschreibung von Zuständen, Ausgaben, internen und äußeren Übergängen sowie Zeitfortschritt in diskreten Ereignissystemen. |
| QSS | Familie numerischer Verfahren, die Änderungen quantisierter Zustände als Auslöser für das Fortschreiten der Rechnung verwenden. |
| Wächter / Reset | Ein Wächter lokalisiert eine Bedingung, etwa den ersten gerichteten Nulldurchgang eines Spalts. Ein Reset legt Folgezustand und gegebenenfalls Modus fest. |
| Einschrittfehler / globaler Fehler | Fehler eines Schritts vom exakten Startwert aus bzw. Fehler nach Fortpflanzung vieler Schritte an einem festgelegten Beobachtungszeitpunkt. |
| A-Stabilität / L-Stabilität | Stabilität für die linke komplexe Halbebene bzw. zusätzliche vollständige Dämpfung sehr steifer linearer Modi. |
| RHS / Jacobi-Matrix | Rechte Seite $f$ der ODE bzw. ihre Matrix partieller Ableitungen nach den Zustandskomponenten. |
| $h$, $\Delta x$, $\Delta_i$ | Zeitliche Schrittweite, räumliche Gitterweite und Quantisierungsbreite der Komponente $i$. Sie besitzen unterschiedliche Einheiten. |
| $y$, $x$, $q$ im QSS-Kapitel | Exakte Lösung, kontinuierliche numerische Näherung und an die rechte Seite gemeldete quantisierte Näherung. |
| $S$, $L_j$, `rtol`, `atol` | Score, physikalischer Grenzwert für Messgröße $j$, relative und absolute lokale Integratortoleranz. |

**Leseschlüssel für den englischen Anhang.** *Guard* entspricht Wächter, *quantum* dem Zustandsquantum, *switch time* dem Schaltzeitpunkt und *right-hand-side evaluations* den Auswertungen der rechten Seite. *Accuracy miss* bezeichnet eine regulär beendete Rechnung außerhalb des Fehlerziels. *Timeout* und *solver error* sind gesonderte Ergebnisse.

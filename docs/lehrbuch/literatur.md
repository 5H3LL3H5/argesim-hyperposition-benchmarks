# Bibliographie und Quellenverzeichnis

Die Kurzbelege in den Kapiteln führen zu diesen Einträgen. Die Bücher erschließen die Theorie. Die Originalaufsätze dokumentieren, wann und für welche Problemklasse eine Methode entwickelt wurde. Für konkrete ARGESIM-Messwerte sind Versuchsdefinition und Rohdaten am Ende dieses Verzeichnisses maßgeblich.

### Lehrbücher und klassische Integration

<a id="hnw"></a>**HNW · E. Hairer, S. P. Nørsett und G. Wanner (1993).** *Solving Ordinary Differential Equations I: Nonstiff Problems.* 2. Auflage, Springer. Herleitung von Runge–Kutta-Verfahren, Ordnungsbegriffen und adaptiver Schrittweite. [DOI 10.1007/978-3-540-78862-1](https://doi.org/10.1007/978-3-540-78862-1)

<a id="hw"></a>**HW · E. Hairer und G. Wanner (1996).** *Solving Ordinary Differential Equations II: Stiff and Differential-Algebraic Problems.* 2. Auflage, Springer. Stabilitätsgebiete, implizite Stufen und die Rolle des Index bei DAEs. [DOI 10.1007/978-3-642-05221-7](https://doi.org/10.1007/978-3-642-05221-7)

<a id="fnc"></a>**FNC · T. A. Driscoll und R. J. Braun.** *Fundamentals of Numerical Computation*, fortgeschriebene Onlineausgabe. Der Abschnitt zur Linienmethode verbindet einen diskreten Ortsoperator mit einem Zeitintegrator. [Lehrbuch](https://fncbook.com/) · [The method of lines](https://fncbook.com/methodlines/)

<a id="lv"></a>**LV · R. J. LeVeque (2002).** *Finite Volume Methods for Hyperbolic Problems.* Cambridge University Press. Hintergrund zu Erhaltung, numerischen Flüssen, Aufwinddiskretisierung und Ausbreitungsgeschwindigkeiten. [DOI 10.1017/CBO9780511791253](https://doi.org/10.1017/CBO9780511791253)

<a id="bs"></a>**BS · P. Bogacki und L. F. Shampine (1989).** *A 3(2) pair of Runge–Kutta formulas.* Applied Mathematics Letters 2(4), 321–325. Das explizite Paar hinter dem hier verwendeten RK23. [DOI 10.1016/0893-9659(89)90079-7](https://doi.org/10.1016/0893-9659(89)90079-7)

<a id="dp"></a>**DP · J. R. Dormand und P. J. Prince (1980).** *A family of embedded Runge-Kutta formulae.* Journal of Computational and Applied Mathematics 6(1), 19–26. Eingebettete Formeln der Ordnungen fünf und vier. [DOI 10.1016/0771-050X(80)90013-3](https://doi.org/10.1016/0771-050X(80)90013-3)

<a id="kv"></a>**KV · A. Kværnø (2004).** *Singly diagonally implicit Runge–Kutta methods with an explicit first stage.* BIT Numerical Mathematics 44, 489–502. Abschnitt 3 des Autorenmanuskripts beschreibt das Paar ESDIRK 3/2a und seinen Stabilitätsparameter. [DOI 10.1023/B:BITN.0000046811.70614.38](https://doi.org/10.1023/B:BITN.0000046811.70614.38) · [Manuskript](https://www.math.ntnu.no/preprint/numerics/2004/N1-2004.pdf)

<a id="ida"></a>**IDA · SUNDIALS-Projekt.** *IDA Mathematical Considerations.* Technische Dokumentation zu DAE-Residuen, konsistenter Initialisierung, variablen BDF-Schritten und nichtlinearen Gleichungssystemen. Der Benchmark nutzt IDAS über CasADi. [Mathematik von IDA](https://sundials.readthedocs.io/en/latest/ida/Mathematics_link.html) · [CasADi-Integratoren](https://web.casadi.org/docs/#initial-value-problems)

## DEVS und QSS: von der Idee zum Solver

<a id="ze"></a>**ZE · B. P. Zeigler (1976).** *Theory of Modelling and Simulation.* Wiley. Historischer Ausgangspunkt für die formale Trennung von Modell, Kopplung und Simulator. [Bibliographischer Nachweis, ISBN 0471981524](https://books.google.com/books?vid=ISBN0471981524)

<a id="zl"></a>**ZL · B. P. Zeigler und J. S. Lee (1998).** *Theory of quantized systems: formal basis for DEVS/HLA distributed simulation environment.* Proceedings of SPIE 3369, 49–58. Zustandsquantisierung als Grundlage ereignisbasierter Kommunikation. [DOI 10.1117/12.319354](https://doi.org/10.1117/12.319354)

<a id="kj"></a>**KJ · E. Kofman und S. Junco (2001).** *Quantized-State Systems: A DEVS Approach for Continuous System Simulation.* Transactions of the Society for Computer Simulation International 18(3), 123–132. Originalquelle zu Hysterese, stückweiser Dynamik und DEVS-Realisierung. [Autorenfassung](https://www.fceia.unr.edu.ar/~kofman/files/qss.pdf)

<a id="q2"></a>**Q2 · E. Kofman (2002).** *A Second-Order Approximation for DEVS Simulation of Continuous Systems.* Simulation 78(2), 76–89. Führt lineare Ausgangspolynome und QSS2 ein. [DOI 10.1177/0037549702078002206](https://doi.org/10.1177/0037549702078002206)

<a id="qd"></a>**QD · E. Kofman (2003).** *Quantization-Based Simulation of Differential Algebraic Equation Systems.* Simulation 79(7), 363–376. Untersucht QSS- und QSS2-Konstruktionen für Index-1-DAEs. [DOI 10.1177/0037549703038881](https://doi.org/10.1177/0037549703038881)

<a id="hy"></a>**HY · E. Kofman (2004).** *Discrete Event Simulation of Hybrid Systems.* SIAM Journal on Scientific Computing 25(5), 1771–1797. Verbindet quantisierte kontinuierliche Dynamik mit diskreten Modellereignissen. [DOI 10.1137/S1064827502418379](https://doi.org/10.1137/S1064827502418379)

<a id="q3"></a>**Q3 · E. Kofman (2006).** *A Third Order Discrete Event Method for Continuous System Simulation.* Latin American Applied Research 36, 101–108. Entwickelt QSS3 und diskutiert Aufwand und Anwendungsbereich. [Volltext](https://www.fceia.unr.edu.ar/~kofman/files/qss3laar.pdf)

<a id="ck"></a>**CK · F. E. Cellier und E. Kofman (2006).** *Continuous System Simulation.* Springer. Umfassende Vertiefung zu dynamischen Modellen, klassischen Integratoren und Zustandsquantisierung. [DOI 10.1007/0-387-30260-3](https://doi.org/10.1007/0-387-30260-3)

## Steife QSS-Verfahren, Benchmarks und Datennachweise

<a id="bq"></a>**BQ · G. Migoni, E. Kofman und F. E. Cellier (2012).** *Quantization-based new integration methods for stiff ordinary differential equations.* Simulation 88(4), 387–407 (online 2011). Entwickelt BQSS für steife Rückkopplung. [DOI 10.1177/0037549711403645](https://doi.org/10.1177/0037549711403645)

<a id="li"></a>**LI · G. Migoni, M. Bortolotto, E. Kofman und F. E. Cellier (2013).** *Linearly implicit quantization-based integration methods for stiff ordinary differential equations.* Simulation Modelling Practice and Theory 35, 118–136. Beschreibt die Behandlung der lokalen Selbstkopplung in LIQSS. [DOI 10.1016/j.simpat.2013.03.004](https://doi.org/10.1016/j.simpat.2013.03.004)

<a id="fk"></a>**FK · J. Fernández und E. Kofman (2014).** *A stand-alone quantized state system solver for continuous system simulation.* Simulation 90(7), 782–799. Eigenständige Implementierung mit Abhängigkeitsgraphen und Vergleichen zu klassischen Integratoren. [DOI 10.1177/0037549714536255](https://doi.org/10.1177/0037549714536255)

<a id="gl"></a>**GL · M. Bergonzi, J. Fernandez und E. Kofman (online 2026).** *On general linearly implicit quantized state system methods.* Computational and Applied Mathematics 46, Artikel 1 (Bandjahr 2027). Verallgemeinert LIQSS und leitet zwei Unterfamilien her. [DOI 10.1007/s40314-026-03858-3](https://link.springer.com/article/10.1007/s40314-026-03858-3)

<a id="arg"></a>**ARG · Arbeitsgemeinschaft Simulation.** *ARGESIM Benchmarks.* Primärquellen zu Aufgaben, Varianten und Modellannahmen. Die reduzierten Versuche hier benennen jeweils Zeitfenster und Messgrößen. [Katalog](https://www.argesim.org/benchmarks) · [C05](https://www.argesim.org/benchmarks/c05) · [C12](https://www.argesim.org/benchmarks/c12) · [C19](https://www.argesim.org/benchmarks/c19) · [C21](https://www.argesim.org/benchmarks/c21)

### Daten, Abbildungen und Wiederholung

Die deutschsprachigen Abbildungen wurden für dieses Lehrbuch aus den genannten Modellgleichungen, der analytischen C05-Referenz und den archivierten Messwerten erzeugt. Das Abbildungsskript enthält die Gleichungen und Parameter der Lehrbeispiele. Die Messgrafik liest Versuch, Verfahren und Toleranzstufe direkt aus der archivierten CSV. [Abbildungsskript](../../scripts/lehrbuch_abbildungen.py) · [Benchmark-Protokoll](../../benchmarks/benchmark_solver_selection.py)

Die drei Vergleichsreihen besitzen eigene Gitter und Messprotokolle. Die Zahlen bezeichnen Konfigurationen und erlauben keine Addition zu einer Zahl verschiedener Modelle. Die C21-Diodenrechnung ist eine separate Validierung. [456 Konfigurationen](../evidence/qss-extension.csv) · [520 Konfigurationen](../evidence/qss-selection.csv) · [138 Konfigurationen](../evidence/rk23-devs.csv) · [C21-Diode](../evidence/c21-idas.json)

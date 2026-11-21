# Eigene Solververgleiche im Praktikum

Im ersten Versuch braucht man nur Python ab Version 3.10 und die Dateien des Repositorys. Führen Sie die Beispiele aus dem Projektverzeichnis aus. Die ODE-Schnittstelle akzeptiert eine Funktion, die einen Vektor von Ableitungen zurückgibt. Bei einer skalaren Gleichung bezeichnet das Komma in `(-y[0],)` einen Vektor mit genau einem Eintrag.

```python
from math import exp
from argesim_benchmarks import InitialValueProblem, solve_ivp

p = InitialValueProblem(lambda t, y: (-y[0],), 0, (1,), 1,
                        autonomous=True)
settings = {
    "rk4": {"step": 0.125},
    "rk23": {"rtol": 1e-5, "atol": 1e-8},
    "esdirk32": {"rtol": 1e-5, "atol": 1e-8},
    "qss1": {"quantum": 0.2},
    "qss2": {"quantum": 0.02},
}
for method, options in settings.items():
    r = solve_ivp(p, method, options=options)
    error = abs(r.final_state[0] - exp(-1))
    print(method, f"{error:.3g}", r.stats.rhs_evaluations)
```

**Versuchsprotokoll.** Legen Sie vor dem Start einen zulässigen Fehler fest, beispielsweise $10^{-4}$ bei $s=1$. Führen Sie die Rechnung aus und notieren Sie Fehler und rechte-Seiten-Auswertungen. Halbieren Sie für RK4 die Schrittweite dreimal und schätzen Sie die Ordnung. Halbieren Sie für QSS das Quantum. Vergleichen Sie erst innerhalb eines Verfahrens, dann zwischen den jeweils günstigsten bestandenen Einstellungen. Bei RK4 und $h=1/8$ sollten Sie rund $8{,}31\cdot10^{-7}$ Fehler sehen. Ein falscher Funktionsaufruf oder eine Verwechslung von $t$ und $s$ fällt damit sofort auf.

**Verändern Sie die Beobachtung.** Tauschen Sie das Abkühlmodell gegen $y'=(y_2,-y_1)$ mit Start $(1,0)$ und Endzeit 25 aus. Als Referenz dienen $(\cos t,-\sin t)$. Plotten Sie Phasenfehler und $y_1^2+y_2^2$ getrennt. Ein Zustand kann fast auf dem Einheitskreis liegen und trotzdem zur falschen Zeit am falschen Ort sein. Vergleichen Sie Ihr Ergebnis mit den vier archivierten Beobachtungszeiten. [Oszillator und Toleranzen](../SOLVER_SELECTION.md#what-the-new-experiment-measures)

## Ein ARGESIM-Experiment reproduzieren

Der folgende Ausschnitt benötigt SciPy und NumPy sowie die Paketquellen. Führen Sie `python -m pip install -e . numpy scipy` in einer geeigneten Python-Umgebung aus. Für das separate C21-DAE-Experiment lässt sich die optionale Abhängigkeit mit `python -m pip install -e '.[dae]'` ergänzen. Die archivierte Vergleichsreihe verwendete SciPy 1.17.0. Für eine Reproduktion einschließlich ihrer Bibliotheksversionen stehen diese im Messprotokoll.

```python
from benchmarks.benchmark_solver_extension import spheres

case = spheres()
for name, options in (("qss2", {"quantum": (0.005,) * 7}),
                      ("rk23", {"rtol": 1e-3, "atol": (1e-5,) * 7})):
    run, measured = case.run(name, options)
    assert run.final_time == case.end
    assert len(measured) == len(case.expected)
    score = max(abs(v-ref)/limit for v, ref, limit in
                zip(measured, case.expected, case.tolerances, strict=True))
    print(name, measured[:3], score, run.stats.rhs_evaluations)
```

Der C12-Fall kontrolliert intern die Reihenfolge der drei benannten Kontakte. Die ersten drei zurückgegebenen Werte sind die Zeiten, die nächsten vier die Endgeschwindigkeiten. Erwartet werden die Zeiten 1, 2 und 3 s und nur ein bewegter Körper am Ende. Durch Ändern der Startlücke in einer eigenen Modellkopie kann man prüfen, ob das Verfahren auf eine physikalische Änderung angemessen reagiert.

**Die gesamte Vergleichsreihe** lässt sich auf POSIX-Systemen mit folgendem Befehl erzeugen. Das Ergebnis besteht aus einer CSV mit Einzelmessungen und einer JSON mit Softwareumgebung, Quellhash und Prüfsumme. Ein Zeitlimit kann auf anderer Hardware andere Ergebnisse liefern. Für eine Wiederholung der publizierten Messung verwenden Sie den in den Quelldaten angegebenen Stand.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
python benchmarks/benchmark_solver_selection.py --profile rk23 --output rk23.csv
```

> **Aufgabe 9.** Formulieren Sie für C12 einen Test, der die letzte Geschwindigkeit korrekt finden kann, obwohl ein Fehler in der Stoßzeit vorliegt. Ergänzen Sie ihn um genau die Beobachtung, die diesen Fehler aufdeckt. Beschreiben Sie anschließend, welche Zusatzkosten beim Vergleich mit einem impliziten Verfahren berücksichtigt werden sollten. [Lösung](10-loesungen.md#a9)

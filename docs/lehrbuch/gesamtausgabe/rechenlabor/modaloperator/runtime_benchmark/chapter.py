"""Generate the runtime pages from the archived and newly timed measurements."""

import csv
import json
import math
from pathlib import Path

ARCHIVED = Path(__file__).with_name("archived")
NAMES = {
    "FNO-small": "FNO",
    "Strang-R24": "Strang + R24",
    "Strang-FNO": "Strang + FNO",
    "FNO-cond": "FNO kond.",
    "Strang-FNO-cond": "Strang + FNO kond.",
    "Cavity-FNO": "Residual-FNO",
    "D2Q9-NumPy": "D2Q9 NumPy",
}


def dec(x, digits=2):
    return f"{float(x):.{digits}f}".replace(".", ",")


def elapsed(x):
    minutes, seconds = divmod(float(x), 60)
    return f"{int(minutes)} min {dec(seconds)} s"


def percent(ratio):
    x = 100 * float(ratio)
    if 0 < x < 0.001:
        exponent = math.floor(math.log10(x))
        mantissa = dec(x / 10**exponent, 2).replace(",", "{,}")
        return f"${mantissa}\\cdot 10^{{{exponent}}}$"
    return dec(x, 3) if x else "0"


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def table(header, rows):
    lines = [header, ["---"] + ["---:"] * (len(header) - 1), *rows]
    return "\n".join("| " + " | ".join(row) + " |" for row in lines)


def job_table(rows):
    return table(
        ["Verfahren", "Neu · s", "Geladen · s", "Warm · ms", "Fehler · %"],
        [
            [
                NAMES.get(r["model"], r["model"]),
                dec(r["freshN_s"], 3),
                dec(r["readyN_s"], 3),
                dec(1000 * float(r["warmN_s"]), 2),
                percent(r["error_ready"]),
            ]
            for r in rows
        ],
    )


def runtime_text(directory):
    directory = Path(directory)
    study = json.loads((directory / "original_total.json").read_text())
    clocks = json.loads((directory / "timings.json").read_text())
    runs = read_csv(directory / "total_jobs.csv")
    by_problem = {
        p: [r for r in runs if r["problem"] == p]
        for p in ("diffusion", "family", "cavity")
    }
    d = {r["model"]: r for r in by_problem["diffusion"]}
    c = {r["model"]: r for r in by_problem["cavity"]}
    mpi = [
        json.loads((ARCHIVED / f"full-mpi-{r}.json").read_text()) for r in (1, 2, 4, 8)
    ]
    speedup = mpi[0]["launcher_wall_s"] / mpi[-1]["launcher_wall_s"]
    wall = study["wall_seconds"]
    comp = clocks["comparison_wall_s"]
    fourier = {
        row["familie"]: row for row in read_csv(ARCHIVED / "vollgitter_methoden.csv")
        if row["verfahren"] == "2D-Fourierschicht"
    }
    direct = fourier["2D-Fourieroperator direkt"]
    hybrid = fourier["2D-Fourieroperator korrektur"]
    pages = []

    pages.append(f"""## Was kostet der vollständige Lauf?

**{
        elapsed(wall)
    }** dauerte die vollständige Wiederholung der Vergleichsstudie zu PR 91 auf einem CPU-Thread. Die Uhr lief vor dem Start des ersten Unterprozesses an und nach der Ausgabe des Kapitels ab. Alle 42 Netze wurden neu trainiert. Diese Dauer ist der Aufwand des gesamten Forschungsversuchs mit zwölf Testszenarien. Wer einen einzigen Operator für eine Anwendung braucht, trainiert nur das gewählte Modell.

{
        table(
            ["Messabschnitt", "Laufzeit"],
            [
                [
                    "Tests, Trainingsdaten, Fits, Auswertung und Ergebnisdateien",
                    elapsed(study["phases_seconds"]["replication"]),
                ],
                [
                    "Tabellen, Abbildungen und PDF der Ausgangsstudie",
                    dec(study["phases_seconds"]["chapter"]) + " s",
                ],
                ["Gesamte Ausgangsstudie, äußere Stoppuhr", elapsed(wall)],
                [
                    "Davon innerhalb der 42 Trainingsschleifen",
                    elapsed(study["sum_inner_fits_seconds"]),
                ],
                [
                    "Zusätzliche LBM- und Operatorvergleiche dieses Nachtrags",
                    elapsed(comp),
                ],
            ],
        )
    }

Der Zusatzversuch umfasst das Übersetzen beider LBM-Kerne, drei frische Prozesse je Verfahren und Aufgabe, die Fehlerberechnung und die Gitterverfeinerung. Die beiden nacheinander gemessenen Versuchsblöcke ergeben zusammen **{
        elapsed(wall + comp)
    }**. Installation, Archivtransfer und Satz dieser erweiterten Fassung liegen außerhalb der beiden Zeitfenster.

**Was bedeutet Gesamtzeit für einen Anwender?** *Neu* beginnt beim Start des Python-Prozesses. Ein lernendes Verfahren erzeugt seine Trainingsdaten, passt die Gewichte an, speichert und lädt den Zustand. Danach löst es sämtliche Feldaufträge, schreibt die Ergebnisse und beendet den Prozess. *Geladen* umfasst denselben Prozessstart, das Laden vorhandener Gewichte, alle Feldaufträge, die Dateiausgabe und das Prozessende. Direkte Solver rechnen in beiden Fällen mit derselben bereits übersetzten Bibliothek. Deren gemeinsamer einmaliger Bau dauerte {
        dec(clocks["build_s"])
    } s.

*Warm* misst alle Feldaufträge hintereinander im laufenden Prozess bei Batchgröße eins. Angegeben ist der Median über neun vollständige Blöcke nach zwei Aufwärmblöcken, jeweils bis zur Rückgabe der Felder im Speicher. Je Kaltstartvariante wurde ein Durchlauf gemessen. Die Testeingaben liegen vor dem Prozessstart auf der Platte. Die analytische Bewertung geschieht anschließend außerhalb der Anwendungszeit.""")

    refines = read_csv(directory / "lbm_refinement.csv")
    grid_table = table(
        ["Knoten je Achse", "LBM-Takte", "Fehler $u$ · %", "Fehler $v$ · %"],
        [[r["n"], r["steps"], percent(r["u"]), percent(r["v"])] for r in refines],
    )
    pages.append(
        r"""## Lattice Boltzmann für zwei Diffusionsfelder

Wie rechnet ein klassischer Solver dieselben Platten? Für jedes Feld speichern wir pro Knoten fünf Populationen $f_i$. Eine ruht, vier bewegen sich zum nächsten Achsennachbarn. Die Temperatur ist $\phi=\sum_i f_i$. In der lokalen BGK-Kollision relaxieren die Populationen zum Gleichgewicht $w_i\phi$. Es gilt $w_0=1/3$ und $w_{1,\ldots,4}=1/6$. Anschließend werden die Populationen um jeweils einen Gitterschritt verschoben.

$$
 f_i^*=f_i+(w_i\phi-f_i)/\tau,\qquad
 D=\frac{1}{3}\left(\tau-\frac12\right)\frac{h^2}{\Delta t}.
$$

Die Momentrelation $\sum_i w_i e_{ix}^2=1/3$ liefert den Vorfaktor. Für jede Platte wählen wir $\tau=1/2+3D\Delta t/h^2$. Der Austausch erhält $u+v$ und multipliziert $u-v$ in einem halben Zeitschritt mit $\exp(-\kappa\Delta t)$. Wir wenden ihn je zur Hälfte vor und nach dem Diffusionsschritt an. An den Rändern setzen wir die Populationen ungerade über die Gitterwand fort. Die Summe am Rand ist dadurch null. [D2Q5-Diffusion und Reaktionssplitting](https://doi.org/10.1103/PhysRevE.102.043305)

**Kontrollrechnung.** Wir halbieren $h=1/(n-1)$ bei identischen acht Anfangsfeldpaaren und gleichem Endzeitpunkt. Mit $K=\max(1,\lceil6\max(D_u,D_v)\,T/h^2\rceil)$ und $\Delta t=T/K$ endet jede Rechnung genau bei $T$. Die Fehler beziehen sich auf die analytischen Sinuslösungen.

"""
        + grid_table
        + """

Mit jeder Verfeinerung fallen die Feldfehler näherungsweise um den Faktor vier. Der Zeitvergleich der nächsten Seite verwendet das 25er-Gitter. Die Raumschritte, Zeitschritte und Fehler der feineren Gitter gehören ausschließlich zur Konvergenzprüfung."""
    )

    d2q5 = d["D2Q5"]
    modal = d["Modal24"]
    pages.append(f"""## Gleiche 32 Aufträge bei festem Material

Jeder Auftrag besteht aus den beiden Anfangstemperaturen auf $25\\times25$ Knoten. Gesucht sind beide Endfelder bei $T=0{{,}}4$. Alle Modelle erhalten dieselben 32 Testeingaben. D2Q5 führt 83 Takte je Feldpaar aus. Die Tabelle gibt die Gesamtzeit **für alle 32 Paare** an. Der Fehler ist das Mittel aus den kanalweisen relativen Feldfehlern auf den gleichen 32 Paaren.

{job_table(by_problem["diffusion"])}

**Ein einzelner Auftrag.** Vom Prozessstart bis zum ersten fertigen Feldpaar im Speicher vergingen bei einsatzbereitem D2Q5 {dec(d2q5["ready1_s"], 3)} s, bei Modal24 {dec(modal["ready1_s"], 3)} s und beim geladenen FNO {dec(d["FNO-small"]["ready1_s"], 3)} s. Die Messgrenze für diese drei Zahlen liegt vor der Ausgabe der restlichen Aufträge auf die Platte.

**Warum ist die Modellwahl hier so folgenreich?** Bei Modal24 reichen sechs Projektionen und sechs kleine Matrixprodukte für das gesamte Zeitintervall. D2Q5 transportiert zehn Populationen an jedem Knoten durch 83 Takte. Die sechs trainierten Moden decken hier sämtliche Testeingaben ab. Der Abschnitt über unbekannte Moden prüft die Kosten dieses Vorwissens für die Vorhersagequalität.

Die Netze verwenden Seed 2027, 96 Trainings- und 24 Validierungsfelder. Beim Kaltstart lädt der Einstieg von Modal24 NumPy und SciPy, D2Q5 lädt NumPy und den nativen Kern. Der Unterschied gehört zur hier gemessenen Software. Die beiden Kaltstartspalten stammen aus unabhängigen Einzelmessungen.""")

    cro = read_csv(directory / "break_even.csv")
    modal_cross = next(
        r for r in cro if r["problem"] == "diffusion" and r["candidate"] == "Modal24"
    )
    gain = 1000 * float(modal_cross["saving_per_field_s"])
    nstar = modal_cross["strict_crossover_n"]
    crossover_text = (
        f"Für Modal24 gegenüber D2Q5 bei festem Material beträgt der gemessene Zeitvorteil pro zusätzlichem Feldpaar {dec(gain, 3)} ms. Das lineare Modell ergibt ab {nstar} Aufträgen eine kleinere Gesamtdauer für Modal24."
        if nstar
        else "Modal24 erreichte im nominalen Messlauf keinen positiven marginalen Zeitvorteil gegenüber D2Q5."
    )
    pages.append(f"""## Wechselnde Parameter und wiederholte Aufträge

Die zweite Serie verwendet wieder 32 Feldpaare auf $25\\times25$. Für jedes Paar ändern sich Diffusivitäten, Kopplung und Endzeit. D2Q5 übernimmt die vier gegebenen Zahlen und bestimmt damit die Taktzahl. Die beiden konditionierten Netze erhalten dieselben vier Werte zusätzlich zu den Anfangsfeldern. Strang verwendet die Parameter im Physikschritt.

{job_table(by_problem["family"])}

Die Fehler sind wieder kanalweise relative Feldfehler gegen die analytische Lösung. Die Auswertung benutzt dieselben Eingaben und Parametersätze für alle vier Verfahren. Ein längerer Zeithorizont kostet D2Q5 weitere Takte. Ein einzelner Aufruf des konditionierten Netzes umfasst stets dieselbe Zahl von Schichten.

**Ab welcher Stückzahl lohnt sich eine Anpassung?** Für einen dauerhaft laufenden Dienst mit $N$ einzeln eintreffenden Aufträgen setzen wir näherungsweise $T_i(N)=A_i+N\\ell_i$. Wir messen $A_i$ vom Start des Prozesses bis unmittelbar vor dem ersten Vorwärtsaufruf einschließlich einer nötigen Anpassung und $\\ell_i$ als warme Blockzeit pro Feldpaar. Bei $\\ell_m<\\ell_b$ ist ein Kandidat $m$ schneller als die Basis $b$, sobald

$$
 N > \\frac{{A_m-A_b}}{{\\ell_b-\\ell_m}}.
$$

{crossover_text} Diese Schwelle ist eine Rechnung aus den Messwerten. Direkt gestoppt wurden die Blöcke mit 32 Feldern. Der Wert gilt für diesen Softwarestand, dieselbe Hardware und die Ausgabe im Speicher. Eine Anwendung muss zusätzlich angeben, welchen Feldfehler sie toleriert.""")

    mpitable = table(
        ["MPI-Prozesse", "Rechenkern · s", "Gesamt · s", "Speedup gesamt"],
        [
            [
                str(r["ranks"]),
                dec(r["kernel_s"], 3),
                dec(r["launcher_wall_s"], 3),
                dec(mpi[0]["launcher_wall_s"] / r["launcher_wall_s"]),
            ]
            for r in mpi
        ],
    )
    ratio = float(c["Cavity-FNO"]["warmN_s"]) / float(c["D2Q9"]["warmN_s"])
    which = (
        f"Der C++-Solver war warm um den Faktor {dec(ratio, 2)} schneller als der geladene Residual-FNO."
        if ratio >= 1
        else f"Der geladene Residual-FNO war warm um den Faktor {dec(1 / ratio, 2)} schneller als der C++-Solver."
    )
    pages.append(f"""## Kavität im Kleinversuch und auf dem Vollgitter

**Direkter Vergleich am trainierten Einsatzpunkt.** Bei $\\mathrm{{Re}}=1000$ und Deckelgeschwindigkeit $0{{,}}1$ sagen alle drei Verfahren die beiden Geschwindigkeitskomponenten auf $17\\times17$ nach genau 16 D2Q9-Takten voraus. Die 24 Testdichtefelder stimmen mit der veröffentlichten Testziehung überein. Die Spalte *Geladen* verwendet beim Residual-FNO den veröffentlichten CP2-Modellzustand. *Neu* erzeugt 96 Trainings- und 16 Validierungspaare mit der NumPy-Referenz und trainiert 80 Epochen.

{job_table(by_problem["cavity"])}

Die Feldfehler beziehen sich auf den Geschwindigkeitsvektor im Fluidinneren gegen die unabhängige Ausführung der CP2-NumPy-Referenz. Deren eigener Fehler ist daher definitionsgemäß null. {which} Beide Zeitangaben schließen das gesamte Vorhersageverfahren samt Startdichte und Ausgabe beider Komponenten ein.

**Archiviertes Vollgitter.** Ein einziger CP2-Fall mit $257\\times257$ Knoten läuft bei $\\mathrm{{Re}}=1000$ bis Takt 350 000, entsprechend $t^*=136{{,}}71875$. Die Gesamtuhr umfasst MPI-Start, Rechenkern, Zusammenführen der Teilfelder und Dateiausgabe. Plattform AMD EPYC 9V45, ein Lauf je Prozesszahl.

{mpitable}

Alle vier Endfelder haben dieselbe SHA-256-Prüfsumme. Acht Prozesse verkürzten den Gesamtauftrag um den Faktor {dec(speedup)}. Das feste CP2-Netz akzeptiert ausschließlich das 17er-Gitter und wurde für 16 Takte trainiert. Das zusätzliche parametrisierte CP2-Modell deckt Gitter 17, 25, 33 und Endtakte 8, 16, 24 ab. Für diesen Residual-FNO fehlt ein validierter Lauf auf dem 257er-Gitter. Für sieben Felder auf diesem Gitter benötigt die räumliche 2D-Fourierschicht aus Kapitel 16 direkt {dec(direct['cpu_s'],3)} CPU-s, mit Grobgitterkorrektur {dec(hybrid['cpu_s'],3)} CPU-s. Die größten lokalen Abweichungen von D2Q9 betragen {dec(100*float(direct['lbm_lokal_max_U']),1)} % und {dec(100*float(hybrid['lbm_lokal_max_U']),1)} % der Deckelgeschwindigkeit. Die MPI-Tabelle misst die Wandzeit für den gesamten Endfeldauftrag. [CP2-Modellzustand](https://github.com/5H3LL3H5/argesim-hyperposition-benchmarks/blob/72d670b51c94c8366ca5f1e070fc4730c78d0d52/docs/lehrbuch/studienbuch/material/cp2_genauigkeit/kavitaet.npz) · [Vollgitter-Messungen](https://github.com/5H3LL3H5/argesim-hyperposition-benchmarks/tree/5e73ade08e753223c59619118f23d24036bdc029/docs/lehrbuch/gesamtausgabe/rechenlabor/pdes_partitionierung)""")

    lead = (
        f"**Gesamtlaufzeit.** Die vollständige Ausgangsstudie dauerte {elapsed(wall)}. "
        f"Für 32 neue nominale Feldpaare brauchte der einsatzbereite Modaloperator im "
        f"laufenden Prozess {dec(1000 * float(modal['warmN_s']))} ms, D2Q5-LBM "
        f"{dec(1000 * float(d2q5['warmN_s']))} ms. Die Tabellen ab Seite 7 zeigen "
        "auch Prozessstart, Neutraining und die Kavitätsmessungen."
    )
    return {
        "RUNTIME_LEAD": lead,
        "RUNTIME_SECTION": "\n\n<!-- page -->\n\n".join(pages),
    }

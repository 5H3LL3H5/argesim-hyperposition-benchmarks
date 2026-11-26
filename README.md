# ARGESIM and NSA-DEVS reference suite

Run the ARGESIM benchmarks, compare selected results with independent references, or study event ordering with the restricted NSA-DEVS scheduler. The Python package includes the model definitions, continuous solvers, discrete-event runtime and experiment runners. Python 3.10 or later is required. The core uses the standard library. Install the optional DAE backend to exercise the IDAS tests.

## Run from a checkout

From the repository root, list the families, inspect a task contract and run the C01 stationary-state calculation.

```sh
python -m argesim_benchmarks list
python -m argesim_benchmarks describe C01
python -m argesim_benchmarks run C01 C
```

Run all registered tasks with smoke inputs, or select families by repeating `--benchmark`. Each task records its arguments, outcome and elapsed time. A failed task gives the suite a nonzero exit code. Use `--fail-fast` to stop at the first failure.

```sh
python -m argesim_benchmarks run-suite --profile smoke
python -m argesim_benchmarks run-suite --profile smoke --benchmark C19R --benchmark C22
python -m unittest discover -s tests -v
```

For the installed `argesim` and `argesim-cifasis-oracle` commands, run `python -m pip install -e .` in a virtual environment. The `definition` profile uses the registered full workloads, including CP2's 350,000-iteration cavity calculation. For C18, supply the training and validation CSVs to `run C18 all`. Its smoke task explicitly selects the packaged figure reconstruction. [C18 inputs](docs/C18_FIGURE_RECONSTRUCTION.md)

## Coverage

The registry exposes 75 tasks across 24 families. Fifteen families have independently validated cases, eight more are implemented, and C18 is specified pending the original recordings. Each validation applies to the quantity, reference and tolerance documented for that case. No family has reached `benchmark-ready`. [Task and status tables](ARGESIM_COVERAGE.md) · [Numerical comparisons](docs/PUBLISHED_REFERENCE_CHECKS.md)

| To find | Start here |
|---|---|
| Model reports, reproduction commands and dated studies | [Documentation index](docs/README.md) |
| Outstanding reference discrepancies and input requirements | [Implementation audit](ARGESIM_AUDIT.md) |
| Evidence gates, event ordering, performance measurements and provenance | [Benchmark methodology](METHODOLOGY.md) |
| Learn numerical simulation with ARGESIM (German) | [Student textbook and worked solutions](docs/lehrbuch/README.md) · [Complete v9.22 textbook (PDF)](docs/ARGESIM_SOLVER_STUDY.pdf) · [QSS lab (ZIP)](docs/ARGESIM_Bachelor_Rechenlabor.zip) · [Full experiment data and weights](docs/lehrbuch/gesamtausgabe/Labor.md) |
| Python model callbacks, CP2 lattice Boltzmann and Fourier neural operators | [Train and test two field operators (German)](docs/CP2_NEURAL_OPERATORS.md) |
| When to use QSS, Runge–Kutta or a stiff solver | [Selection guide and experimental results](docs/SOLVER_SELECTION.md) |
| DEVS origins and low-order RK for stiff and nonstiff ODEs | [Event trace, new methods and comparison](docs/QSS_DEVS_HISTORY.md) |
| Quantized solver comparison, event repair and residual DAE results | [Study and raw measurements](docs/SOLVER_COMPARISON.md) · [Method explanations](docs/SOLVER_METHODS.md) |
| Introduction to each QSS method, classical baselines and the IDAS interface | [Start with the tank example and method guide](QSS_SOLVERS.md#how-to-read-a-qss-method-name) |
| Optional native QSS1/QSS2 linear-decay comparison | [CIFASIS adapter](docs/CIFASIS_ORACLE.md) |

## Pre-Commit für Python-Änderungen

Einmal pro Checkout `pre-commit install` ausführen. Beim Commit prüft Ruff die
gestagten Python-Dateien und wendet nur sichere Korrekturen an. Wenn der Hook
Dateien geändert hat, den Diff prüfen, die Korrekturen stagen und erneut committen.
Manuell: `pre-commit run`; für alle Dateien: `pre-commit run --all-files`.
Die GitHub-CI prüft mit derselben Ruff-Version, ohne Dateien zu ändern.

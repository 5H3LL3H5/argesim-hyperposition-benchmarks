"""Generate and verify status tables derived from the canonical catalog."""

from __future__ import annotations

from pathlib import Path

from .catalog import BENCHMARKS
from .runner import CONTRACTS, verify_registry_complete

COVERAGE_START = "<!-- BEGIN GENERATED BENCHMARK STATUS -->"
COVERAGE_END = "<!-- END GENERATED BENCHMARK STATUS -->"
SCOPE_START = "<!-- BEGIN GENERATED EXECUTABLE SCOPE -->"
SCOPE_END = "<!-- END GENERATED EXECUTABLE SCOPE -->"

# The registry owns CLI task names. These notes describe the evidence for a
# case, which cannot be inferred from its entry point or a successful smoke run.
_EVIDENCE = {
    "C01": "Five Task B trajectories against Radau and two stationary states against Dymola. [Results](docs/C01_RESULTS.md)",
    "C02": "Finite assembly plant and pallet study. Eleven CSIM loads pass under one convention. Default SimEvents gaps at 13, 14 and 25 pallets. [Clocks and comparison](C02_IMPLEMENTATION.md)",
    "C03": "Switch-state eigenvalues, half cycles and finite-ramp endpoints. [Results](C03_VALIDATION_REPORT.md)",
    "C04": "Fork conservation, cleaning, deterministic replay and deadlock checks. Published fairness distributions remain open.",
    "C05": "Five default and 62 Task D switches, logarithmic crossing references and precision studies.",
    "C06": "Three service policies and 21 daily metrics compared with 100-replication STROBOSCOPE results.",
    "C07": "Nonlinear pin contact times and independent DOP853 trajectories for two initial conditions.",
    "C08": "Five published deterministic datasets for lock policies, plus stochastic replication tests. [Results](C08_VALIDATION.md)",
    "C09": "Three fuzzy controllers. One of three Simulink figure measurements matches the definition-scale run. [Windows and control signal](docs/C09_FIGURE_CHECKS.md)",
    "C10": "Simultaneous-access priority, deadlock termination and 50-run study. Matched waiting-time distributions remain open.",
    "C11": "SCARA robot motion and sampled control. A matched independent DAE trajectory remains open.",
    "C12": "Inverse restitution and the Dymola distribution of terminal speeds.",
    "C13": "Linear Task A endpoints validated at three loads. B/C holding and emergency brake logic tested. [C13R evidence](docs/C13_REFERENCE_ANALYSIS.md)",
    "C14": "Supply chain demand at midnight, order delays and three-week trace. [Reference variants](C14_VALIDATION.md)",
    "C15": "Three bolus masses, Task B fit and a 1,000-sample parameter experiment.",
    "C16": "Year-five restaurant count compared with two published studies. [Results](docs/C16_REFERENCE_RESULTS.json)",
    "C17R": "Default ODE trajectories validated. The spatial FHP-I comparison uses a published single-run statistic. [C17R results](docs/PUBLISHED_REFERENCE_CHECKS.md#c17r-default-ode-and-spatial-comparison)",
    "C18": "ARX, static and recurrent networks implemented. Figure reconstruction executable. Original training and validation recordings missing. [Provenance](docs/C18_FIGURE_RECONSTRUCTION.md)",
    "C19R": "Groundwater profiles, continuous and scheduled treatment. The 1 m grid retains spatial error at breakthrough and near the disks. [Accuracy](docs/PUBLISHED_REFERENCE_CHECKS.md#c19r-spatial-and-time-accuracy)",
    "C20": "Layout, blocking, rework and disruptions. 360 runs on three generated order books, 36 transport replays. [Experiment](docs/C20_EXPERIMENT_20261120.json)",
    "C21": "Published contact and pendulum quantities, plus residual checks on three RLC realizations.",
    "C22": "Published jockeying, abandonment and class waiting-time records.",
    "CP1": "Serial/parallel RK4, pair and rope decompositions. Published ten-population endpoint for Task B.",
    "CP2": "Monte Carlo, full-way D2Q9 parity and the corrected 499-unknown rope/Fourier comparison.",
}


def benchmark_status_table() -> str:
    """Return the canonical Markdown benchmark status table."""

    lines = [
        "| ID | Official benchmark | Model family | Status |",
        "|---|---|---|---|",
    ]
    for entry in BENCHMARKS:
        lines.append(
            f"| {entry.identifier} | {entry.title} | {entry.coverage_family} | "
            f"{entry.status.value} |"
        )
    return "\n".join(lines)


def executable_scope_table() -> str:
    verify_registry_complete()
    lines = [
        "| ID | Registered CLI tasks | Scope and evidence |",
        "|---|---|---|",
    ]
    for entry in BENCHMARKS:
        identifier = entry.identifier
        tasks = ", ".join(f"`{name}`" for name in CONTRACTS[identifier].tasks)
        note = _EVIDENCE.get(identifier, entry.coverage_family)
        lines.append(f"| {identifier} | {tasks} | {note} |")
    return "\n".join(lines)


def replace_generated_section(text: str, generated: str, *,
                              start_marker: str = COVERAGE_START,
                              end_marker: str = COVERAGE_END) -> str:
    """Replace the unique generated Markdown section, rejecting malformed markers."""

    if text.count(start_marker) != 1 or text.count(end_marker) != 1:
        raise ValueError(f"expected one marker pair for {start_marker}")
    start = text.index(start_marker)
    end = text.index(end_marker)
    if end < start:
        raise ValueError("generated benchmark status markers are missing or malformed")
    return (
        text[:start + len(start_marker)]
        + "\n"
        + generated.rstrip()
        + "\n"
        + text[end:]
    )


def render_coverage_document(text: str) -> str:
    """Render both catalog status and registered CLI tasks."""

    if text.find(SCOPE_START) <= text.find(COVERAGE_END):
        raise ValueError("expected separate status and executable scope sections in order")
    text = replace_generated_section(text, benchmark_status_table())
    return replace_generated_section(text, executable_scope_table(),
                                     start_marker=SCOPE_START, end_marker=SCOPE_END)


def verify_coverage_document(path: Path) -> None:
    """Raise when the checked-in coverage table differs from the catalog."""

    text = path.read_text(encoding="utf-8")
    rendered = render_coverage_document(text)
    if rendered != text:
        raise AssertionError(
            "ARGESIM_COVERAGE.md is stale. Run python scripts/update_status_docs.py"
        )

"""Versioned inventory of the current official ARGESIM benchmark catalog."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BenchmarkStatus(str, Enum):
    """Evidence gates; later states require all preceding gates."""

    CATALOGED = "cataloged"
    SPECIFIED = "specified"
    IMPLEMENTED = "implemented"
    VALIDATED = "validated"
    BENCHMARK_READY = "benchmark-ready"


class ModelClass(str, Enum):
    ODE = "ode"
    STIFF_ODE = "stiff-ode"
    DAE = "dae"
    PDE = "pde"
    HYBRID = "hybrid"
    DES = "des"
    STOCHASTIC = "stochastic"
    DISCRETE_TIME = "discrete-time"
    AGENT_BASED = "agent-based"
    CELLULAR_AUTOMATON = "cellular-automaton"
    IDENTIFICATION = "identification"
    MACHINE_LEARNING = "machine-learning"
    PARALLEL = "parallel"


@dataclass(frozen=True)
class BenchmarkDefinition:
    identifier: str
    title: str
    model_classes: tuple[ModelClass, ...]
    primary_source: str
    status: BenchmarkStatus = BenchmarkStatus.CATALOGED


def _source(path: str) -> str:
    return f"https://www.argesim.org/benchmarks/{path}/"


BENCHMARKS: tuple[BenchmarkDefinition, ...] = (
    BenchmarkDefinition(
        "C01",
        "Lithium-Cluster Dynamics",
        (ModelClass.STIFF_ODE,),
        _source("c01"),
        BenchmarkStatus.IMPLEMENTED,
    ),
    BenchmarkDefinition(
        "C02", "Flexible Assembly System", (ModelClass.DES,), _source("c02")
    ),
    BenchmarkDefinition(
        "C03",
        "Class-E Amplifier",
        (ModelClass.ODE, ModelClass.HYBRID),
        _source("c03"),
    ),
    BenchmarkDefinition(
        "C04", "Dining Philosophers", (ModelClass.DES,), _source("c04")
    ),
    BenchmarkDefinition(
        "C05",
        "Two State Model",
        (ModelClass.STIFF_ODE, ModelClass.HYBRID),
        _source("c05"),
    ),
    BenchmarkDefinition(
        "C06",
        "Emergency Department - Follow-up Treatment",
        (ModelClass.DES, ModelClass.STOCHASTIC),
        _source("c06"),
        BenchmarkStatus.IMPLEMENTED,
    ),
    BenchmarkDefinition(
        "C07",
        "Constrained Pendulum",
        (ModelClass.ODE, ModelClass.HYBRID),
        _source("c07"),
    ),
    BenchmarkDefinition(
        "C08",
        "Canal-and-Lock System",
        (ModelClass.DES, ModelClass.STOCHASTIC),
        _source("c08"),
    ),
    BenchmarkDefinition(
        "C09",
        "Fuzzy Control of a Two Tank System",
        (ModelClass.ODE, ModelClass.HYBRID, ModelClass.DISCRETE_TIME),
        _source("c09"),
    ),
    BenchmarkDefinition(
        "C10", "Dining Philosophers II", (ModelClass.DES,), _source("c10")
    ),
    BenchmarkDefinition(
        "C11",
        "SCARA Robot",
        (ModelClass.DAE, ModelClass.HYBRID),
        _source("c11"),
    ),
    BenchmarkDefinition(
        "C12",
        "Collision Processes in Rows of Spheres",
        (ModelClass.ODE, ModelClass.HYBRID, ModelClass.STOCHASTIC),
        _source("c12"),
    ),
    BenchmarkDefinition(
        "C13",
        "Crane and Embedded Control",
        (ModelClass.DAE, ModelClass.HYBRID, ModelClass.DISCRETE_TIME),
        _source("c13"),
        BenchmarkStatus.IMPLEMENTED,
    ),
    BenchmarkDefinition(
        "C14", "Supply Chain", (ModelClass.DISCRETE_TIME,), _source("c14")
    ),
    BenchmarkDefinition(
        "C15",
        "Clearance Identification",
        (ModelClass.ODE, ModelClass.IDENTIFICATION, ModelClass.STOCHASTIC),
        _source("c15"),
    ),
    BenchmarkDefinition(
        "C16",
        "Restaurant Business Dynamics",
        (ModelClass.DES, ModelClass.AGENT_BASED, ModelClass.STOCHASTIC),
        _source("c16"),
    ),
    BenchmarkDefinition(
        "C17R",
        "SIR-type Epidemic with Cellular Automata and ODEs",
        (
            ModelClass.ODE,
            ModelClass.CELLULAR_AUTOMATON,
            ModelClass.HYBRID,
            ModelClass.IDENTIFICATION,
        ),
        _source("c17r"),
    ),
    BenchmarkDefinition(
        "C18",
        "Identification of Nonlinear Dynamics - Neural Networks versus "
        "Transfer Functions",
        (
            ModelClass.DISCRETE_TIME,
            ModelClass.IDENTIFICATION,
            ModelClass.MACHINE_LEARNING,
        ),
        _source("c18"),
    ),
    BenchmarkDefinition(
        "C19R",
        "Pollution in Groundwater Flow",
        (ModelClass.PDE, ModelClass.HYBRID),
        _source("c19"),
        BenchmarkStatus.IMPLEMENTED,
    ),
    BenchmarkDefinition(
        "C20", "Complex Production System", (ModelClass.DES,), _source("c20")
    ),
    BenchmarkDefinition(
        "C21",
        "State Events and Structural-dynamic Systems",
        (ModelClass.ODE, ModelClass.DAE, ModelClass.HYBRID),
        _source("c21"),
        BenchmarkStatus.IMPLEMENTED,
    ),
    BenchmarkDefinition(
        "C22",
        "Non-standard Queuing Policies",
        (ModelClass.DES,),
        _source("c22"),
        BenchmarkStatus.IMPLEMENTED,
    ),
    BenchmarkDefinition(
        "CP1",
        "Parallel Simulation Techniques",
        (ModelClass.ODE, ModelClass.PDE, ModelClass.PARALLEL),
        _source("cp"),
        BenchmarkStatus.IMPLEMENTED,
    ),
    BenchmarkDefinition(
        "CP2",
        "Parallel and Distributed Simulation",
        (
            ModelClass.ODE,
            ModelClass.PDE,
            ModelClass.CELLULAR_AUTOMATON,
            ModelClass.PARALLEL,
            ModelClass.STOCHASTIC,
        ),
        _source("cp"),
        BenchmarkStatus.IMPLEMENTED,
    ),
)


def benchmark(identifier: str) -> BenchmarkDefinition:
    """Return one catalog entry by canonical identifier."""

    for definition in BENCHMARKS:
        if definition.identifier == identifier:
            return definition
    raise KeyError(identifier)

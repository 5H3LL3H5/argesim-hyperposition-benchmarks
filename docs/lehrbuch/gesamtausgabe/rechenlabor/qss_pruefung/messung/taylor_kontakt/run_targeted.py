import json
import random
import signal
import sys
from pathlib import Path
from types import SimpleNamespace

from benchmarks import benchmark_solver_extension as ext
from benchmarks import benchmark_solver_selection as sel

root = Path(sys.argv[1])
signal.signal(signal.SIGALRM, ext.timeout_handler)
controls = SimpleNamespace(repeat=3, timeout=2.0)
for name, jobs, configure in (
    ("extension", [(factory(), m, q) for factory in (ext.amplifier, ext.switches, ext.pendulum, ext.tanks, ext.robot, ext.spheres, ext.crane, ext.bounce) for m in ("qss3", "qss4") for q in ext.LEVELS], ext.options),
    ("selection", [(c,m,q) for c,m,q in sel.schedule() if m in ("qss3", "qss4")], sel.configure),
):
    if name == "extension":
        random.Random(71).shuffle(jobs)
    with (root / (name + ".jsonl")).open("w", buffering=1) as f:
        for case, method, level in jobs:
            row = ext.measure(case, method, level, controls, configure)
            f.write(json.dumps(row, allow_nan=False) + "\n")
    print(name, len(jobs), flush=True)

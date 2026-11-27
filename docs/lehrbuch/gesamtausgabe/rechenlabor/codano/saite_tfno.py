"""Small paired CP2 operator pilot; run from this repository with PYTHONPATH=."""

import json
import platform
import subprocess
import time
from importlib.metadata import version
import numpy as np
import torch
from neuralop.models import TFNO
from argesim_benchmarks.experiments import (
    cp2_fields as f,
    cp2_operators as op,
    cp2_accuracy as a,
)
from scripts.cp2_accuracy.rope_finetune import data, objective, POSITIONS, TIMES

torch.set_num_threads(1)
torch.use_deterministic_algorithms(True)
x, y = data(96, 4101)
vx, vy = data(16, 4102)
tests = {}
for n in (129, 501):
    xs, ys = f.rope_samples(24, np.random.default_rng(93017), nodes=n)
    z = np.linspace(0, f.ROPE.length, n)
    xt = np.stack([a.pluck(z, 0.0, p) for p in POSITIONS])
    yt = np.stack([a.pluck(z, np.array(TIMES), p) for p in POSITIONS])
    for group, pair in {"smooth": (xs, ys), "held_out_plucks": (xt, yt)}.items():
        tests[f"{n}_{group}"] = tuple(
            torch.from_numpy(q.astype("float32")) for q in pair
        )


def make(name):
    if name == "FNO":
        return op.make_model("rope")
    return TFNO(
        n_modes=(24,),
        in_channels=1,
        out_channels=2,
        hidden_channels=12,
        n_layers=2,
        positional_embedding=None,
        rank=0.25,
    )


def evaluate(net, xx, yy):
    with torch.inference_mode():
        pred = op.forward_field("rope", net, xx)
    err = op.errors("rope", pred.numpy(), yy.numpy())
    err["peak_abs_mm"] = float((pred - yy).abs().max() * 1000)
    err["fixed_end_max_abs_mm"] = float(pred[..., [0, -1]].abs().max() * 1000)
    return err


rows = []
for seed in (2027, 73, 3917):
    for name in ("FNO", "TFNO"):
        torch.manual_seed(seed)
        model = make(name)
        opt = torch.optim.Adam(model.parameters(), lr=0.003)
        rng = torch.Generator().manual_seed(seed)
        best = float("inf")
        start = time.perf_counter()
        for epoch in range(1, 41):
            model.train()
            for ix in torch.randperm(len(x), generator=rng).split(16):
                opt.zero_grad(set_to_none=True)
                loss = objective(op.forward_field("rope", model, x[ix]), y[ix])
                loss.backward()
                opt.step()
            model.eval()
            with torch.inference_mode():
                val = objective(op.forward_field("rope", model, vx), vy).item()
            if val < best:
                best, best_epoch, state = val, epoch, op.tensor_weights(model)
        seconds = time.perf_counter() - start
        torch.nn.Module.load_state_dict(model, state)
        row = {
            "model": name,
            "seed": seed,
            "parameter_elements": sum(
                p.numel() * (2 if p.is_complex() else 1) for p in model.parameters()
            ),
            "best_epoch": best_epoch,
            "seconds": seconds,
            "test": {k: evaluate(model, *v) for k, v in tests.items()},
        }
        rows.append(row)
    print(
        json.dumps(
            {
                "python": platform.python_version(),
                "torch": str(torch.__version__),
                "neuraloperator": version("neuraloperator"),
                "source_commit": subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], text=True
                ).strip(),
                "epochs": 40,
                "threads": 1,
                "rows": rows,
            },
            allow_nan=False,
        ),
        flush=True,
    )

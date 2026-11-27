"""Train the original networks and learned FNO residuals, using disjoint validation."""

import argparse
import json
import sys
import time
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
import torch
from neuralop.models import FNO

from physics import (
    NOMINAL,
    Physics,
    add_training_noise,
    basis,
    draw,
    family,
    samples,
    strang,
)
from reference import austausch as pr

ROOT = Path(__file__).resolve().parent
MODELS = ("FNO-small", "UNO", "CoDA-NO", "Strang-FNO")
CONDITIONAL = ("FNO-cond", "Strang-FNO-cond")
# Count, relative training noise, varying physical parameters, optimizer epochs.
CASES = {
    "n2": (2, 0.0, False, 40),
    "n8": (8, 0.0, False, 40),
    "n24": (24, 0.0, False, 40),
    "n96": (96, 0.0, False, 40),
    "n8_steps": (8, 0.0, False, 240),
    "noise5": (96, 0.05, False, 40),
    "input5": (96, 0.05, False, 40),
    "family": (96, 0.0, True, 40),
}


def configure():
    torch.set_num_threads(1)
    torch.backends.nnpack.set_flags(False)
    torch.use_deterministic_algorithms(True)


def make(name):
    if name in CONDITIONAL:
        return FNO(
            n_modes=(10, 10),
            in_channels=6,
            out_channels=2,
            hidden_channels=2,
            n_layers=2,
            positional_embedding=None,
        )
    return pr.make("FNO-small" if name == "Strang-FNO" else name)


def features(x, p, name):
    if name not in CONDITIONAL:
        return torch.from_numpy(x)
    params = (p,) * len(x) if isinstance(p, Physics) else p
    ref = np.array([NOMINAL.du, NOMINAL.dv, NOMINAL.rate, NOMINAL.time])
    table = np.array([[q.du, q.dv, q.rate, q.time] for q in params]) / ref - 1
    n = x.shape[-1]
    maps = table[..., None, None] * basis(n, ((1, 1),)).reshape(1, 1, n, n)
    return torch.from_numpy(np.concatenate((x, maps.astype(np.float32)), axis=1))


def model_state(model):
    return {
        k: v.detach().clone()
        for k, v in model.state_dict().items()
        if torch.is_tensor(v)
    }


def data(case):
    n, noise, varying, _ = CASES[case]
    pt = family(n, 52201) if varying else NOMINAL
    pv = family(24, 52202) if varying else NOMINAL
    x, y = samples(draw(n, 42201), 13, params=pt)
    xv, yv = samples(draw(24, 42202), 13, params=pv)
    if case == "input5":
        x = add_training_noise(x, noise)
    else:
        y = add_training_noise(y, noise)
    return (x, y, pt), (xv, yv, pv)


def train(name, seed, case, output, epochs=None):
    if CASES[case][2] != (name in CONDITIONAL):
        raise ValueError(
            "family runs use conditioned networks; fixed-physics runs use PR inputs"
        )
    (x, y, pt), (xv, yv, pv) = data(case)
    epochs = CASES[case][3] if epochs is None else epochs
    if epochs < 1:
        raise ValueError("epochs must be positive")
    torch.manual_seed(seed)
    model = make(name)
    generator = torch.Generator().manual_seed(seed)
    opt = torch.optim.Adam(model.parameters(), lr=0.003)
    start = time.perf_counter()
    tx, vx = features(x, pt, name), features(xv, pv, name)
    scale = 1.0
    if name.startswith("Strang-"):
        resid, vresid = y - strang(x, pt), yv - strang(xv, pv)
        scale = max(float(np.sqrt(np.mean(resid**2))), 1e-12)
        ty = torch.from_numpy((resid / scale).astype(np.float32))
        vy = torch.from_numpy((vresid / scale).astype(np.float32))
        # Starts at the physics-only prediction, included in validation selection.
        with torch.no_grad():
            for p in model.projection.fcs[-1].parameters():
                p.zero_()
        best, selected, weights = vy.square().mean().item(), 0, model_state(model)
    else:
        ty, vy = torch.from_numpy(y), torch.from_numpy(yv)
        best, selected, weights = float("inf"), 0, None
    for epoch in range(1, epochs + 1):
        model.train()
        for ix in torch.randperm(len(tx), generator=generator).split(16):
            opt.zero_grad(set_to_none=True)
            loss = (pr.predict(model, tx[ix]) - ty[ix]).square().mean()
            loss.backward()
            opt.step()
        model.eval()
        with torch.inference_mode():
            val = (pr.predict(model, vx) - vy).square().mean().item()
        if val < best:
            best, selected, weights = val, epoch, model_state(model)
    torch.nn.Module.load_state_dict(model, weights)
    elapsed = time.perf_counter() - start
    info = {
        "model": name,
        "seed": seed,
        "case": case,
        "n": len(x),
        "epochs": epochs,
        "steps": epochs * ((len(x) + 15) // 16),
        "selected_epoch": selected,
        "parameters": sum(
            p.numel() * (2 if p.is_complex() else 1) for p in model.parameters()
        ),
        "train_s": elapsed,
        "validation_mse": best * scale**2,
        "residual_scale": scale,
    }
    output.mkdir(parents=True, exist_ok=True)
    stem = f"{case}_{name}_{seed}"
    torch.save({"info": info, "weights": weights}, output / (stem + ".pt"))
    (output / (stem + ".json")).write_text(
        json.dumps(info, indent=2) + "\n", encoding="utf-8"
    )
    return info


class Network:
    def __init__(self, checkpoint):
        record = torch.load(checkpoint, map_location="cpu", weights_only=True)
        self.info = record["info"]
        self.name = self.info["model"]
        self.model = make(self.name)
        torch.nn.Module.load_state_dict(self.model, record["weights"])
        self.model.eval()

    @torch.inference_mode()
    def predict(self, x, p=NOMINAL):
        z = pr.predict(self.model, features(x, p, self.name)).numpy()
        if self.name.startswith("Strang-"):
            return strang(x, p) + self.info["residual_scale"] * z.astype(np.float64)
        return z


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--models", nargs="+", choices=MODELS + CONDITIONAL, default=MODELS
    )
    parser.add_argument("--cases", nargs="+", choices=CASES, default=["n96"])
    parser.add_argument("--seeds", nargs="+", type=int, default=[2027])
    parser.add_argument(
        "--epochs", type=int, help="override recipe length for a smoke run"
    )
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "weights")
    args = parser.parse_args()
    configure()
    for case in args.cases:
        for seed in args.seeds:
            for name in args.models:
                with redirect_stdout(sys.stderr):
                    info = train(name, seed, case, args.output, args.epochs)
                print(json.dumps(info), flush=True)


if __name__ == "__main__":
    main()

"""One method in one process. The outer driver times interpreter start and exit."""

import argparse
import json
from pathlib import Path
from statistics import median
from time import perf_counter, perf_counter_ns

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ARCHIVED = Path(__file__).resolve().parent / "archived"


def cavity_densities(count, split):
    from . import cp2_reference as ref

    rng = np.random.default_rng(np.random.SeedSequence(2027).spawn(3)[split])
    amplitudes = rng.uniform(-1, 1, (count, 6))
    return amplitudes, ref.density_samples(17, amplitudes)


def prepare_cavity(name, mode, scratch):
    if name == "D2Q9":
        from .native_lbm import Native

        native = Native(scratch / "lbm.so")
        return lambda x, p: native.cavity(x)
    from . import cp2_reference as ref

    if name == "D2Q9-NumPy":
        return lambda x, p: ref.cavity_snapshots(x, 0.1, [16])[16]
    import torch

    from . import cp2_network as net

    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    checkpoint = ARCHIVED / "cavity-checkpoint.npz"
    if mode == "fresh":
        amp, x = cavity_densities(96, 0)
        _, vx = cavity_densities(16, 1)

        def labels(inputs):
            return np.concatenate(
                [
                    ref.cavity_snapshots(xx, 0.1, [16])[16]
                    for xx in np.array_split(inputs, (len(inputs) + 15) // 16)
                ]
            )

        y, vy = labels(x), labels(vx)
        affine = ref.fit_affine(amp, y)
        model, scale, _ = net.train(x, y, vx, vy, affine, 2027, 80)
        checkpoint = scratch / "new-cavity-weights.npz"
        net.save(checkpoint, model, affine, scale)
    model, affine, scale = net.load(checkpoint)
    return lambda x, p: net.predict(model, x, affine, scale)


def prepare_diffusion(name, family, mode, scratch):
    if name == "D2Q5":
        from .native_lbm import Native

        native = Native(scratch / "lbm.so")
        return native.diffusion
    from physics import Generator, Modal, StrangModal, fixed_split, strang

    if name == "Strang":
        return strang
    if name in ("Modal24", "Generator3", "Strang-R24"):
        file = scratch / (name + ".npy")
        if mode == "fresh":
            x, y = fixed_split(96, 42201, 13)
            if name == "Generator3":
                coeff = Generator.fit(x, y).coeff
            elif name == "Strang-R24":
                coeff = StrangModal.fit(x, y).residual.blocks
            else:
                coeff = Modal.fit(x, y).blocks
            np.save(file, coeff)
        coeff = np.load(file, allow_pickle=False)
        if name == "Generator3":
            return Generator(coeff).predict
        if name == "Strang-R24":
            return StrangModal(Modal(coeff)).predict
        return Modal(coeff).predict
    from neural import Network, configure, train

    configure()
    case = "family" if family else "n96"
    ckpt_dir = ROOT / "results" / "weights"
    if mode == "fresh":
        ckpt_dir = scratch / "retrained"
        train(name, 2027, case, ckpt_dir)
    return Network(ckpt_dir / f"{case}_{name}_2027.pt").predict


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("problem", choices=["diffusion", "family", "cavity"])
    parser.add_argument("model")
    parser.add_argument("mode", choices=["fresh", "ready", "warm"])
    parser.add_argument("scratch", type=Path)
    args = parser.parse_args()
    problem, model, mode, work = args.problem, args.model, args.mode, args.scratch
    key = f"{problem}_{model}_{mode}"
    with np.load(work / f"inputs_{problem}.npz", allow_pickle=False) as data:
        x = data["x"]
        raw = data["params"] if problem != "cavity" else None
    if problem == "cavity":
        params = [None] * len(x)
    elif model == "D2Q5":
        from collections import namedtuple

        Input = namedtuple("Input", "du dv rate time")
        params = [Input(*q) for q in raw]
    else:
        from physics import Physics

        params = [Physics(*q) for q in raw]
    tick = perf_counter()
    predict = (
        prepare_cavity(model, mode, work)
        if problem == "cavity"
        else prepare_diffusion(model, problem == "family", mode, work)
    )
    prep = perf_counter() - tick

    def serve():
        out = []
        first = 0
        for i, q in enumerate(params):
            out.append(predict(x[i : i + 1], q))
            if i == 0:
                first = perf_counter_ns()
        return first, np.concatenate(out, axis=0)

    if mode == "warm":
        for _ in range(2):
            serve()
        runs = []
        for _ in range(9):
            start = perf_counter()
            _, y = serve()
            runs.append(perf_counter() - start)
        receipt = {
            "block_seconds": runs,
            "block_median_s": median(runs),
            "count": len(x),
        }
    else:
        service_ns = perf_counter_ns()
        first, y = serve()
        last = perf_counter_ns()
        receipt = {
            "setup_s": prep,
            "service_start_ns": service_ns,
            "first_ns": first,
            "last_ns": last,
            "count": len(x),
            "prediction_block_s": (last - service_ns) * 1e-9,
        }
        np.save(work / f"{key}.npy", y)
    (work / f"{key}.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()

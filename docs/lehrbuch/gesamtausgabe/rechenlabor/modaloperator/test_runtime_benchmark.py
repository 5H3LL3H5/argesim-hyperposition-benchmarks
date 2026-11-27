"""Independent lattice checks and measurement-boundary regressions."""

import csv
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from physics import NOMINAL, Physics, draw, samples
from runtime_benchmark import cp2_reference
from runtime_benchmark.native_lbm import Native, build, diffusion_steps


def odd_extension(x):
    for axis in (-1, -2):
        interior = np.take(x, np.arange(1, x.shape[axis] - 1), axis=axis)
        x = np.concatenate([x, -np.flip(interior, axis=axis)], axis=axis)
    return x


def periodic_d2q5(pair, p):
    n = pair.shape[-1]
    steps = diffusion_steps(n, p)
    dt = p.time / steps
    weights = np.array([1 / 3, 1 / 6, 1 / 6, 1 / 6, 1 / 6])[None, :, None, None]
    rates = 1 / (0.5 + 3 * np.array([p.du, p.dv]) * dt * (n - 1) ** 2)
    f = odd_extension(pair)[:, None] * weights
    alpha = -np.expm1(-p.rate * dt) / 2

    def half(z):
        return z + alpha * (z[::-1] - z)

    for _ in range(steps):
        f = half(f)
        f = f + rates[:, None, None, None] * (
            weights * f.sum(axis=1, keepdims=True) - f
        )
        for q, (dy, dx) in enumerate([(0, 0), (0, 1), (1, 0), (0, -1), (-1, 0)]):
            f[:, q] = np.roll(f[:, q], (dy, dx), axis=(-2, -1))
        f = half(f)
    return f.sum(axis=1)[:, :n, :n]


class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        path = Path(cls.tmp.name) / "lbm.so"
        build(path)
        cls.k = Native(path)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_d2q5_against_full_periodic_extension(self):
        x = np.random.default_rng(627).standard_normal((1, 2, 11, 11))
        x[..., [0, -1], :] = 0
        x[..., :, [0, -1]] = 0
        p = Physics(0.032, 0.073, 1.4, 0.13)
        actual = self.k.diffusion(x, p)[0]
        np.testing.assert_allclose(actual, periodic_d2q5(x[0], p), atol=6e-15)
        self.assertLess(np.max(np.abs(actual[..., [0, -1], :])), 1e-14)

    def test_zero_time_and_zero_coupling(self):
        x, _ = samples(draw(1, 3917), 17)
        np.testing.assert_array_equal(self.k.diffusion(x, Physics(time=0)), x)
        x[:, 0] = 0
        y = self.k.diffusion(x, Physics(rate=0))
        np.testing.assert_array_equal(y[:, 0], 0)
        self.assertGreater(np.linalg.norm(y[:, 1]), 0.1)

    def test_diffusive_grid_convergence(self):
        coeff = draw(1, 73)
        last = None
        for n in (13, 25, 49):
            x, y = samples(coeff, n)
            z = self.k.diffusion(x, NOMINAL)
            err = np.linalg.norm(z - y) / np.linalg.norm(y)
            if last is not None:
                self.assertGreater(last / err, 3.6)
            last = err

    def test_d2q9_matches_vector_reference(self):
        for n in (9, 17):
            x = cp2_reference.density_samples(
                n, np.random.default_rng(7).uniform(-1, 1, (3, 6))
            )
            ref = cp2_reference.cavity_snapshots(x, 0.1, [1, 8, 16])
            for steps, y in ref.items():
                pred = np.concatenate([self.k.cavity(a[None], steps=steps) for a in x])
                np.testing.assert_allclose(pred, y, rtol=3e-6, atol=4e-8)

    @unittest.skipUnless(
        importlib.util.find_spec("neuralop"), "requires neuraloperator"
    )
    def test_archived_checkpoint_enforces_grid(self):
        from runtime_benchmark import cp2_network

        with self.assertRaisesRegex(ValueError, "17 by 17"):
            cp2_network.predict(None, np.ones((1, 257, 257), dtype=np.float32), None, 1)


class TimingTests(unittest.TestCase):
    def test_ready_predictions_match_published_models(self):
        root = Path(__file__).resolve().parent
        arch = root / "runtime_benchmark" / "archived"
        checkpoint = (arch / "cavity-checkpoint.npz").read_bytes()
        git_blob = b"blob " + str(len(checkpoint)).encode() + b"\0" + checkpoint
        self.assertEqual(
            hashlib.sha1(git_blob).hexdigest(),
            "2cc0cef8ef92c0a0409acbedb5bf39f7aa7b39b8",
        )
        with (root / "results" / "runtime" / "total_jobs.csv").open() as stream:
            runs = {(r["problem"], r["model"]): r for r in csv.DictReader(stream)}
        published = json.loads((arch / "cavity_accuracy.json").read_text())["runs"][0]
        self.assertEqual(published["seed"], 2027)
        measured = float(runs["cavity", "Cavity-FNO"]["error_ready"])
        self.assertAlmostEqual(measured, published["vector"]["mean"], delta=2e-9)
        with (root / "results" / "neural.csv").open() as stream:
            for r in csv.DictReader(stream):
                if r["seed"] != "2027":
                    continue
                key = (r["case"], r["scenario"])
                matched = {
                    ("n96", "nominal"): "diffusion",
                    ("family", "family_test"): "family",
                }
                if key in matched:
                    measured = float(runs[matched[key], r["model"]]["error_ready"])
                    expected = (float(r["u"]) + float(r["v"])) / 2
                    self.assertAlmostEqual(measured, expected, delta=5e-6)

    def test_projected_crossover_uses_a_strict_inequality(self):
        path = Path(__file__).resolve().parent / "results/runtime/break_even.csv"
        with path.open() as stream:
            for row in csv.DictReader(stream):
                gain = float(row["saving_per_field_s"])
                extra = float(row["extra_prepare_s"])
                if gain <= 0:
                    self.assertEqual(row["strict_crossover_n"], "")
                else:
                    n = int(row["strict_crossover_n"])
                    self.assertGreater(n * gain, extra)
                    if n > 1:
                        self.assertLessEqual((n - 1) * gain, extra)

    def test_full_cavity_clocks_and_field_identity(self):
        arch = Path(__file__).resolve().parent / "runtime_benchmark" / "archived"
        data = [
            json.loads((arch / f"full-mpi-{r}.json").read_text()) for r in (1, 2, 4, 8)
        ]
        self.assertEqual({d["steps"] for d in data}, {350000})
        self.assertEqual(len({d["field_sha256"] for d in data}), 1)
        self.assertTrue(all(d["launcher_wall_s"] >= d["kernel_s"] > 0 for d in data))

    def test_matched_timings_and_sample_counts(self):
        root = Path(__file__).resolve().parent / "results" / "runtime"
        with (root / "total_jobs.csv").open() as f:
            items = list(csv.DictReader(f))
        self.assertEqual(len(items), 16)
        expected_counts = {"diffusion": 32, "family": 32, "cavity": 24}
        clocks = json.loads((root / "timings.json").read_text())
        for item in items:
            self.assertEqual(int(item["n"]), expected_counts[item["problem"]])
            for m in ("fresh", "ready"):
                self.assertLessEqual(float(item[m + "1_s"]), float(item[m + "N_s"]))
            warm = clocks["jobs"][item["problem"] + "/" + item["model"]]["warm"][
                "block_seconds"
            ]
            self.assertEqual(len(warm), 9)
            self.assertAlmostEqual(np.median(warm), float(item["warmN_s"]))
            self.assertTrue(np.isfinite(float(item["error_ready"])))
        t = json.loads((root / "original_total.json").read_text())
        self.assertEqual(t["trained_networks"], 42)
        self.assertGreater(t["wall_seconds"], t["sum_inner_fits_seconds"])
        self.assertLess(abs(t["wall_seconds"] - sum(t["phases_seconds"].values())), 0.1)


if __name__ == "__main__":
    unittest.main()

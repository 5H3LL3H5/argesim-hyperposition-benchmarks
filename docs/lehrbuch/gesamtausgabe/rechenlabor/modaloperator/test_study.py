"""Run with python -m unittest -v. Torch tests run when the optional stack is installed."""

import contextlib
import csv
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp
from scipy.linalg import expm

from physics import (
    KNOWN,
    NEW,
    NOMINAL,
    Generator,
    Modal,
    Physics,
    StrangModal,
    add_training_noise,
    basis,
    counter_probe,
    draw,
    family,
    fixed_split,
    probe_score,
    project,
    reconstruct,
    reference_matrix,
    samples,
    score,
    strang,
)


class PhysicsTests(unittest.TestCase):
    def test_orthogonal_sines_and_resolvable_indices(self):
        for n in (13, 25):
            b = basis(n, KNOWN + NEW)
            np.testing.assert_allclose(
                b @ b.T, ((n - 1) / 2) ** 2 * np.eye(len(b)), atol=1e-12
            )
        for modes in [((0, 1),), ((12, 1),), ((1, 1), (1, 1))]:
            with self.assertRaises(ValueError):
                basis(13, modes)

    def test_projection_on_two_meshes(self):
        c = draw(7, 91)
        for n in (13, 25):
            np.testing.assert_allclose(
                project(reconstruct(c, n)), c, rtol=1e-12, atol=1e-13
            )

    def test_generator_against_independent_ode_and_pade(self):
        p = Physics(0.042, 0.031, 0.71, 0.53)
        for k, block in zip(KNOWN + NEW, reference_matrix(KNOWN + NEW, p)):
            laplace = np.pi**2 * np.dot(k, k)
            a = np.array(
                [[-laplace * p.du - p.rate, p.rate], [p.rate, -laplace * p.dv - p.rate]]
            )
            np.testing.assert_allclose(block, expm(a * p.time), atol=5e-15)
            init = np.array([1.3, -0.4])
            ivp = solve_ivp(
                lambda t, z, matrix=a: matrix @ z,
                (0, p.time),
                init,
                method="DOP853",
                rtol=1e-12,
                atol=2e-14,
            )
            self.assertTrue(ivp.success)
            np.testing.assert_allclose(
                block @ init, ivp.y[:, -1], atol=3e-13, rtol=3e-12
            )

    def test_truth_semigroup_symmetry_contraction(self):
        p = Physics(time=0.20)
        h = reference_matrix(KNOWN, p)
        np.testing.assert_allclose(h @ h, reference_matrix(KNOWN, NOMINAL), atol=5e-15)
        np.testing.assert_allclose(h, h.swapaxes(1, 2), atol=1e-14)
        self.assertTrue(
            np.all((np.linalg.eigvalsh(h) > 0) & (np.linalg.eigvalsh(h) <= 1))
        )

    def test_zero_exchange_zero_time_and_equal_diffusion(self):
        c = draw(9, 333, KNOWN + NEW)
        for p in (Physics(rate=0), Physics(time=0), Physics(du=0.04, dv=0.04)):
            x, y = samples(c, 25, KNOWN + NEW, p)
            np.testing.assert_allclose(strang(x, p), y, atol=1.2e-7, rtol=2e-6)
        x, y = counter_probe(Physics(rate=0))
        result = probe_score(strang(x, Physics(rate=0)), y)
        self.assertIsNone(result["response"])
        self.assertEqual(result["response_abs_l2"], 0.0)

    def test_strang_local_defect_order(self):
        m = ((3, 2),)
        init = np.array([[[0.15], [1.0]]])
        x = reconstruct(init, 25, m)

        def defect(t):
            p = Physics(time=t)
            truth = np.einsum("kij,bjk->bik", reference_matrix(m, p), init)
            return np.linalg.norm(project(strang(x, p), m) - truth)

        self.assertGreater(defect(0.008) / defect(0.004), 7.5)

    def test_rank_failure_and_identification(self):
        x, y = fixed_split(1, 1, 13)
        with self.assertRaisesRegex(ValueError, "rank 1"):
            Modal.fit(x, y)
        c = draw(3, 13)
        c[:, 1, :] = c[:, 0, :]
        x, y = samples(c, 13)
        with self.assertRaises(ValueError):
            Modal.fit(x, y)
        x, y = fixed_split(2, 42201, 13)
        fit = Modal.fit(x, y)
        np.testing.assert_allclose(
            fit.blocks, reference_matrix(KNOWN, NOMINAL), atol=2e-6
        )

    def test_original_countercalculation_in_both_units(self):
        fit = Modal.fit(*fixed_split(96, 42201, 13))
        x, y = fixed_split(32, 42203, 25)
        stat = score(fit.predict(x), y)
        np.testing.assert_allclose(
            [stat["u"], stat["v"]], [2.5510e-8, 2.5262e-8], rtol=0.005
        )
        e = reference_matrix(KNOWN, NOMINAL)[0, 0, 1]
        self.assertAlmostEqual(
            abs(fit.blocks[0, 0, 1] / e - 1), 2.26997e-9, delta=1e-11
        )
        xp, yp = counter_probe()
        field = probe_score(fit.predict(xp), yp)["response"]
        self.assertGreater(field, 2e-8)
        self.assertLess(field, 2e-7)

    def test_unknown_mode_and_residual_fallback(self):
        x, y = fixed_split(96, 42201, 13)
        xf, yf = samples(draw(6, 910, NEW), 25, NEW)
        m = Modal.fit(x, y)
        hybrid = StrangModal.fit(x, y)
        self.assertAlmostEqual(score(m.predict(xf), yf)["u"], 1.0, places=10)
        np.testing.assert_allclose(hybrid.predict(xf), strang(xf), atol=2e-10)

    def test_generator_identification_and_extra_modes(self):
        g = Generator.fit(*fixed_split(96, 42201, 13))
        np.testing.assert_allclose(g.coeff, (0.03, 0.06, 1.25), rtol=2e-7)
        c = draw(8, 190, NEW)
        for p in (NOMINAL, Physics(time=0.8), Physics(time=0)):
            x, y = samples(c, 25, NEW, p)
            np.testing.assert_allclose(g.predict(x, p), y, atol=8e-8)
        np.testing.assert_array_equal(
            g.predict(x, Physics(rate=0.2)), g.predict(x, Physics(rate=2.5))
        )
        with self.assertRaises(ValueError):
            Generator.fit(*fixed_split(2, 1, 13), train_time=0)

    def test_noise_split_and_rank_independent_of_labels(self):
        x, y = fixed_split(96, 42201, 13)
        backup = y.copy()
        noisy = add_training_noise(y, 0.05)
        self.assertTrue(np.array_equal(backup, y))
        self.assertTrue(np.array_equal(noisy[:8], add_training_noise(y[:8], 0.05)))
        self.assertTrue(np.array_equal(noisy[..., 0, :], y[..., 0, :]))
        self.assertFalse(np.array_equal(noisy, y))
        coherent = add_training_noise(y, 0.05, mode_noise=True)
        self.assertGreater(
            np.linalg.norm(project(coherent - y)),
            3 * np.linalg.norm(project(noisy - y)),
        )
        self.assertTrue(np.array_equal(x[:8], fixed_split(8, 42201, 13)[0]))
        self.assertFalse(np.array_equal(x[:24], fixed_split(24, 42202, 13)[0]))

    def test_paired_family_and_mesh(self):
        c = draw(8, 410)
        params = family(8, 520)
        x13, y13 = samples(c, 13, params=params)
        x25, y25 = samples(c, 25, params=params)
        np.testing.assert_array_equal(x13, x25[:, :, ::2, ::2])
        np.testing.assert_array_equal(y13, y25[:, :, ::2, ::2])
        v = strang(x13, params)
        for i, p in enumerate(params):
            np.testing.assert_array_equal(strang(x13[i : i + 1], p), v[i : i + 1])

    def test_source_hashes_and_archive_rows(self):
        d = Path(__file__).resolve().parent / "reference"
        hashes = {
            "austausch.py": "18675203cf17532e884022275602519da97d848fbb32e497ca044391f7d6ef4d",
            "messung_kapazitaet.json": "75b660ebdcd1e358417f808d58a48908bdf1dd8f9f016f2d5da07cfecf4fe163",
        }
        for name, h in hashes.items():
            self.assertEqual(hashlib.sha256((d / name).read_bytes()).hexdigest(), h)
        rows = json.loads((d / "messung_kapazitaet.json").read_bytes())["rows"]
        for name, pct in [("FNO-small", 38.11), ("UNO", 38.05), ("CoDA-NO", 132.04)]:
            group = [
                r["counterfactual_relative_l2_u"] for r in rows if r["model"] == name
            ]
            self.assertEqual(len(group), 3)
            self.assertEqual(round(100 * np.mean(group), 2), pct)


class ResultTests(unittest.TestCase):
    def test_paired_bootstrap_matches_recorded_contrasts(self):
        from paired_intervals import intervals

        root = Path(__file__).resolve().parent / "results"
        with (root / "paired_intervals.csv").open(encoding="utf-8") as stream:
            stored = list(csv.DictReader(stream))
        actual = intervals(root)
        self.assertEqual(len(stored), 4)
        for expected, r in zip(stored, actual):
            self.assertEqual(expected["baseline"], r["baseline"])
            self.assertEqual(expected["candidate"], r["candidate"])
            self.assertEqual(r["test_pairs"], 32)
            for key in ("gain_pp", "p025_pp", "p975_pp"):
                self.assertAlmostEqual(float(expected[key]), r[key], places=10)

    def test_complete_measured_grid_and_sample_means(self):
        root = Path(__file__).resolve().parent / "results"
        for name, expected_fits in [("neural", 42), ("structured", 110)]:
            with (root / (name + ".csv")).open(encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            with (root / (name + "_samples.csv")).open(encoding="utf-8") as stream:
                fields = list(csv.DictReader(stream))
            self.assertEqual(len(rows), expected_fits * 12)
            self.assertEqual(len(fields), len(rows) * 32)
            for i, row in enumerate(rows):
                section = fields[32 * i : 32 * (i + 1)]
                ident = ("model", "case", "seed", "scenario")
                self.assertTrue(
                    all(all(s[k] == row[k] for k in ident) for s in section)
                )
                self.assertEqual([int(s["sample"]) for s in section], list(range(32)))
                for channel in ("u", "v"):
                    self.assertAlmostEqual(
                        float(row[channel]),
                        np.mean([float(s[channel]) for s in section]),
                        places=12,
                    )
                if row["scenario"] in ("t_zero", "k_zero", "family_test"):
                    self.assertEqual(row["response"], "")
                else:
                    self.assertNotEqual(row["response"], "")


@unittest.skipUnless(
    importlib.util.find_spec("torch") and importlib.util.find_spec("neuralop"),
    "requires the optional original NeuralOperator stack",
)
class NetworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import neural

        cls.neural = neural
        neural.configure()

    def test_bitwise_original_data(self):
        for key, n, seed, count in [
            ("train", 13, 42201, 96),
            ("validation", 13, 42202, 24),
            ("test13", 13, 42203, 32),
            ("test25", 25, 42203, 32),
        ]:
            original = self.neural.pr.arrays(count, np.random.default_rng(seed), n)
            current = fixed_split(count, seed, n)
            path = Path(__file__).resolve().parent / "reference" / "nominale_felder.npz"
            with np.load(path) as archive:
                for suffix, a, b in zip(("_x", "_y"), original, current):
                    np.testing.assert_array_equal(a.numpy(), b)
                    np.testing.assert_array_equal(archive[key + suffix], b)

    def test_input_noise_leaves_targets_and_validation_clean(self):
        n = self.neural
        train, val = n.data("n96")
        train_in, val_in = n.data("input5")
        train_out, val_out = n.data("noise5")
        self.assertFalse(np.array_equal(train_in[0], train[0]))
        np.testing.assert_array_equal(train_in[1], train[1])
        np.testing.assert_array_equal(train_out[0], train[0])
        self.assertFalse(np.array_equal(train_out[1], train[1]))
        for v in (val_in, val_out):
            for actual, expected in zip(v[:2], val[:2]):
                np.testing.assert_array_equal(actual, expected)

    def test_saved_weights_match_measured_fields(self):
        base = Path(__file__).resolve().parent / "results"
        with (base / "neural.csv").open(encoding="utf-8") as stream:
            expected = list(csv.DictReader(stream))
        n = self.neural
        with contextlib.redirect_stdout(io.StringIO()):
            for name in n.MODELS + n.CONDITIONAL:
                conditional = name in n.CONDITIONAL
                case = "family" if conditional else "n96"
                scenario = "family_test" if conditional else "nominal"
                params = family(32, 52203) if conditional else NOMINAL
                x, y = samples(draw(32, 42203), 25, params=params)
                net = n.Network(base / "weights" / f"{case}_{name}_2027.pt")
                actual = score(net.predict(x, params), y)
                ref = next(
                    r
                    for r in expected
                    if (r["model"], r["case"], r["seed"], r["scenario"])
                    == (name, case, "2027", scenario)
                )
                for field in ("u", "v"):
                    np.testing.assert_allclose(
                        actual[field], float(ref[field]), rtol=2e-4, atol=2e-6
                    )

    def test_counts_boundaries_and_condition_channels(self):
        n = self.neural
        x, y = fixed_split(1, 55, 13)
        with contextlib.redirect_stdout(io.StringIO()), n.torch.inference_mode():
            for name in n.MODELS + n.CONDITIONAL:
                model = n.make(name)
                count = sum(
                    p.numel() * (2 if p.is_complex() else 1) for p in model.parameters()
                )
                if name in n.MODELS:
                    self.assertEqual(count, 1051 if name == "CoDA-NO" else 1034)
                f = n.features(x, NOMINAL, name)
                pred = n.pr.predict(model, f).numpy()
                self.assertEqual(pred.shape, y.shape)
                self.assertEqual(score(pred, y)["boundary"], 0)
            f = n.features(x, [Physics(time=0.8)], "FNO-cond").numpy()
            self.assertEqual(f.shape[1], 6)
            self.assertAlmostEqual(f[0, -1, 6, 6], 1.0)

    def test_restart_determinism_and_hybrid_evaluation(self):
        n = self.neural
        with (
            tempfile.TemporaryDirectory() as temp,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            folder = Path(temp)
            x, _ = fixed_split(2, 43, 13)
            for name in ("FNO-small", "Strang-FNO"):
                before = None
                for _ in range(2):
                    info = n.train(name, 2027, "n2", folder, epochs=1)
                    pred = n.Network(folder / f"n2_{name}_2027.pt").predict(x)
                    if before is not None:
                        np.testing.assert_array_equal(pred, before)
                    before = pred.copy()
                    self.assertTrue(np.isfinite(pred).all())
                    self.assertGreaterEqual(info["selected_epoch"], 0)


if __name__ == "__main__":
    unittest.main()

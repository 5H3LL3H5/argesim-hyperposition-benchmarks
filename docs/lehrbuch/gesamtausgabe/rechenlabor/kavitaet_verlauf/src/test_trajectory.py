"""Fast, deterministic regression checks for the packaged CP2 trajectory audit."""

import csv
import os
import tempfile
import unittest
from pathlib import Path

import numpy as np
from design import ORIGINAL, N, ticks
from eingaben import prepare
from evaluate import Projection, summary
from fields import Frozen, diagnostics, lid_value, prolong, raw_field
from native import Lattice, build
from stepper import ANCHORS, Stepper, support_grid

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prepared = os.environ.get("CP2_VERLAUF_INPUTS")
        if prepared:
            cls.inputs = Path(prepared)
        else:
            scratch = tempfile.TemporaryDirectory(prefix="cp2-test-")
            cls.addClassCleanup(scratch.cleanup)
            cls.inputs = Path(scratch.name)
            prepare(cls.inputs)

    def test_schedule_and_blind_times(self):
        historical = np.loadtxt(self.inputs / "src/zeitpunkte.txt", dtype=int)
        planned = ticks(historical)
        support = set(support_grid(planned))
        self.assertEqual(len(planned), 315)
        self.assertEqual(len(set(planned) - set(historical)), 278)
        self.assertTrue(all(k % 4 == 0 for k in planned))
        self.assertEqual(planned[-1], 350000)
        self.assertTrue({4096, 65536, 262144}.isdisjoint(support))
        self.assertEqual(len(support), 159)

    def test_zero_norm_and_local_error(self):
        truth = np.zeros((N, N, 2))
        guess = truth.copy()
        guess[8, 4] = (0.03, 0.04)
        m = diagnostics(guess, truth)
        self.assertIsNone(m["rel"])
        self.assertAlmostEqual(m["max_U"], 0.05)
        self.assertEqual((m["x"], m["y"]), (4, 8))
        guess[:] = 0
        guess[-1, :, 0] = 5
        self.assertEqual(diagnostics(guess, truth)["max_U"], 0)

    def test_prolongation_reproduces_affine_fields(self):
        y, x = np.mgrid[:65, :65]
        v = np.stack((3 * x + 2 * y, 1 + y - x), axis=-1).astype(float)
        Y, X = np.mgrid[:N, :N] / 4
        expected = np.stack((3 * X + 2 * Y, 1 + Y - X), axis=-1)
        np.testing.assert_allclose(prolong(v), expected, rtol=0, atol=1e-13)

    def test_unmodified_fourier_against_archived_reference(self):
        model = Frozen(self.inputs, "direkt", "fourier")
        pred = model.predict(ORIGINAL)
        with np.load(self.inputs / "daten/testreferenzen.npz") as f:
            truth = f["lbm"]
        with (self.inputs / "daten/operatoren/test.csv").open() as f:
            legacy = {
                int(r["step"]): r
                for r in csv.DictReader(f)
                if (r["art"], r["kern"]) == ("direkt", "fourier")
            }
        for k, v, ref in zip(ORIGINAL, pred, truth, strict=True):
            val = diagnostics(v, ref)
            self.assertAlmostEqual(val["rel"], float(legacy[k]["rel"]), places=10)
            self.assertAlmostEqual(val["max_U"], float(legacy[k]["max_U"]), places=10)

    def test_rollout_semantics(self):
        net = Stepper(self.inputs, RESULTS / "stepper.npz")
        self.assertEqual(tuple(net.p["anchors"]), ANCHORS)
        self.assertNotIn(1000, net.p["anchors"])
        head = net.head(1000)
        np.testing.assert_allclose(
            head, (net.p["heads"][0] + net.p["heads"][1]) / 2, rtol=1e-14
        )
        v = net.rollout([0, 4, 8])
        np.testing.assert_array_equal(v[0], np.zeros(24))
        np.testing.assert_allclose(
            v[-1], net.advance(net.advance(v[0], 0, 4, head), 4, 8, head)
        )
        np.testing.assert_array_equal(net.rollout([0, 4, 8, 12])[:3], v)
        self.assertTrue(np.max(np.abs(net.advance(v[1] + 1, 4, 8, head) - v[2])) > 1e-6)
        for seq in ([4, 8], [0, 0], [0, 8, 4]):
            with self.assertRaises(ValueError):
                net.rollout(seq)

    def test_best_interior_projection(self):
        basis = np.load(self.inputs / "daten/operatoren/basis_direkt.npy", mmap_mode="r")
        p = Projection(basis)
        rng = np.random.default_rng(41)
        ref = (rng.normal(size=24) @ basis).reshape(N, N, 2)
        ref = lid_value(ref)
        m = diagnostics(p.field(ref), ref)
        self.assertLess(m["rel"], 1e-12)

    def test_time_integral_uses_interval_lengths(self):
        rows = [
            {
                "method": "toy",
                "k": k,
                "error_sq": e,
                "ref_sq": b,
                "rel": r,
                "max_U": 0.0,
                "pass_both": p,
                "book7": False,
                "new_time": k > 0,
            }
            for k, e, b, r, p in (
                (0, 0, 0, None, None),
                (16, 1, 1, 1.0, False),
                (4096, 0, 1, 0.0, True),
            )
        ]
        self.assertAlmostEqual(
            summary(rows)["space_time_rel"], np.sqrt(4096 / (16 + 2 * (4096 - 16)))
        )

    def test_native_transient_independent_numpy(self):
        import subprocess

        from check_reference import microcheck

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build(self.inputs, root)
            n = 17
            steps = [1, 4, 16]
            (root / "ticks").write_text("1\n4\n16\n")
            dest = root / "n17_re1000"
            subprocess.run(
                [root / "d2q9", "17", "1000", "1", dest, root / "ticks"], check=True
            )
            errs = microcheck(17, 1000, steps, root)
            self.assertLess(max(max(v) for v in errs.values()), 2e-13)
            ram = Lattice(root / "cp2.so").fields(n, 1000, [0, *steps])
            self.assertEqual(ram.shape, (4, 17, 17, 2))
            for i, k in enumerate(steps):
                np.testing.assert_allclose(
                    ram[i + 1], raw_field(root, n, 1000, k), rtol=0, atol=1e-13
                )

    def test_switches_and_window_endpoints(self):
        from switch import START, STOP, Smoothed, Switched, weight

        np.testing.assert_allclose(
            weight([0, START, (START + STOP) // 2, STOP, STOP + 4]), [0, 0, 0.5, 1, 1]
        )

        # A small fake field encodes the Reynolds number and clock on either trajectory.
        # Native solver timing and the full-grid outputs are checked separately.
        class FakeLattice:
            def fields(self, n, re, ticks):
                return np.broadcast_to(
                    np.asarray(ticks)[:, None, None, None] + re, (len(ticks), n, n, 2)
                ).copy()

        class FakeNet:
            def predict(self, ticks, re, coarse):
                return np.broadcast_to(
                    np.asarray(ticks)[:, None, None, None] + re + 10,
                    (len(ticks), N, N, 2),
                )

        times = np.array([0, START, (START + STOP) // 2, STOP, STOP + 4])
        re = 975
        for cls, offset in (
            (Switched, [0, 0, 10, 10, 10]),
            (Smoothed, [0, 0, 5, 10, 10]),
        ):
            net = cls.__new__(cls)
            net.lattice = FakeLattice()
            net.coarse_net = FakeNet()
            np.testing.assert_allclose(
                net.predict(times, re)[:, 4, 4, 0], times + re + offset
            )
            with self.assertRaises(ValueError):
                net.predict([0, 3], re)

    def test_handoff_measurements(self):
        with (RESULTS / "smooth_fenster.csv").open() as f:
            r = list(csv.DictReader(f))
        for re in ("975", "1000", "1025"):
            selected = [
                i
                for i in r
                if i["re"] == re and i["side"] == "entry" and i["k"] == "32772"
            ]
            by = {i["method"]: i for i in selected}
            self.assertEqual(len(by), 2)
            self.assertLess(
                float(by["smooth"]["delta_max_U"]),
                1e-5 * float(by["hard"]["delta_max_U"]),
            )
            for side in ("entry", "exit"):
                self.assertEqual(
                    sum(
                        i["method"] == "smooth" and i["side"] == side and i["re"] == re
                        for i in r
                    ),
                    64,
                )

    def test_interior_and_boundary_verdicts(self):
        def records(name):
            with (RESULTS / name).open() as f:
                return list(csv.DictReader(f))

        main = records("smooth_verlauf.csv")
        windows = records("smooth_fenster.csv")
        walls = records("smooth_alle_knoten.csv")
        for re in ("975", "1000", "1025"):
            primary = [r for r in main if r["re"] == re and int(r["k"]) > 0]
            extra = [r for r in windows if r["re"] == re and r["method"] == "smooth"]
            self.assertEqual(len({r["k"] for r in primary + extra}), 442)
            self.assertTrue(
                all(
                    float(r["rel"]) <= 0.01 and float(r["max_U"]) <= 0.01
                    for r in primary + extra
                )
            )
            side = [r for r in walls if r["re"] == re]
            self.assertEqual(sum(r["full_pass"] == "True" for r in side), 309)
            self.assertGreater(float(side[-1]["boundary_max_U"]), 0.01)

    def test_published_table_recomputed_from_all_rows(self):
        from collections import defaultdict

        def records(name):
            with (RESULTS / name).open() as f:
                return list(csv.DictReader(f))

        groups = defaultdict(list)
        for row in records("verlauf.csv"):
            row["k"] = int(row["k"])
            row["rel"] = float(row["rel"]) if row["rel"] else None
            for x in ("max_U", "error_sq", "ref_sq"):
                row[x] = float(row[x])
            for x in ("pass_both", "book7", "new_time"):
                row[x] = row[x] == "True"
            groups[row["method"]].append(row)
        for row in records("vergleich.csv"):
            original = groups[row["method"]]
            self.assertEqual(len(original), 316)
            calc = summary(original)
            for prop in ("n_pass", "worst_rel_k", "n_new_pass", "n_book_pass"):
                self.assertEqual(calc[prop], int(row[prop]))
            for prop in ("worst_rel", "end_rel", "space_time_rel", "worst_max_U"):
                self.assertAlmostEqual(calc[prop], float(row[prop]), places=10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
